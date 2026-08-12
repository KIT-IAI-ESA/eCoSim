# Setup OpenCode

## KIToolbox

- copy the opencode-auth.json.example to `opencode-auth.kit.json`
- fill-in your API key
    - check the official documentation how to receive your API key: https://www.zml.kit.edu/downloads/KI.Toolbox_API.pdf
- run `start-open-code-docker-kit.sh` to run open code set up with KIT KIToolbox
- open in browser: `http://localhost:29333`

#### Further notes
- Open API doc: https://ki-toolbox.scc.kit.edu/docs

## Custom provider

_Please note: all *custom* files are ignored by GIT_

- create `opencode.custom.json` and fill in your provider
- create `opencode-auth.custom.json` and fill in your authentication details
- run `start-open-code-docker-custom.sh`
- open in browser: `http://localhost:29334`
