FROM astral/uv:0.12.5-python3.12-trixie-slim as BUILD

ARG BUILD_DIR=/opt/ecosim
ARG SOURCE_DIR
ARG COMMAND_NAME

RUN uv tool install pex==2.100.7

COPY ecosim-common ${BUILD_DIR}/ecosim-common
COPY ecosim-test-common ${BUILD_DIR}/ecosim-test-common
COPY ecosim-common-fmpy ${BUILD_DIR}/ecosim-common-fmpy
RUN find ${BUILD_DIR} -name .venv -maxdepth 3 -type d -prune -exec rm -rf {} +
RUN find ${BUILD_DIR} -name dist -maxdepth 3 -type d -prune -exec rm -rf {} +

RUN cd ${BUILD_DIR}/ecosim-common && uv sync

# the copying (and venv deleting) of the actual source dir is done later
# so the tasks above can be cached and reused across different runs
COPY ${SOURCE_DIR} ${BUILD_DIR}/${SOURCE_DIR}
RUN rm -rf ${BUILD_DIR}/${SOURCE_DIR}/.venv
RUN rm -rf ${BUILD_DIR}/${SOURCE_DIR}/dist

WORKDIR ${BUILD_DIR}/${SOURCE_DIR}
RUN uv sync
RUN uv build --all-packages

# create PEX (python executable)
RUN uv export --no-dev --no-emit-workspace --no-hashes --format requirements-txt -o requirements.txt
RUN uvx pex -r requirements.txt dist/*.whl -c ${COMMAND_NAME} \
  --scie eager \
  -o ${BUILD_DIR}/${COMMAND_NAME}.pex


FROM python:3.12-slim

ARG BUILD_DIR=/opt/ecosim
ARG COMMAND_NAME
ENV EXECUTABLE=${COMMAND_NAME}.pex

COPY --from=BUILD ${BUILD_DIR}/${EXECUTABLE} /opt
# '/opt/ecosim' is a fixed name, because the exec form of ENTRYPOINT below does not expand variables
RUN chmod +x /opt/${EXECUTABLE} && ln -s /opt/${EXECUTABLE} /opt/ecosim

# ENTRYPOINT instead of CMD, so that arguments are appended to the executable instead of replacing it
ENTRYPOINT ["/opt/ecosim"]
