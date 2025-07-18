# Makefile for creating a standalone Claude container launcher script
# Embeds claude.template.json and claude-code-ubuntu.dockerfile into launch-claude-container.py

SCRIPT_DIR = podman
SOURCE_SCRIPT = $(SCRIPT_DIR)/launch-claude-container.py
TEMPLATE_FILE = $(SCRIPT_DIR)/claude.template.json
DOCKERFILE = $(SCRIPT_DIR)/claude-code-ubuntu.dockerfile
OUTPUT_SCRIPT = launch-claude-container-standalone.py

.PHONY: build clean help

build: $(OUTPUT_SCRIPT)

$(OUTPUT_SCRIPT): $(SOURCE_SCRIPT) $(TEMPLATE_FILE) $(DOCKERFILE) build_standalone.py
	@echo "Building standalone Claude container launcher..."
	@python3 build_standalone.py

clean:
	@rm -f $(OUTPUT_SCRIPT)
	@echo "Cleaned up generated files"

help:
	@echo "Available targets:"
	@echo "  build  - Create standalone launcher script (default)"
	@echo "  clean  - Remove generated files"
	@echo "  help   - Show this help message"
	@echo ""
	@echo "Output: $(OUTPUT_SCRIPT)"