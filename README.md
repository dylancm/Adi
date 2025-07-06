# Claude Code Container Setup

A pre-configured Podman container with Claude Code installed and ready to use, providing a consistent development environment with Ubuntu, Node.js, and Claude Code pre-installed.

## Quick Start

1. **Run the container:**
   ```bash
   ./podman/launch-claude-container.sh
   ```

2. **Inside the container, start Claude Code:**
   ```bash
   claude
   ```

3. **Or run with a direct message:**
   ```bash
   ./podman/launch-claude-container.sh -m "your message here"
   ```

## Authentication

The container supports multiple authentication methods:

1. **Environment variable (recommended):**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ./podman/launch-claude-container.sh
   ```

2. **Host credentials:** If you've already run `claude auth` on your host, credentials will be automatically copied and merged.

## Features

### Container Components
- **Base:** Ubuntu latest with Node.js 20.x LTS
- **Runtime:** Claude Code installed globally via npm
- **MCP Servers:** Playwright MCP server pre-installed
- **User Setup:** Non-root user with proper permissions matching host UID/GID

### Pre-configured Settings
- **Dark theme:** Enabled by default
- **Notifications disabled:** Reduces noise during development  
- **Auto-update disabled:** Maintains consistent container environment
- **Trust dialog pre-accepted:** Streamlines initial setup
- **Smart configuration merge:** Preserves host authentication while applying container defaults

### MCP Server Support
- **Playwright:** Pre-installed globally for web automation and testing
- **GitHub:** Configured for GitHub API interactions
- **Context7:** SSE-based context server for enhanced capabilities

## File Structure

```
├── podman/
│   ├── claude-code-ubuntu.dockerfile    # Container definition
│   ├── launch-claude-container.sh       # Launch script with config merge
│   └── claude.template.json             # Default container settings
├── CLAUDE.md                            # Project guidance for Claude Code
└── README.md                            # This file
```

## Container Architecture

### Configuration Management
The launch script performs intelligent configuration merging:
1. Copies host credentials (`.credentials.json`)
2. Extracts user ID and OAuth account from host config
3. Applies container defaults while preserving authentication
4. Cleans up temporary files after container build

### Container Lifecycle
- **Ephemeral:** Container is stopped and recreated on each launch
- **Credential Management:** Host credentials are copied during build (not mounted)
- **File Permissions:** Container runs with host user's UID/GID for proper file access
- **Directory Mounting:** Current working directory is mounted to `/home/user/dev`

## Command Line Options

```bash
# Basic usage
./podman/launch-claude-container.sh

# Run with direct message
./podman/launch-claude-container.sh -m "your message here"

# Show help
./podman/launch-claude-container.sh -h
```

## Troubleshooting

### Common Issues
- **Authentication errors:** Ensure `ANTHROPIC_API_KEY` is set or `~/.claude/.credentials.json` exists
- **Permission issues:** Verify launch script is executable: `chmod +x podman/launch-claude-container.sh`
- **Container rebuild:** Delete existing image to force rebuild: `podman rmi claude-code-ubuntu`
- **jq dependency:** Launch script requires `jq` for configuration merging

### Build Process
The container is automatically built when:
- Image doesn't exist
- Dockerfile is newer than existing image
- Build includes user-specific UID/GID and username

### Security Considerations
- Non-root user execution inside container
- Credentials copied (not mounted) for security
- Temporary configuration files cleaned up after build
- User namespace mapping for proper file permissions