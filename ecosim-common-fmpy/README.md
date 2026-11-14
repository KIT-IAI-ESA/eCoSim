# ecosim-common-fmpy

Code shared by the eCoSim clients for FMI 2.0 and FMI 3.0 models, which run the models with fmpy: the `fmu_file` setting, the `[start_values]` section, the `--validate-fmu-file-only` option that only checks the FMU file, the interfaces of the `.fmc` file and the start values, the rule that chooses the client for a simulator folder, the inputs and outputs an FMU offers to eCoSim, and a fix for a threading problem in lxml.

See the [architecture page](https://ecosim.easimov.com/docs/development/architecture#subprojects) of the eCoSim documentation.
