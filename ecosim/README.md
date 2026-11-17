# eCoSim

`ecosim` runs a simulation locally with one command. It installs the eCoSim server, both FMU clients and the
Python client.

```shell
ecosim check building
ecosim run building --steps 100
ecosim results building
```

`ecosim check` reads the config files and the models of a simulation. It lists every problem with its file.

`ecosim run` checks the simulation, then starts the server and one client per simulator. Each run gets its own
folder in `building/results` with the results and the logs. Ctrl-C stops the run.

`ecosim results` shows the newest run of a simulation with the minimum, mean and maximum of every output.
`--csv results.csv` writes the values as one table.

A simulation folder has `server/simulation.json`, `server/preferences.ini` and one folder per simulator in
`Modules/`, like `simulation_examples/building` in the repository. `ecosim new my_simulation house.fmu weather.fmu`
writes such a folder from FMU files.

The extras add the Pyro5 client (`ecosim[pyro5]`) and pandas for the results (`ecosim[pandas]`). The MATLAB client
needs Python 3.12 and is installed separately, see the MATLAB client guide.

See the [documentation](https://ecosim.easimov.com/docs) for the details.
