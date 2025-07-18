#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "click>=8.0.0",
# ]
# ///

"""
Script to launch a Podman container with Ubuntu and Claude Code pre-installed.
Creates a git worktree for isolated development environment.
Shares the host's Claude Code credentials and mounts worktree as working directory.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


class ClaudeContainerLauncher:
    # Embedded content - dockerfile
    DOCKERFILE_CONTENT = """FROM ubuntu:latest

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
"""

    # Embedded content - template
    TEMPLATE_CONTENT = """{
	"numStartups": 1,
	"installMethod": "unknown",
	"autoUpdates": true,
	"tipsHistory": {
		"new-user-warmup": 1
	},
	"userID": "",
	"projects": {
		"/home/$USER_NAME/dev": {
			"allowedTools": [],
			"history": [],
			"mcpContextUris": [],
			"mcpServers": {},
			"enabledMcpjsonServers": [],
			"disabledMcpjsonServers": [],
			"hasTrustDialogAccepted": true,
			"projectOnboardingSeenCount": 1,
			"hasClaudeMdExternalIncludesApproved": false,
			"hasClaudeMdExternalIncludesWarningShown": false
		}
	},
	"oauthAccount": {
	},
	"hasCompletedOnboarding": true,
	"mcpServers": {
    "context7": {
      "type": "sse",
      "url": "https://mcp.context7.com/sse"
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_GITHUB_TOKEN_HERE"
      }
    },
		"playwright": {
			"command": "npx",
			"args": [
				"@playwright/mcp@latest"
			]
		}
  }
}
"""

    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        # Create temporary directory for embedded files
        self.temp_dir = Path(tempfile.mkdtemp())
        self.dockerfile = self.temp_dir / "claude-code-ubuntu.dockerfile"
        self.template_file = self.temp_dir / "claude.template.json"

        # Extract embedded files
        self.dockerfile.write_text(self.DOCKERFILE_CONTENT)
        self.template_file.write_text(self.TEMPLATE_CONTENT)

        # Set up cleanup
        import atexit
        atexit.register(self._cleanup_temp_dir)
        self.image_name = "claude-code-ubuntu"
        self.container_name = "claude-code-dev"
        
        # Get user information
        self.user_uid = os.getuid()
        self.user_gid = os.getgid()
        self.user_name = os.environ.get('USER', 'user')
        self.cwd = Path.cwd()
        
        # Worktree state
        self.worktree_path: Optional[Path] = None
        self.worktree_created = False
        self.cleanup_worktree = True

    def parse_args(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Launch a Podman container with Claude Code pre-installed"
        )
        parser.add_argument(
            "-m", "--message",
            help="Run 'claude -p MESSAGE' after container starts"
        )
        parser.add_argument(
            "--no-cache",
            action="store_true",
            help="Force rebuild of container image"
        )
        parser.add_argument(
            "--permission-mode",
            help="Set permission mode (default, acceptEdits, plan, bypassPermissions)"
        )
        parser.add_argument(
            "--worktree-branch",
            help="Create worktree from specific branch/commit (default: current HEAD)"
        )
        parser.add_argument(
            "--keep-worktree",
            action="store_true",
            help="Keep worktree after container stops"
        )
        parser.add_argument(
            "--no-worktree",
            action="store_true",
            help="Mount current directory instead of creating worktree"
        )
        parser.add_argument(
            "--worktree-path",
            type=Path,
            help="Use existing worktree at specified path"
        )
        return parser.parse_args()

    def print_colored(self, message: str, color: str = Colors.NC) -> None:
        print(f"{color}{message}{Colors.NC}", file=sys.stderr)

    def run_command(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        return subprocess.run(cmd, **kwargs)

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def create_worktree(self, branch_or_commit: str = "HEAD") -> Path:
        """Create a git worktree and return its path."""
        if not self.is_git_repo():
            self.print_colored(
                "Error: Not in a git repository. Worktree requires a git repository.",
                Colors.YELLOW
            )
            sys.exit(1)
        
        worktree_path = self.cwd / "claude_wt"
        
        self.print_colored(f"Creating git worktree 'claude_wt' from '{branch_or_commit}'...", Colors.GREEN)
        
        try:
            subprocess.run(
                ["git", "worktree", "add", "-b", "claude_wt", "wt_temp/"],
                check=True,
                capture_output=True
            )
            self.print_colored(f"Worktree created at: {worktree_path}", Colors.BLUE)
            self.worktree_created = True
            return worktree_path
        except subprocess.CalledProcessError:
            self.print_colored(
                "Failed to create worktree. Using current directory instead.",
                Colors.YELLOW
            )
            return self.cwd

    def cleanup_worktree_if_needed(self) -> None:
        """Clean up worktree if it was created and cleanup is enabled."""
        if (self.worktree_path and 
            self.cleanup_worktree and 
            self.worktree_created):
            self.print_colored("Cleaning up worktree...", Colors.GREEN)
            try:
                # Check if worktree exists in git worktree list
                result = subprocess.run(
                    ["git", "worktree", "list", "--porcelain"],
                    capture_output=True,
                    text=True
                )
                if str(self.worktree_path) in result.stdout:
                    subprocess.run(
                        ["git", "worktree", "remove", str(self.worktree_path), "--force"],
                        capture_output=True
                    )
            except subprocess.CalledProcessError:
                pass

    def prepare_claude_config(self) -> None:
        """Prepare Claude configuration files."""
        self.print_colored("Preparing Claude configuration files...", Colors.GREEN)
        
        # Copy credentials file
        credentials_src = Path.home() / ".claude" / ".credentials.json"
        credentials_dest = self.script_dir / ".credentials.json"
        
        if credentials_src.exists():
            shutil.copy2(credentials_src, credentials_dest)
            self.print_colored("Copied credentials file", Colors.BLUE)
        else:
            self.print_colored("Warning: ~/.claude/.credentials.json not found", Colors.YELLOW)
            sys.exit(1)
        
        # Create .claude.json from template
        user_config = Path.home() / ".claude.json"
        if user_config.exists() and self.template_file.exists():
            try:
                with open(user_config) as f:
                    user_data = json.load(f)
                
                with open(self.template_file) as f:
                    template_data = json.load(f)
                
                # Extract user information
                user_id = user_data.get("userID") or user_data.get("userId", "")
                oauth_account = user_data.get("oauthAccount", {})
                
                # Update template with user data
                template_data["userID"] = user_id
                template_data["oauthAccount"] = oauth_account
                
                # Replace $USER_NAME in projects
                if "projects" in template_data:
                    updated_projects = {}
                    for key, value in template_data["projects"].items():
                        updated_key = key.replace("$USER_NAME", self.user_name)
                        updated_projects[updated_key] = value
                    template_data["projects"] = updated_projects
                
                # Write updated config
                config_dest = self.script_dir / ".claude.json"
                with open(config_dest, "w") as f:
                    json.dump(template_data, f, indent=2)
                
                self.print_colored("Created .claude.json with user configuration", Colors.BLUE)
                
            except (json.JSONDecodeError, KeyError, IOError) as e:
                self.print_colored(f"Error processing configuration: {e}", Colors.YELLOW)
                sys.exit(1)
        else:
            self.print_colored("Warning: ~/.claude.json or template file not found", Colors.YELLOW)
            sys.exit(1)

    def should_build_image(self, no_cache: bool) -> bool:
        """Check if image should be built."""
        if no_cache:
            return True
        
        # Check if image exists
        result = subprocess.run(
            ["podman", "image", "exists", self.image_name],
            capture_output=True
        )
        if result.returncode != 0:
            return True
        
        # Check if Dockerfile is newer than image
        try:
            result = subprocess.run(
                ["podman", "image", "inspect", self.image_name, "--format", "{{.Created}}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # For simplicity, always rebuild if Dockerfile exists
                return self.dockerfile.exists()
        except subprocess.CalledProcessError:
            pass
        
        return False

    def build_image(self, no_cache: bool) -> None:
        """Build the container image."""
        self.print_colored("Building Claude Code Ubuntu image...", Colors.GREEN)
        
        build_args = [
            "podman", "build",
            "-f", str(self.dockerfile),
            "--build-arg", f"USER_ID={self.user_uid}",
            "--build-arg", f"GROUP_ID={self.user_gid}",
            "--build-arg", f"USER_NAME={self.user_name}",
            "-t", self.image_name,
        ]
        
        if no_cache:
            build_args.append("--no-cache")
        
        build_args.append(str(self.script_dir))
        
        subprocess.run(build_args, check=True)

    def cleanup_temp_files(self) -> None:
        """Clean up temporary configuration files."""
        self.print_colored("Cleaning up temporary files...", Colors.GREEN)
        temp_files = [
            self.script_dir / ".credentials.json",
            self.script_dir / ".claude.json"
        ]
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()

    def stop_existing_container(self) -> None:
        """Stop and remove existing container if running."""
        result = subprocess.run(
            ["podman", "container", "exists", self.container_name],
            capture_output=True
        )
        if result.returncode == 0:
            self.print_colored("Stopping existing container...", Colors.YELLOW)
            subprocess.run(
                ["podman", "stop", self.container_name],
                capture_output=True
            )
            subprocess.run(
                ["podman", "rm", self.container_name],
                capture_output=True
            )

    def run_container(self, mount_path: Path, message: Optional[str], permission_mode: Optional[str]) -> None:
        """Run the container."""
        self.print_colored("Starting Claude Code container...", Colors.GREEN)
        self.print_colored(f"Container name: {self.container_name}", Colors.BLUE)
        self.print_colored(f"Working directory: /home/{self.user_name}/dev", Colors.BLUE)
        self.print_colored(f"Host directory mounted: {mount_path}", Colors.BLUE)
        
        if mount_path != self.cwd:
            self.print_colored(f"Worktree will be {'preserved' if not self.cleanup_worktree else 'cleaned up'} after container stops", Colors.BLUE)
        
        self.print_colored("Type 'claude' to start Claude Code", Colors.BLUE)
        self.print_colored("Type 'exit' to stop the container", Colors.BLUE)
        print("")
        
        run_args = [
            "podman", "run", "-it",
            "--name", self.container_name,
            "--hostname", "claude-dev",
            "--user", f"{self.user_uid}:{self.user_gid}",
            "--volume", f"{mount_path}:/home/{self.user_name}/dev:Z",
            "--userns=keep-id",
            self.image_name
        ]
        
        if message:
            claude_cmd = "claude"
            if permission_mode:
                claude_cmd += f" --permission-mode {permission_mode}"
            else:
                claude_cmd += " --dangerously-skip-permissions"
            claude_cmd += f' -p "{message}" --output-format stream-json --verbose'
            
            self.print_colored(f"Running {claude_cmd} after container starts...", Colors.BLUE)
            run_args.extend(["bash", "-c", claude_cmd])
        
        subprocess.run(run_args)

    def handle_worktree_post_processing(self) -> None:
        """Handle post-container git operations for worktree."""
        if not (self.worktree_created and self.worktree_path and self.worktree_path.exists()):
            return
        
        self.print_colored("Processing worktree changes...", Colors.GREEN)
        
        original_cwd = os.getcwd()
        try:
            os.chdir(self.worktree_path)
            
            # Check if there are changes
            has_changes = False
            
            # Check for unstaged changes
            result = subprocess.run(["git", "diff", "--quiet"], capture_output=True)
            if result.returncode != 0:
                has_changes = True
            
            # Check for staged changes
            result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
            if result.returncode != 0:
                has_changes = True
            
            # Check for untracked files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                has_changes = True
            
            if has_changes:
                self.print_colored("Changes detected in worktree, committing and pushing...", Colors.BLUE)
                
                # Add all changes
                subprocess.run(["git", "add", "-A"], check=True)
                
                # Commit with timestamp
                commit_msg = f"chore: claude code container changes {time.strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                
                # Get current branch
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                current_branch = result.stdout.strip()
                
                # Try to push
                try:
                    subprocess.run(["git", "push", "origin", current_branch], check=True)
                    self.print_colored(f"Changes pushed to origin/{current_branch}", Colors.GREEN)
                except subprocess.CalledProcessError:
                    try:
                        subprocess.run(["git", "push", "--set-upstream", "origin", current_branch], check=True)
                        self.print_colored(f"New branch created and pushed to origin/{current_branch}", Colors.GREEN)
                    except subprocess.CalledProcessError:
                        self.print_colored("Warning: Failed to push changes to remote", Colors.YELLOW)
            else:
                self.print_colored("No changes detected in worktree", Colors.BLUE)
                
        finally:
            os.chdir(original_cwd)

    def _cleanup_temp_dir(self) -> None:
        """Clean up temporary directory."""
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run(self) -> None:
        """Main execution method."""
        args = self.parse_args()
        
        self.print_colored("Claude Code Container Launcher", Colors.BLUE)
        
        # Check if Dockerfile exists
        if not self.dockerfile.exists():
            self.print_colored(f"Warning: {self.dockerfile} not found in script directory", Colors.YELLOW)
            sys.exit(1)
        
        # Set up cleanup behavior
        if args.keep_worktree:
            self.cleanup_worktree = False
        
        # Setup working directory
        mount_path = self.cwd
        if not args.no_worktree:
            if args.worktree_path and args.worktree_path.exists():
                self.print_colored(f"Using existing worktree at: {args.worktree_path}", Colors.BLUE)
                self.worktree_path = args.worktree_path
                mount_path = args.worktree_path
                self.cleanup_worktree = False
            else:
                self.worktree_path = self.create_worktree(args.worktree_branch or "HEAD")
                mount_path = self.worktree_path
        else:
            self.print_colored("Using current directory (no worktree)", Colors.BLUE)
        
        try:
            # Prepare configuration
            self.prepare_claude_config()
            
            # Build image if needed
            if self.should_build_image(args.no_cache):
                self.build_image(args.no_cache)
            
            # Clean up temp files
            self.cleanup_temp_files()
            
            # Stop existing container
            self.stop_existing_container()
            
            # Run container
            self.run_container(mount_path, args.message, args.permission_mode)
            
            self.print_colored("Container stopped", Colors.GREEN)
            
            # Handle post-container operations
            self.handle_worktree_post_processing()
            
        finally:
            # Cleanup
            self.cleanup_worktree_if_needed()


if __name__ == "__main__":
    launcher = ClaudeContainerLauncher()
    launcher.run()