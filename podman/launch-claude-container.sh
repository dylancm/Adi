#!/bin/bash

# Script to launch a Podman container with Ubuntu and Claude Code pre-installed
# Shares the host's Claude Code credentials and current directory

set -e

# Parse command line arguments
MESSAGE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--message)
            MESSAGE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -m, --message MESSAGE    Run 'claude -p MESSAGE' after container starts"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
IMAGE_NAME="claude-code-ubuntu"
CONTAINER_NAME="claude-code-dev"
DOCKERFILE="$SCRIPT_DIR/claude-code-ubuntu.dockerfile"
TEMPLATE_FILE="$SCRIPT_DIR/claude.template.json"

# Get current user's UID, GID and username
USER_UID=$(id -u)
USER_GID=$(id -g)
USER_NAME=$(whoami)
CWD=$(pwd)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Claude Code Container Launcher${NC}"

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${YELLOW}Warning: $DOCKERFILE not found in script directory${NC}"
    exit 1
fi

# Prepare Claude configuration files
echo -e "${GREEN}Preparing Claude configuration files...${NC}"

# Copy credentials file
if [ -f "$HOME/.claude/.credentials.json" ]; then
    cp "$HOME/.claude/.credentials.json" "$SCRIPT_DIR/.credentials.json"
    echo -e "${BLUE}Copied credentials file${NC}"
else
    echo -e "${YELLOW}Warning: ~/.claude/.credentials.json not found${NC}"
    exit 1
fi

# Create .claude.json from template with user's config
if [ -f "$HOME/.claude.json" ] && [ -f "$TEMPLATE_FILE" ]; then
    # Extract userId and oauthAccount from user's config using jq
    USER_ID=$(jq -r '.userID // .userId // ""' "$HOME/.claude.json" 2>/dev/null || echo "")
    OAUTH_ACCOUNT=$(jq -c '.oauthAccount // {}' "$HOME/.claude.json" 2>/dev/null || echo "{}")
    
    # Update template with user's data and replace $USER_NAME
    jq --arg userId "$USER_ID" --argjson oauthAccount "$OAUTH_ACCOUNT" --arg userName "$USER_NAME" \
       '.userID = $userId | .oauthAccount = $oauthAccount | 
        .projects = (.projects | to_entries | map(
          .key |= sub("\\$USER_NAME"; $userName)
        ) | from_entries)' \
       "$TEMPLATE_FILE" > "$SCRIPT_DIR/.claude.json"
    
    echo -e "${BLUE}Created .claude.json with user configuration${NC}"
else
    echo -e "${YELLOW}Warning: ~/.claude.json or $TEMPLATE_FILE not found${NC}"
    exit 1
fi

# Build the image if it doesn't exist or if Dockerfile is newer
if ! podman image exists "$IMAGE_NAME" || [ "$DOCKERFILE" -nt "$(podman image inspect $IMAGE_NAME --format '{{.Created}}' 2>/dev/null || echo '1970-01-01')" ]; then
    echo -e "${GREEN}Building Claude Code Ubuntu image...${NC}"
    podman build -f "$DOCKERFILE" \
	    --build-arg USER_ID=$USER_UID \
	    --build-arg GROUP_ID=$USER_GID \
	    --build-arg USER_NAME=$USER_NAME \
	    -t "$IMAGE_NAME" "$SCRIPT_DIR"
fi

# Clean up temporary files
echo -e "${GREEN}Cleaning up temporary files...${NC}"
rm -f "$SCRIPT_DIR/.credentials.json" "$SCRIPT_DIR/.claude.json"

# Stop and remove existing container if running
if podman container exists "$CONTAINER_NAME"; then
    echo -e "${YELLOW}Stopping existing container...${NC}"
    podman stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    podman rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

echo -e "${GREEN}Starting Claude Code container...${NC}"
echo -e "${BLUE}Container name: $CONTAINER_NAME${NC}"
echo -e "${BLUE}Working directory: /home/$USER_NAME/dev${NC}"
echo -e "${BLUE}Host directory mounted: $CWD${NC}"
echo -e "${BLUE}Type 'claude' to start Claude Code${NC}"
echo -e "${BLUE}Type 'exit' to stop the container${NC}"
echo ""

# Run the container
if [ -n "$MESSAGE" ]; then
    echo -e "${BLUE}Running claude -p \"$MESSAGE\" after container starts...${NC}"
    podman run -it \
        --name "$CONTAINER_NAME" \
        --hostname claude-dev \
        --user "$USER_UID:$USER_GID" \
        --volume "$CWD:/home/$USER_NAME/dev:Z" \
        --userns=keep-id \
        "$IMAGE_NAME" \
        bash -c "claude -p --dangerously-skip-permissions \"$MESSAGE\""
else
    podman run -it \
        --name "$CONTAINER_NAME" \
        --hostname claude-dev \
        --user "$USER_UID:$USER_GID" \
        --volume "$CWD:/home/$USER_NAME/dev:Z" \
        --userns=keep-id \
        "$IMAGE_NAME"
fi

echo -e "${GREEN}Container stopped${NC}"
