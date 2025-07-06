FROM ubuntu:latest

# Update package list and install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    gh \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (LTS)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# setup build args
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER_NAME=user

# Create a non-root group and user (UID/GID will be overridden at runtime)
RUN groupadd -g $GROUP_ID $USER_NAME && \
	useradd -m -s /bin/bash -u $USER_ID -g $GROUP_ID $USER_NAME

# Create Claude Code configuration directory and default settings
RUN mkdir -p /home/$USER_NAME/.claude && \
    mkdir -p /home/$USER_NAME/dev

COPY .credentials.json /home/$USER_NAME/.claude/
COPY .claude.json /home/$USER_NAME/

RUN chown -R $USER_NAME:$USER_NAME /home/$USER_NAME/.claude && \
    chown $USER_NAME:$USER_NAME /home/$USER_NAME/.claude.json && \
    chown -R $USER_NAME:$USER_NAME /home/$USER_NAME/dev

# Switch to non-root user
USER $USER_NAME

# Set PATH
ENV PATH="/home/$USER_NAME/.npm-global/bin:$PATH"

# Set the npm global cache dir
RUN npm config set prefix ~/.npm-global

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Install Playwright MCP server globally
RUN npm install -g @playwright/mcp

# Set working directory
WORKDIR /home/$USER_NAME/dev

# Set entrypoint and default command
CMD ["/bin/bash"]
