# eCoSim

`ecosim` is the one command for a simulation on this computer. It installs the eCoSim server, both FMU clients and
the Python client, so a local run needs nothing else.

```shell
ecosim check building
```

`ecosim check` reads a simulation as a run would: the simulation config, the server config and the folder of every
simulator with its model. It lists every problem with its file and names the closest name for a typo.

A simulation folder holds `server/simulation.json`, `server/preferences.ini` and one folder for each simulator in
`Modules/`, like `simulation_examples/building` in the repository.

The extras add the Pyro5 client (`ecosim[pyro5]`) and pandas for the results (`ecosim[pandas]`). The MATLAB client
needs Python 3.12 and is installed on its own, see the MATLAB client guide.

See the [documentation](https://ecosim.easimov.com/docs) for the details.
