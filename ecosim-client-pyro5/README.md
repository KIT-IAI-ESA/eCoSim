# Usage of the Pyro Client
- The Pyro Client can be used to simulate with external Python files, which provide a pyro object
- In the new Pyro Config [Pyro] inside the preferences.ini of a Pyro client three values have to be entered
  - pyro_host: Name of the host or IP-address, where the Python file with the active Pyro object is running
  - pyro_port: Port that pyro uses for connection. This should be a different to the database and server port
  - pyro_object_name: The name of the provided Pyro-Object
- The external Python file, providing the Pyro connection, should use these functions as interfaces to the simulator
  - initialize(): Do things here, that need to be done before the simulation is started
  - do_step(value_dict): Everything that needs to be done during each simulation step. Necessary data from other simulators is inside
    this value dictionary. At the end of the function a dictionary of the outputs for the other simulators should be given
  - clear(): Things to be done after the simulation ends
