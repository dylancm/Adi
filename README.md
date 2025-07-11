# Claude Code Container Setup

A pre-configured Podman container with Claude Code installed and ready to use, providing a consistent development environment with Ubuntu, Node.js, and Claude Code pre-installed.

## Why Use This Container?

- **Consistent Environment**: Same Claude Code version and dependencies across all machines
- **Isolated Setup**: Container prevents conflicts with host system packages
- **Pre-configured**: Dark theme, optimized settings, and MCP servers ready out-of-the-box
- **Zero Setup**: No need to install Node.js, npm, or manage Claude Code versions manually
- **Secure**: Credentials are safely handled with proper permission management

## Prerequisites

- **Podman**: Ensure Podman is installed and running
- **jq**: Required for configuration merging (`apt install jq` on Ubuntu/Debian)
- **Permissions**: Make sure the launch script is executable

## Quick Start

1. **Set up authentication (choose one method):**
   ```bash
   # Option 1: Environment variable (recommended)
   export ANTHROPIC_API_KEY="your-api-key"
   
   # Option 2: Use existing host credentials
   claude auth  # run this on your host first
   ```

2. **Run the container:**
   ```bash
   ./podman/launch-claude-container.sh
   ```

3. **Inside the container, start Claude Code:**
   ```bash
   claude
   ```

4. **Or run with a direct message:**
   ```bash
   ./podman/launch-claude-container.sh -m "your message here"
   ```

## Authentication Details

The container supports multiple authentication methods with automatic credential management:

1. **Environment variable (recommended):**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ./podman/launch-claude-container.sh
   ```

2. **Host credentials:** If you've already run `claude auth` on your host, credentials will be automatically copied and merged.

3. **OAuth Integration:** Existing OAuth tokens from host are preserved and integrated with container settings.

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
# Basic usage - launches interactive Claude Code session
./podman/launch-claude-container.sh

# Run with direct message - execute single command and exit
./podman/launch-claude-container.sh -m "your message here"

# Force rebuild of container image (ignores cache)
./podman/launch-claude-container.sh --no-cache

# Set permission mode for Claude Code execution
./podman/launch-claude-container.sh --permission-mode plan -m "your message"

# Show help and usage information
./podman/launch-claude-container.sh -h

# Examples
./podman/launch-claude-container.sh -m "List all Python files in this directory"
./podman/launch-claude-container.sh -m "Run the tests and show me the results"
./podman/launch-claude-container.sh --permission-mode acceptEdits -m "Fix the linting errors"
./podman/launch-claude-container.sh --no-cache -m "Analyze this codebase"
```

### Available Options

- `-m, --message MESSAGE` - Run Claude Code with a specific message and exit
- `--no-cache` - Force rebuild of container image, ignoring existing cache
- `--permission-mode MODE` - Set permission mode for Claude Code execution
  - `default` - Use default permission handling
  - `acceptEdits` - Automatically accept file edits
  - `plan` - Run in planning mode only
  - `bypassPermissions` - Skip all permission checks
- `-h, --help` - Show help message and usage information

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

## Advanced Usage

### Custom Configuration
You can customize the container settings by modifying `podman/claude.template.json` before building:

```json
{
  "appearance": {
    "theme": "dark",
    "fontSize": 14
  },
  "behavior": {
    "notifications": false,
    "autoUpdate": false
  }
}
```

### Rebuilding the Container
To rebuild the container with updates:

```bash
# Option 1: Use --no-cache flag (recommended)
./podman/launch-claude-container.sh --no-cache

# Option 2: Manual rebuild
podman rmi claude-code-ubuntu
./podman/launch-claude-container.sh
```

### Using with Different Projects
The container mounts your current working directory, so you can use it with any project:

```bash
cd /path/to/your/project
/path/to/claude-container/podman/launch-claude-container.sh
```

## Contributing

Feel free to submit issues and enhancement requests. When contributing:

1. Test your changes with the container
2. Update documentation as needed
3. Follow the existing code style
4. Ensure security best practices are maintained