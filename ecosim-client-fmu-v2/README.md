# ecosim-client-fmu-v2

The eCoSim client for FMI 2.0 models. It runs a co-simulation FMU with fmpy and exchanges its Real inputs and outputs with the eCoSim server.

```shell
pip install ecosim-client-fmu-v2
ecosim-client-fmu-v2 --config-file modules/house/preferences.ini
```

The `ecosim` package installs it as well, and `ecosim new` writes the config files of a simulation from your FMUs.

See [Your own models](https://ecosim.easimov.com/docs/getting-started/your-own-models), the [settings of the FMU clients](https://ecosim.easimov.com/docs/reference/configuration-files#fmu-clients) and the [options of `ecosim-client-fmu-v2`](https://ecosim.easimov.com/docs/reference/command-line#fmu-clients).
