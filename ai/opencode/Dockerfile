FROM node:24-trixie

ARG OPENCODE_VERSION=1.18.16
RUN npm install -g opencode-ai@${OPENCODE_VERSION}

RUN mkdir -p /home/node/.config/opencode \
             /home/node/.local/share/opencode \
             /home/node/.cache/opencode \
             /home/node/ecosim \
 && chown -R node:node /home/node

USER node
ENV HOME=/home/node
WORKDIR /home/node/ecosim

CMD ["opencode", "serve", "--hostname", "0.0.0.0", "--port", "29333", \
     "--print-logs", "--log-level", "DEBUG"]
