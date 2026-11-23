# Examples

Three simulations to try eCoSim with. You need [uv](https://docs.astral.sh/uv/), for `docker` Docker or Podman instead.

| Folder | What it is |
| --- | --- |
| [building](building) | a house, its weather and the people in it, as three FMI 2.0 models. Runs on your machine |
| [building_hpc](building_hpc) | the same models, set up for a run on an HPC cluster |
| [docker](docker) | a house simulation in containers, with the results in PostgreSQL or as files. Needs Docker or Podman |

Run the building example from this folder:

```shell
uv run ecosim check building
uv run ecosim run building --steps 100
uv run ecosim results building
```

The [quick start](../docs/content/getting-started/quick-start.md) explains each step.
