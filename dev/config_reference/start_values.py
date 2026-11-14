"""The start values section of the configuration reference."""

START_VALUES_TEXT = """## Start values

The `preferences.ini` of an FMU client can set variables of the FMU in a `[start_values]` section, for
example parameters, without exporting the FMU again. The client sets them after it loads the FMU and before
the FMU initializes, so they count from the first step on:

```ini
[start_values]
U_wall = 0.3
zon5R1C.capMas.T = 291.15
```

- The key is the name of the variable in the FMU, in the same case. Two keys that differ only in case count
  as the same key, and the client stops for them. A value is in the unit of the FMU, for example `K` for a
  temperature. A comment goes on a line of its own.
- A variable can be set if the FMU allows it before its initialization: a parameter, an input that is not in
  the `.fmc` file, or another variable with `initial="exact"` or `"approx"` in `modelDescription.xml`, such as
  the start value of a state. An input that is not in the `.fmc` file keeps the value for the whole run, as
  long as `simulation.json` does not connect it either. With `"approx"`, the value is only the first guess of
  an iteration, and the FMU calculates the real one.
- Constants, variables the FMU calculates, the time, structural parameters and the inputs in the `.fmc` file
  cannot be set.
- `ecosim-client-fmu-v2` takes Real, Integer and Boolean variables. `ecosim-client-fmu-v3` takes Float32,
  Float64, the Int and UInt types and Boolean, but no arrays. A Boolean is `true`, `false`, `yes` or `no`.
- At start-up the client stops for a name the FMU does not have, a variable that cannot be set or has another
  type, and a value that is not a number of that type or lies outside the `min` or `max` of the variable.
  `--validate-fmu-file-only` reports the same. The values the FMU gets are listed under `Start values` in the
  `CLIENT CONFIG` block at start-up.
- A section with a name close to `start_values`, like `[Start_Values]`, stops the client too, since its values
  would be left out without a word.
- A tool can fix a parameter when it exports the FMU. If the FMU marks it as a constant, the client stops.
  If the model only uses a parameter in some cases, a new value may change nothing, so check the effect on a
  short run.
- A restore with `--restore-simulation-run` needs the start values of the aborted run.
- The MATLAB, Pyro5 and Python clients do not read `[start_values]`.
"""
