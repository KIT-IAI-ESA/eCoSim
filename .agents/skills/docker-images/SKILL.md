---
name: docker-images
description: Build the ecosim container images and run the docker-compose examples for the postgres and file storage backends. Use when working on the Dockerfile, the images, or dev/docker/example.
---

# Docker images and examples

## Build

All images come from the single `dev/docker/Dockerfile`, parameterised by `SOURCE_DIR` and
`COMMAND_NAME`:

```shell
cd dev/docker
docker compose -f docker-compose-build-images.yml build ecosim_server ecosim_client_fmu_v2
```

Services: `ecosim_server`, `ecosim_client_fmu_v2`, `ecosim_client_fmu_v3`,
`ecosim_client_matlab`, `ecosim_client_pyro5`.

Each service pins an explicit `image:` (`localhost/ecosim_server:latest`, …). That pin is
load-bearing: without it compose tags the build `localhost/<project>_<service>` — i.e.
`localhost/docker_ecosim_server` — and the examples, which refer to the images by their
plain name, silently keep using an older image. Do not remove the `image:` keys.

## The executable is the ENTRYPOINT

The build produces a self-contained `${COMMAND_NAME}.pex` (a `pex --scie eager` binary). The
final stage symlinks it to the fixed path `/opt/ecosim` and declares
`ENTRYPOINT ["/opt/ecosim"]`.

The symlink exists because the **exec form of `ENTRYPOINT` does not expand build
arguments** — `ENTRYPOINT ["/opt/${EXECUTABLE}"]` would look for a literal `${EXECUTABLE}`.
The shell form would expand it but would then swallow appended arguments.

Consequences:

- `command:` in a compose file lists **arguments only** — they are appended to the
  entrypoint. Never put `/opt/ecosim-server.pex` back into a `command:` list.
- `docker run localhost/ecosim_server:latest --help` works directly.
- The original `/opt/<command>.pex` path still resolves through the symlink, so anything
  that referred to it keeps working.

## Run an example

Two variants of the same `house` simulation, differing only in where results go:

| Directory | Storage |
|---|---|
| `dev/docker/example/postgres` | TimescaleDB container, `DatabaseType.POSTGRES` |
| `dev/docker/example/file` | JSON lines bind-mounted to `./results`, `DatabaseType.FILE` |

```shell
cd dev/docker/example/file
docker compose down          # required, see below
docker compose up
```

Both variants publish port 1234, so **they cannot run at the same time**, and neither can
run alongside integration tests that bind that port.

## Pitfalls

- **`docker` may be podman.** `/usr/bin/docker` execs `podman`, and `podman compose`
  delegates to `podman-compose` on the host. It should not make a difference, but on
  errors check which system is actually used.
- **`up` reuses an existing container** instead of recreating it from a freshly built
  image. After any rebuild, run `docker compose down` first — otherwise you debug the old
  code and see stale tracebacks. This is the single most common time sink here.
- **Model mounts are four levels up** from an example directory
  (`../../../../ecosim-test-common/...`). Three levels points at a path that does not
  exist, and the container then fails on a missing model rather than on a bad mount.
- **Results are written as root** under rootful docker. Use `sudo` to remove
  `example/file/results`, which is gitignored and safe to delete.

## Checking a run

```shell
ls results
wc -l results/*.jsonl
tail -n 1 results/simulation_state.jsonl
```

A finished run has one line per step in each `module_<simulator>.jsonl`. Note the two
backends serialise the final state differently — the file repository writes `Finished`, the
database writes `finished`. `dev/docker/example/README.md` documents both variants.
