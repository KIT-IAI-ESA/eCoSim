from pathlib import Path

from ecosim_common.config.client_id import ClientID


def write_simulator_directory(directory: Path, client_id: ClientID, model_file: str | None, extra_ini_text: str = "") -> Path:
    """Returns the ini file."""
    directory.mkdir()
    ini_file = directory / "preferences.ini"
    ini_file.write_text(
        f"[simulator]\nsimulator_name={client_id.simulator_name}\nmodel_name={client_id.model_name}\nfmc_file=[model.fmc]\ntype=fmu\n"
        + extra_ini_text,
    )
    if model_file is not None:
        (directory / model_file).touch()
    return ini_file
