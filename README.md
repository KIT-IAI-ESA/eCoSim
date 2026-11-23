<div align="center">

<h1>
<img alt="eCoSim" src="docs/static/img/readme/wordmark-band.png" width="100%">
</h1>

A co-simulation framework for energy systems.

[![tests](https://img.shields.io/github/actions/workflow/status/KIT-IAI-ESA/eCoSim/tests.yml?branch=main&label=tests&style=for-the-badge)](https://github.com/KIT-IAI-ESA/eCoSim/actions/workflows/tests.yml)
[![windows tests](https://img.shields.io/github/actions/workflow/status/KIT-IAI-ESA/eCoSim/windows-tests.yml?branch=main&label=windows%20tests&style=for-the-badge)](https://github.com/KIT-IAI-ESA/eCoSim/actions/workflows/windows-tests.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/KIT-IAI-ESA/eCoSim/github-code-scanning/codeql?branch=main&label=CodeQL&style=for-the-badge)](https://github.com/KIT-IAI-ESA/eCoSim/actions/workflows/github-code-scanning/codeql)
[![docs](https://img.shields.io/github/actions/workflow/status/KIT-IAI-ESA/eCoSim/docs.yml?branch=main&label=docs&style=for-the-badge)](https://ecosim.easimov.com/docs)
[![licence](https://img.shields.io/badge/licence-Apache%202.0-00876c?style=for-the-badge)](LICENSE)
[![python](https://img.shields.io/badge/python-3.12%20%7C%203.14-00876c?style=for-the-badge)](https://ecosim.easimov.com/docs/getting-started/installation)
[![FMI](https://img.shields.io/badge/FMI-2.0%20%7C%203.0-00876c?style=for-the-badge)](https://fmi-standard.org/)

</div>

eCoSim runs several simulation models together as one simulation, for example a house, its heating
and the weather. In every step it passes the outputs of each model on to the models that need them.

```mermaid
---
config:
  look: classic
  flowchart:
    rankSpacing: 30
  themeVariables:
    lineColor: "#00876c"
---
flowchart TB
    fmu2(["FMI 2.0"]) <--> server(("eCoSim"))
    fmu3(["FMI 3.0"]) <--> server
    server <--> matlab(["MATLAB"])
    matlab ~~~ results[("Results")]
    server --> results
    server <--> python(["Python"])
    python ~~~ results
    classDef accent fill:#00876c,stroke:#00876c,color:#ffffff,font-size:18px,font-weight:bold
    classDef plain fill:transparent,stroke:#00876c
    class server accent
    class fmu2,fmu3,matlab,python,results plain
    linkStyle 0,1,2,4,5 stroke-width:2px
```

Your models can be FMUs (FMI 2.0 or 3.0), MATLAB scripts or Python code. The results go into files or
into PostgreSQL. To run many simulations on a cluster, see the
[HPC guide](https://ecosim.easimov.com/docs/guides/hpc-cluster).

## Quick start

You need Python 3.12 or newer and [uv](https://docs.astral.sh/uv/). eCoSim is installed from source:

```shell
git clone https://github.com/KIT-IAI-ESA/ecosim.git
cd ecosim
```

The building example runs three models for 100 steps. No database is needed:

```shell
cd examples
uv run ecosim check building
uv run ecosim run building --steps 100
uv run ecosim results building
```

The first run takes a moment to set up. The results and the logs end up in `building/results`. The
[quick start](https://ecosim.easimov.com/docs/getting-started/quick-start) explains each step and shows
how to use your own FMUs.

## What it looks like

A real run of the three commands, with the waits shortened.

<img alt="The three commands of the quick start in a terminal" src="docs/static/img/readme/quick-start.svg" width="100%">

## Documentation

The documentation is at [ecosim.easimov.com/docs](https://ecosim.easimov.com/docs).

## Contributing

Questions, bug reports and pull requests are welcome, see [Contributing](CONTRIBUTING.md).

## Citing eCoSim

If you use eCoSim in your work, please cite it. The details are in [CITATION.cff](CITATION.cff), and
GitHub shows them under "Cite this repository" on the repository page.

## Licence

eCoSim is released under the [Apache License 2.0](LICENSE).

## Credits

eCoSim is part of [eASiMOV](https://easimov.cloud.iai.kit.edu). It is a project of the
[Energy System Analysis](https://www.iai.kit.edu/english/groups_4104.php) research group at the
[Institute for Automation and Applied Informatics (IAI)](https://www.iai.kit.edu/english/index.php)
of the [Karlsruhe Institute of Technology (KIT)](https://www.kit.edu/english/index.php).
