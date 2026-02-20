from ecosim_common.config.config_parser import ConfigParser


class PyroConfig:
    def __init__(
        self,
        config: ConfigParser,
    ):
        self.host: str = config.get_string('pyro', 'pyro_host')
        self.port: str = config.get_string('pyro', 'pyro_port')
        self.object_name: str = config.get_string('pyro', 'pyro_object_name')
