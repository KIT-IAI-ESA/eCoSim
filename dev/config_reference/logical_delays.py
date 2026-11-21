LOGICAL_DELAYS_TEXT = """## Logical delays

A logical delay hands the value of an output to an input a number of steps later. It breaks a loop of models
that wait for each other's values in the same step. An input connected to an output of its own simulator always
needs one. `ecosim new --logical-delay` writes a delay of one step, see
[Other names and loops](../getting-started/your-own-models.md#other-names-and-loops).

The [Docker example](../guides/docker.md) hands the room temperature of the house to its two controllers one step
later. Shortened to the heating, whose `T_room` gets `room_temperature` of the house, simulator 1 in `simulators`:

```json
{
  "simulators": [
    {
      "name": "heating",
      "model": "heating",
      "interfaces": [
        {
          "name": "T_room",
          "type": "Input",
          "connected_to": [{"simulator": "1", "interface": "room_temperature", "delay_path": ["1"]}]
        }
      ]
    }
  ],
  "logical_delays": [
    {
      "delay": "1",
      "output_connections": [
        {"destination_simulator_name": "heating", "destination_interface_name": "T_room", "start_value": "293.15"}
      ]
    }
  ]
}
```

- `delay`: the number of steps, a whole number of at least 1.
- `output_connections`: the inputs that get the value later. `destination_simulator_name` is the `name` of the
  simulator and `destination_interface_name` the `name` of the input. One delay can list several inputs, the one
  in the Docker example also lists `T_room` of the ventilation.
- `start_value`: what the input gets until the first delayed value arrives. A number, or a list of numbers, also
  nested, for an input that takes a list. Numbers can be written as strings.
- `delay_path` in the `connected_to` of the input: the position of the delay in `logical_delays` as a string,
  counting from 1, so `["1"]` names the first delay. An `id` of a delay is not read.
- The input and the delay have to name each other. If the delay lists an input whose `delay_path` does not
  name the delay, or the other way round, the server stops when it loads the config.

With a `delay` of N, the input gets `start_value` in the first N steps and after that the value the output had
N steps earlier. With a `delay` of 2 it gets `start_value` in steps 1 and 2, the value of step 1 in step 3, the
value of step 2 in step 4, and so on. If the output sends no value in a step, its last value counts for that step.
After a restore with `--restore-simulation-run` the delays start again with `start_value`, so the first steps after
the restore can differ from a run without the abort.
"""
