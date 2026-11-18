START_VALUES_TEXT = """## Start values

The `preferences.ini` of an FMU client can set variables of the FMU in a `[start_values]` section, for
example parameters. The FMU does not have to be exported again. The client sets the values before the FMU
initializes:

```ini
[start_values]
U_wall = 0.3
zon5R1C.capMas.T = 291.15
```

- The key is the name of the variable in the FMU, in the same case. The value is in the unit of the FMU.
  A comment goes on its own line.
- A variable can be set if it is a parameter, an input that is not in the `.fmc` file, or has
  `initial="exact"` or `"approx"` in `modelDescription.xml`.
- `ecosim-client-fmu-v2` takes Real, Integer and Boolean variables. `ecosim-client-fmu-v3` takes Float32,
  Float64, the Int and UInt types and Boolean, but no arrays. A Boolean is `true`, `false`, `yes` or `no`.
- The client stops at start-up for a name the FMU does not have, a variable that cannot be set and a value
  of the wrong type. `--validate-fmu-file-only` reports the same.
- A value outside `min` and `max` of the FMU gets a warning at start-up and is set anyway. If the FMU does
  not accept it, the run fails at the start.
- The values the FMU gets are listed under `Start values` in the `CLIENT CONFIG` block at start-up.
- A restore with `--restore-simulation-run` needs the start values of the aborted run.
- The MATLAB, Pyro5 and Python clients do not read `[start_values]`.
"""
