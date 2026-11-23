# the build and the final image share the same Python, so the venv finds its Python in the final image
ARG PYTHON_VERSION=3.14
ARG DEBIAN_RELEASE=trixie

FROM astral/uv:0.13.7-python${PYTHON_VERSION}-${DEBIAN_RELEASE}-slim AS build

ARG SOURCE_DIR

# dedicated venv to be able to easily copy it in the final stage
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
# pre-compile each file to .pyc, so on a new container start everything is already compiled
ENV UV_COMPILE_BYTECODE=1
# prevent `uv` from downloading a different python interpreter -> this would later break the link in the copied `/opt/venv`
ENV UV_PYTHON_DOWNLOADS=never

COPY ecosim-common /src/ecosim-common
COPY ecosim-test-common /src/ecosim-test-common
COPY ecosim-common-fmpy /src/ecosim-common-fmpy

COPY ${SOURCE_DIR} /src/${SOURCE_DIR}

WORKDIR /src/${SOURCE_DIR}
# non-editable: the project and its editable sources (see [tool.uv.sources]) would otherwise only be linked to /src,
# which the final stage does not copy; this way the packages are copied into the venv
RUN uv sync --locked --no-editable


FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE}

ARG COMMAND_NAME

COPY --from=build /opt/venv /opt/venv
# '/opt/ecosim' is a fixed name, because the exec form of ENTRYPOINT below does not expand variables
RUN ln -s /opt/venv/bin/${COMMAND_NAME} /opt/ecosim

# ENTRYPOINT instead of CMD, so that arguments are appended to the executable instead of replacing it
ENTRYPOINT ["/opt/ecosim"]
