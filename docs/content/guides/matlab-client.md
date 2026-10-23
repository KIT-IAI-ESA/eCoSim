---
title: MATLAB client
description: Couple a model written as MATLAB scripts.
---

# MATLAB client

`ecosim-client-matlab` runs a model written as MATLAB scripts. It needs a MATLAB installation and
Python 3.12.

## The model scripts

The model is split into three scripts in one folder:

| Script | Runs |
| --- | --- |
| `setup.m` | once, before the simulation starts |
| `step.m` | every step |
| `finishing.m` | once, after the simulation ends |

- Pre- and postprocessing belong into the script where they are needed. Additional data, such as CSV
  files, is read inside the scripts as well.
- The current simulated time is available as `client_time`, in seconds. Calculate timestamps from it.
- Input and output variables use Python's snake_case names.
- Every output that other simulators use has to be initialized in the MATLAB workspace in `setup.m`.

## Configuration

The client's `preferences.ini` names the folder with the scripts:

```ini
[matlab]
scriptfolder = path/to/the/scripts
```

The other keys are the same as for every client, see the [configuration reference](../reference/configuration-files.md).

## Install

The client needs the MATLAB engine for your MATLAB version, which is chosen with an extra, for
example `R2024b`:

```shell
cd ecosim-client-matlab
uv sync --extra R2024b
```
