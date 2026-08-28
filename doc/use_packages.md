# Use packages

- Package repository
    - Web: https://gitlab.kit.edu/kit/iai/esa/ecosim/-/packages
    - URL: https://gitlab.kit.edu/api/v4/projects/187427/packages/pypi/simple

## Install packages in your project

- create a private access token for Gitlab
    - User settings -> Personal access tokens -> Add new token
        - Name: e.g. `API_READ`
        - Scope: `read_api`
- setup the credentials
    - either use `netrc`
        - create `.netrc` file
            - Linux/OS X: `~/.netrc`
            - Windows: `%USERPROFILE%\_netrc`
            - Content
              ```text
              machine gitlab.kit.edu
              login TOKEN_NAME
              password TOKEN
              ```
    - or use environment variables
        - `export UV_INDEX_ECOSIM_REGISTRY_USERNAME=TOKEN_NAME`
        - `export UV_INDEX_ECOSIM_REGISTRY_PASSWORD=TOKEN`
            - the part between `UV_INDEX_` and `_USERNAME`/`_PASSWORD` must match with the `pyproject.toml` index name
    - replace `TOKEN_NAME` with the name of the token (e.g. `API_READ`)
    - replace `TOKEN` with the actual token (the token is only accessible right after creation)
- add to your `pyproject.toml`
  ```toml
  [[tool.uv.index]]
  name= "ecosim-registry"
  url = "https://gitlab.kit.edu/api/v4/projects/187427/packages/pypi/simple"
  authenticate = "always"
  ```
- check, if you can access the repo
    - e.g. add the required ecosim dependencies and run `uv sync`
    - minimal `pyproject.toml`
      ```toml
      [project]
      name = "ecosim-test"
      version = "0.123"
      requires-python = ">=3.14"

      dependencies = [
          "ecosim-common>=1", # if you need a specific version, set it here
      ]

      [[tool.uv.index]]
      name= "ecosim-registry"
      url = "https://gitlab.kit.edu/api/v4/projects/187427/packages/pypi/simple"
      authenticate = "always"
      ```
