import ast

from config_reference.start_values import START_VALUES_TEXT

CLIENT_TYPES_INTRO = """## Client types

`type` in the `[simulator]` section takes one of these values, in upper or lower case:
"""
CLIENT_TYPES_OUTRO = """
Any other value stops the client with `Unknown client type`. The value does not choose how the model
runs, the command does: `ecosim-client-fmu-v2` runs its FMU whatever `type` says.
"""
LISTS_TEXT = """## Lists

A key of type list is written in square brackets, with commas between the entries. Quotes around an
entry are optional. A client's `preferences.ini` with its two lists:

```ini
[server]
ip = localhost
port = 1234

[simulator]
simulator_name = house
model_name = house
type = fmu_2
fmc_file = [house.fmc]

[fmu]
fmu_file = [house.fmu]
```

Without brackets, as in `fmc_file = house.fmc`, the client stops with an error. The clients only read the
first entry of `fmc_file` and `fmu_file`.
"""
INTERFACE_FILES_TEXT = """## Interface files

The `.fmc` file named by `fmc_file` is a JSON file with the interfaces of the model, saved as UTF-8. Its
path is relative to the ini file. The `house.fmc` of the example above:

```json
{
  "inputs": [{"name": "weatherBus_TDryBul", "unit": "K", "description": "Outdoor air temperature", "required": "true"}],
  "outputs": [{"name": "T_indoor", "unit": "K"}]
}
```

A list that is left out counts as empty. The `weather.fmc` of a model without inputs:

```json
{"outputs": [{"name": "weatherBus.TDryBul", "unit": "K"}]}
```

The list decides whether an entry is an input or an output, so `type` and `connected_to` are not read
here. Neither are `fmu-file` and `modeldescription`, which the files of the examples contain. The client logs a
warning for any other unknown key and for a name that is twice in `inputs` or `outputs`.
"""
INTERFACE_KEYS_TEXT = """## Interface keys

The interface files and `simulators` in the simulation config describe an interface with these keys:

| Key | In the `.fmc` file | In `simulation.json` | Value |
| --- | --- | --- | --- |
| `name` | required | required | The same in both files, and the name in the model |
| `type` | not read | required | `Input` or `Output`, in upper or lower case |
| `required` | optional | optional | `true` or `false`, or a string: `"true"`, `"yes"`, `"false"`, `"no"`, in upper or lower case. Default `false`. |
| `unit` | optional | optional | Free text. Values are passed on as they are, nothing converts or compares units. |
| `description` | optional | optional | Free text |
| `connected_to` | not read | required on inputs | A list with one entry: the output the input gets its value from |

- `name` in the model is the variable of the FMU, the key in the dictionaries of the Python model or
  the Pyro object, or the variable in the MATLAB workspace.
- `required` in `simulation.json`: if the `.fmc` file does not list the interface, the server rejects the
  client and logs the interface. Without `required` the client logs a warning.
- `required` in the `.fmc` file only counts for inputs: the client logs a warning if `simulation.json` does
  not connect the input.
- `connected_to` holds `simulator`, the position of the output's simulator in `simulators`, counting
  from 0, and `interface`, the `name` of the output. `simulator` can be a number or a string.
  An input with a logical delay also has `delay_path`, see [Logical delays](#logical-delays).
- The run only uses the interfaces in `simulation.json`, so the `.fmc` file may list more.
- At load, the server lists every bad `connected_to`: every input needs one, the target has to
  exist and be an output, and an output of the same simulator needs a logical delay.
- With PostgreSQL storage, names stop the server at start-up if they are too long (`name` over 60
  bytes, simulator name over 56) or would share a column or table.

A complete `simulation.json` for the two models above. Unlike the shortened example, it loads as it is:

```json
{
  "simulators": [
    {
      "name": "weather",
      "model": "weather",
      "interfaces": [{"name": "weatherBus.TDryBul", "type": "Output", "unit": "K"}]
    },
    {
      "name": "house",
      "model": "house",
      "interfaces": [
        {
          "name": "weatherBus_TDryBul",
          "type": "Input",
          "required": "true",
          "unit": "K",
          "connected_to": [{"simulator": "0", "interface": "weatherBus.TDryBul"}]
        },
        {"name": "T_indoor", "type": "Output", "unit": "K"}
      ]
    }
  ],
  "logical_delays": [],
  "setup": {"delta_t": "900000"}
}
```

- `name` and `model` of a simulator have to match `simulator_name` and `model_name` in the ini file
  of its client.
- `logical_delays` has to be present, with `[]` if there are none.
"""


def accepted_values(member: str | tuple[str, tuple[str, ...]]) -> list[str]:
    if isinstance(member, str):
        return [member]
    serialized, alternatives = member
    return [serialized, *alternatives]


def client_type_values(source: str) -> list[list[str]]:
    """The values each ClientType member accepts, the serialized one first."""
    classes = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ClassDef)]
    body = next(node.body for node in classes if node.name == "ClientType")
    return [accepted_values(ast.literal_eval(statement.value)) for statement in body if isinstance(statement, ast.Assign)]


def render_client_types(client_types: list[list[str]]) -> str:
    lines = ["| Value | Also accepted |", "| --- | --- |"]
    for serialized, *alternatives in client_types:
        lines.append(f"| `{serialized}` | {', '.join(f'`{alternative}`' for alternative in alternatives)} |")
    return "\n".join(lines)


def render_client_sections(client_types: list[list[str]]) -> str:
    return "\n".join([CLIENT_TYPES_INTRO, render_client_types(client_types), CLIENT_TYPES_OUTRO, LISTS_TEXT, START_VALUES_TEXT, INTERFACE_FILES_TEXT])
