# Usage of the Matlab-Client

- It is always assumed, that the user provides .m files, that have their functionality divided into three files
  setup.m, step.m, finishing.m
- Every additional pre- or postprocessing that is necessary, is assumed to be contained inside the respecting .m file
- Additional information (like .csv files) are also to be used inside the .m files.
- When timestamps are needed, the .m file should calculate it by using the given "client_time", which indicates the current simulated time in seconds
- For the usage of the input and output variables inside the .m files the Python naming convention of snake_case should be used
- If output values from the matlab client are used, they have to be initialized in the Matlab workspace in the setup.m file

## Install

- you need to install the version that matches your Matlab version
  - e.g. `pip install ecosim-client-matlab[R2024b]`

## Dev
- you need to install the library for your Matlab version
  - e.g.: `uv sync --extra dev --extra R2024b`
    - in the future, other Matlab version may be supported
