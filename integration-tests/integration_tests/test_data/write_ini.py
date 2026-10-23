import json
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser

Sections = dict[str, dict[str, str]]


def _interfaces(names: list[str], required: bool) -> list[dict[str, str]]:
    return [{"name": name, "unit": "", "description": "", "required": str(required).lower()} for name in names]


def write_fmc(directory: Path, inputs: list[str], outputs: list[str]) -> str:
    fmc_file = directory / "model.fmc"
    fmc_file.write_text(json.dumps({"inputs": _interfaces(inputs, required=True), "outputs": _interfaces(outputs, required=False)}))
    return fmc_file.name


def write_client_ini(
    directory: Path,
    client_type: str,
    model_name: str,
    fmc_file: str,
    extra_sections: Sections | None = None,
) -> ConfigParser:
    sections: Sections = {
        "server": {"ip": "localhost", "port": "1234"},
        "simulator": {"simulator_name": client_type, "model_name": model_name, "fmc_file": f"[{fmc_file}]", "type": client_type},
        **(extra_sections or {}),
    }
    ini_file = directory / "client.ini"
    ini_file.write_text(
        "\n".join(f"[{section}]\n" + "\n".join(f"{key}={value}" for key, value in entries.items()) for section, entries in sections.items()),
    )
    return ConfigParser(ini_file)
