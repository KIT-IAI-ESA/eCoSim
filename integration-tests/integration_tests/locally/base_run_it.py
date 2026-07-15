import io
import tempfile
import tarfile
from pathlib import Path
from typing import Tuple

import docker
from docker import DockerClient
import os
import uuid


# Function to copy files from a container and save as a tar file
def save_tar_from_container(
    client,
    container_name,
    src_path,
    tar_dest_path,
):
    container = client.containers.get(container_name)
    # Retrieve the archive from the container
    bits, stat = container.get_archive(src_path)
    # Create a buffer to hold the tar stream
    file_like_object = io.BytesIO()
    # Write the tar stream to the buffer
    for chunk in bits:
        file_like_object.write(chunk)
    # Move the buffer's position to the beginning
    file_like_object.seek(0)
    # Save the tar file to the specified destination
    with open(tar_dest_path, "wb") as tar_file:
        tar_file.write(file_like_object.read())
    print(f"Saved {src_path} from container {container_name} to {tar_dest_path} as a tar file")


def run_integration_test(
    start_script: str,
    copy_results: bool = False,
    copy_logs: bool = False,
    copy_destination_path: str | None = None,
    # ecosimpy_dir must be aligned with ECOSIMPY_DIR in config.sh in integration test container
    ecosimpy_dir: str = "/builds/ecosimpy",
):
    docker_client: DockerClient = docker.from_env()

    print("Build image...")
    image_name = "ecosimpy-it:latest"

    try:
        test_dir = Path(__file__).parent.parent
        image, logs = docker_client.images.build(
            path=os.path.abspath(f"{test_dir}/resources/ci_container"),
            dockerfile="Dockerfile",
            tag=image_name,
        )
        for log in logs:
            if "stream" in log:
                print(log["stream"].strip())
    except docker.errors.BuildError as e:
        print(f"Error building image: {e}")
        if hasattr(e, "build_log"):
            for log in e.build_log:
                if "stream" in log:
                    print(log["stream"].strip())
                elif "errorDetail" in log:
                    print(log["errorDetail"].get("message", ""))
    except docker.errors.APIError as e:
        print(f"API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    def create_tarfile(
        source_dir: str,
        exclude_dirs: Tuple[str, ...] = (),
    ):

        def should_exclude(
            path,
            exclude_dirs,
        ):
            """
            Determine if the given path should be excluded based on the exclude_dirs list.

            :param path: Relative path to check.
            :param exclude_dirs: Set of subdirectories to exclude.
            :return: True if the path should be excluded, False otherwise.
            """
            for exclude_dir in exclude_dirs:
                if (
                    path == exclude_dir
                    or path == f"./{exclude_dir}"
                    or path.startswith(
                        exclude_dir + os.sep,
                    )
                    or path.startswith(f"./{exclude_dir}{os.sep}")
                ):
                    return True
            return False

        exclude_dirs = set(exclude_dirs or [])
        tar_stream = io.BytesIO()

        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            for root, dirs, files in os.walk(source_dir):
                # Normalize the paths to match them properly
                relative_root = os.path.relpath(root, source_dir)

                # Exclude directories matching the exclusion patterns
                dirs[:] = [d for d in dirs if not should_exclude(os.path.join(relative_root, d), exclude_dirs)]

                # Add the directories with mode 777
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    arcname = os.path.relpath(dir_path, source_dir)
                    dir_info = tar.gettarinfo(name=dir_path, arcname=arcname)
                    dir_info.mode = 0o777
                    tar.addfile(dir_info)

                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, source_dir)
                    tar.add(full_path, arcname=arcname)

        tar_stream.seek(0)
        return tar_stream

    def copy_directory_to_container(
        container_name: str,
        source_dir: str,
        destination_dir: str,
        exclude_dirs: Tuple[str, ...] = (),
    ):
        client = docker.from_env()
        container = client.containers.get(container_name)

        tar_stream = create_tarfile(source_dir, exclude_dirs)
        container.put_archive(destination_dir, tar_stream)

    container_name = f"ecosimpy-it-{uuid.uuid4()}"
    try:
        print("Run integration test...")
        docker_client.containers.run(image=image_name, name=container_name, detach=True)
        container = docker_client.containers.get(container_name)

        print("Copy files to container...")
        copy_directory_to_container(
            container_name=container_name,
            source_dir="..",
            destination_dir=ecosimpy_dir,
            exclude_dirs=(
                ".git",
                ".idea",
                "ecosim/venv",
                "ecosim/dist",
                "ecosim/integration_tests",
                "ecosim/unit_tests",
                "ecosim/ecosim-server/build",
                "ecosim/ecosim-server/ecosim_server.egg-info",
                "ecosim/ecosim-common/build",
                "ecosim/ecosim-common/ecosim_common.egg-info",
                "ecosim/ecosim-client-fmu-v2/build",
                "ecosim/ecosim-client-fmu-v2/ecosim_client_fmu_v2.egg-info",
                ".idea",
                ".git",
                ".mypy_cache",
                "doc",
                "sim-control",
                ".pytest_cache",
                "ecosim/.pytest_cache",
                "ecosim/.mypy_cache",
            ),
        )

        print("Start process...")
        exec_id = container.client.api.exec_create(
            container.id,
            start_script,
            stdout=True,
            stderr=True,
        )["Id"]
        output = container.client.api.exec_start(exec_id, stream=True)
        for line in output:
            print(line.decode("utf-8").strip())

        result_path = "/integration_test/results/result"
        stream, _ = container.get_archive(path=result_path)
        # Read the tar stream into a BytesIO object
        file_like_object = io.BytesIO()
        for chunk in stream:
            file_like_object.write(chunk)

        # Seek to the beginning of the BytesIO object
        file_like_object.seek(0)

        # Open the tar archive
        with tarfile.open(fileobj=file_like_object) as tar:
            # Extract the file from the tar archive
            extracted_file = tar.extractfile("result")

            # Read the file contents
            if extracted_file:
                file_contents = extracted_file.read().decode("utf-8")
                print(file_contents)
            else:
                print(f"File {result_path} not found in the archive.")

        if file_contents.startswith("SUCCESS"):
            print("Integration test successful.")
        else:
            print("Integration test failed.")

    finally:
        copy_destination_path = copy_destination_path or tempfile.gettempdir()
        if copy_logs:
            save_tar_from_container(
                client=docker_client,
                container_name=container_name,
                src_path="/integration_test/logs",
                tar_dest_path=f"{copy_destination_path}/logs.tar",
            )
        if copy_results:
            save_tar_from_container(
                client=docker_client,
                container_name=container_name,
                src_path="/integration_test/results",
                tar_dest_path=f"{copy_destination_path}/results.tar",
            )
        docker_client.containers.get(container_name).remove(force=True)
