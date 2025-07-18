#!/usr/bin/env python3
"""
Script to build a standalone version of the Claude container launcher.
Embeds the dockerfile and template content into the Python script.
"""

import sys
from pathlib import Path


def main():
    # File paths
    source_script = Path("podman/launch-claude-container.py")
    dockerfile = Path("podman/claude-code-ubuntu.dockerfile")
    template_file = Path("podman/claude.template.json")
    output_script = Path("launch-claude-container-standalone.py")
    
    # Read the source script
    with source_script.open('r') as f:
        source = f.read()
    
    # Read embedded files
    with dockerfile.open('r') as f:
        dockerfile_content = f.read()
    
    with template_file.open('r') as f:
        template_content = f.read()
    
    # Find the class definition and inject embedded content
    lines = source.split('\n')
    output_lines = []
    in_init = False
    
    for i, line in enumerate(lines):
        if line.strip() == 'class ClaudeContainerLauncher:':
            output_lines.append(line)
            output_lines.append('    # Embedded content - dockerfile')
            output_lines.append(f'    DOCKERFILE_CONTENT = """{dockerfile_content}"""')
            output_lines.append('')
            output_lines.append('    # Embedded content - template')
            output_lines.append(f'    TEMPLATE_CONTENT = """{template_content}"""')
            output_lines.append('')
        elif line.strip() == 'def __init__(self):':
            in_init = True
            output_lines.append(line)
        elif in_init and line.strip().startswith('self.script_dir'):
            output_lines.append(line)
            output_lines.append('        # Create temporary directory for embedded files')
            output_lines.append('        self.temp_dir = Path(tempfile.mkdtemp())')
            output_lines.append('        self.dockerfile = self.temp_dir / "claude-code-ubuntu.dockerfile"')
            output_lines.append('        self.template_file = self.temp_dir / "claude.template.json"')
            output_lines.append('')
            output_lines.append('        # Extract embedded files')
            output_lines.append('        self.dockerfile.write_text(self.DOCKERFILE_CONTENT)')
            output_lines.append('        self.template_file.write_text(self.TEMPLATE_CONTENT)')
            output_lines.append('')
            output_lines.append('        # Set up cleanup')
            output_lines.append('        import atexit')
            output_lines.append('        atexit.register(self._cleanup_temp_dir)')
            in_init = False
        elif 'self.dockerfile = self.script_dir' in line:
            continue
        elif 'self.template_file = self.script_dir' in line:
            continue
        elif line.strip() == 'def run(self) -> None:':
            output_lines.append('    def _cleanup_temp_dir(self) -> None:')
            output_lines.append('        """Clean up temporary directory."""')
            output_lines.append('        if hasattr(self, "temp_dir") and self.temp_dir.exists():')
            output_lines.append('            import shutil')
            output_lines.append('            shutil.rmtree(self.temp_dir, ignore_errors=True)')
            output_lines.append('')
            output_lines.append(line)
        else:
            output_lines.append(line)
    
    # Write output
    with output_script.open('w') as f:
        f.write('\n'.join(output_lines))
    
    # Make executable
    output_script.chmod(0o755)
    
    print(f"Created standalone script: {output_script}")


if __name__ == "__main__":
    main()