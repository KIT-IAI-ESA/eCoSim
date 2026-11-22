# Building example

A house, its weather and the people in it, as three FMI 2.0 models. In every step of 15 minutes `weather`
and `occupancy` give their values to `house`.

Run it from the `simulation_examples` folder. The results are written as files, so no database is needed:

```shell
uv run ecosim run building --steps 100
uv run ecosim results building
```

To start the server and the clients by hand and store the results in PostgreSQL, see
[Executable/README.md](Executable/README.md).
