FROM node:latest

RUN useradd -m -s /bin/bash opencode

RUN npm install -g opencode-ai

USER opencode

RUN mkdir -p "/home/opencode/.config/opencode"
RUN mkdir -p "/home/opencode/.local/share/opencode"
WORKDIR /home/opencode/.config/opencode

CMD ["opencode", "serve", "--print-logs", "--log-level", "DEBUG"]
