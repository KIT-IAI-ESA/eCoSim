from ecosim_common.config.config_parser import ConfigParser


class MatlabConfig:
    def __init__(
        self,
        config: ConfigParser,
    ):
        # Indicates the path where the .mat files are for execution. The three names used are setup, step and finish
        self.folder_path: str = config.get_string("matlab", "scriptfolder")
