from __future__ import annotations

import pickle
from pathlib import Path

from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from tests.tech.db.file_repository_test_setup import (
    MeasurementFileRepository,
    RecordingLock,
    create_measurement,
    create_repository,
    read_lines_of,
)


def test_all_is_empty_when_the_file_does_not_exist(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl")
    assert repository.all() == []


def test_an_added_entry_is_returned_by_all(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl")
    entry = create_measurement()

    repository.add(entry)

    assert repository.all() == [entry]


def test_the_entries_are_returned_in_the_order_they_were_added(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl")
    entries = [create_measurement(minute) for minute in range(3)]

    for entry in entries:
        repository.add(entry)

    assert repository.all() == entries


def test_blank_lines_are_ignored(tmp_path: Path) -> None:
    file_path = tmp_path / "measurements.jsonl"
    repository = create_repository(file_path)
    entry = create_measurement()

    repository.add(entry)
    with file_path.open("a", encoding="utf-8") as file:
        file.write("\n")

    assert repository.all() == [entry]


def test_every_entry_is_written_as_one_json_line(tmp_path: Path) -> None:
    file_path = tmp_path / "measurements.jsonl"
    repository = create_repository(file_path)

    repository.add(create_measurement(0))
    repository.add(create_measurement(1))

    lines = read_lines_of(file_path)
    assert len(lines) == 2


def test_the_entries_are_persisted_for_a_new_repository_instance(tmp_path: Path) -> None:
    file_path = tmp_path / "measurements.jsonl"
    create_repository(file_path).add(create_measurement())

    assert create_repository(file_path).all() == [create_measurement()]


def test_a_missing_parent_directory_is_created(tmp_path: Path) -> None:
    file_path = tmp_path / "results" / "measurements.jsonl"

    create_repository(file_path).add(create_measurement())

    assert file_path.exists()


def test_adding_an_entry_uses_the_write_lock(tmp_path: Path) -> None:
    write_lock = RecordingLock()
    repository = create_repository(tmp_path / "measurements.jsonl", write_lock)

    repository.add(create_measurement())

    assert write_lock.enter_count == 1


def test_reading_the_entries_uses_the_write_lock(tmp_path: Path) -> None:
    write_lock = RecordingLock()
    repository = create_repository(tmp_path / "measurements.jsonl", write_lock)
    repository.add(create_measurement())

    repository.all()

    assert write_lock.enter_count == 2


def test_the_repository_survives_a_pickle_round_trip(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl")

    restored = pickle.loads(pickle.dumps(repository))

    assert isinstance(restored, MeasurementFileRepository)
    assert restored == repository


def test_the_unpickled_repository_reads_the_entries_of_the_file(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl")
    repository.add(create_measurement())

    restored = pickle.loads(pickle.dumps(repository))

    assert restored.all() == [create_measurement()]


def test_the_unpickled_repository_adds_to_the_same_file(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl")
    repository.add(create_measurement(0))

    restored = pickle.loads(pickle.dumps(repository))
    restored.add(create_measurement(1))

    assert repository.all() == [create_measurement(0), create_measurement(1)]


def test_a_repository_with_a_dask_lock_can_be_pickled(tmp_path: Path) -> None:
    repository = create_repository(tmp_path / "measurements.jsonl", ParallelLock.dask(name="file_repository"))

    restored = pickle.loads(pickle.dumps(repository))

    assert restored.file_path() == repository.file_path()
