# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code container setup project that provides a pre-configured Podman container with Claude Code installed and ready to use. The project creates a development environment with Ubuntu, Node.js, and Claude Code pre-installed.

## Common Development Commands

### Container Management
```bash
# Launch the Claude Code container (mounts current directory)
./podman/launch-claude-container.sh

# Inside the container, start Claude Code
claude

# Rebuild container (if needed)
podman rmi claude-code-ubuntu
./podman/launch-claude-container.sh
```

### Authentication Setup
```bash
# Set API key before launching (recommended)
export ANTHROPIC_API_KEY="your-api-key"
./podman/launch-claude-container.sh

# Or ensure host credentials exist
claude auth  # run on host first
```

## Architecture

### Container Components
- **Base**: Ubuntu latest with Node.js 20.x LTS
- **Runtime**: Claude Code installed globally via npm
- **MCP Servers**: Playwright MCP server pre-installed
- **User Setup**: Non-root user with proper permissions
- **Configuration**: Smart merge of host and container settings

### File Structure
```
├── podman/
│   ├── claude-code-ubuntu.dockerfile    # Container definition
│   ├── launch-claude-container.sh       # Launch script with config merge
│   └── claude.template.json             # Default container settings
└── README.md                            # User documentation
```

### Configuration Management
The launch script performs intelligent configuration merging:
1. Copies host credentials (`.credentials.json`)
2. Merges user ID and OAuth account from host config
3. Applies container defaults (dark theme, disabled notifications/updates)
4. Cleans up temporary files after container build

### Container Features
- **Pre-configured theme**: Dark mode enabled by default
- **Notifications disabled**: Reduces noise during development
- **Auto-update disabled**: Maintains consistent container environment
- **Trust dialog pre-accepted**: Streamlines initial setup

## Development Notes

### Container Lifecycle
- Container is ephemeral - stopped and recreated on each launch
- Host credentials are copied during build, not mounted
- Configuration is merged at launch time to preserve authentication
- Current working directory is mounted to `/home/user/dev` in the container
- Container runs with host user's UID/GID for proper file permissions

### Troubleshooting
- **Authentication errors**: Ensure `ANTHROPIC_API_KEY` is set or host credentials exist
- **Permission issues**: Verify launch script is executable
- **Build issues**: Delete existing image to force rebuild

### MCP Servers
The container includes pre-configured MCP servers:
- **Playwright**: Pre-installed globally for web automation and testing
- **GitHub**: Configured for GitHub API interactions
- **Context7**: SSE-based context server

### Security Considerations
- Uses non-root user inside container
- Credentials are copied (not mounted) for security
- Temporary files are cleaned up after build