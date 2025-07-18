# Makefile for creating a standalone Claude container launcher script
# Embeds claude.template.json and claude-code-ubuntu.dockerfile into launch-claude-container.sh

SCRIPT_DIR = podman
SOURCE_SCRIPT = $(SCRIPT_DIR)/launch-claude-container.sh
TEMPLATE_FILE = $(SCRIPT_DIR)/claude.template.json
DOCKERFILE = $(SCRIPT_DIR)/claude-code-ubuntu.dockerfile
OUTPUT_SCRIPT = launch-claude-container-standalone.sh

.PHONY: build clean help

build: $(OUTPUT_SCRIPT)

$(OUTPUT_SCRIPT): $(SOURCE_SCRIPT) $(TEMPLATE_FILE) $(DOCKERFILE)
	@echo "Building standalone Claude container launcher..."
	@# Start with the original script header and argument parsing
	@sed -n '1,/^# Get the directory where this script is located/p' $(SOURCE_SCRIPT) > $(OUTPUT_SCRIPT)
	@# Add embedded content extraction functions
	@echo "" >> $(OUTPUT_SCRIPT)
	@echo "# Embedded file extraction functions" >> $(OUTPUT_SCRIPT)
	@echo "extract_dockerfile() {" >> $(OUTPUT_SCRIPT)
	@echo "    cat > \"\$$1\" << 'DOCKERFILE_EOF'" >> $(OUTPUT_SCRIPT)
	@cat $(DOCKERFILE) >> $(OUTPUT_SCRIPT)
	@echo "DOCKERFILE_EOF" >> $(OUTPUT_SCRIPT)
	@echo "}" >> $(OUTPUT_SCRIPT)
	@echo "" >> $(OUTPUT_SCRIPT)
	@echo "extract_template() {" >> $(OUTPUT_SCRIPT)
	@echo "    cat > \"\$$1\" << 'TEMPLATE_EOF'" >> $(OUTPUT_SCRIPT)
	@cat $(TEMPLATE_FILE) >> $(OUTPUT_SCRIPT)
	@echo "TEMPLATE_EOF" >> $(OUTPUT_SCRIPT)
	@echo "}" >> $(OUTPUT_SCRIPT)
	@echo "" >> $(OUTPUT_SCRIPT)
	@# Skip the script directory detection line and continue from configuration
	@sed -n '/^# Configuration$$/,$$p' $(SOURCE_SCRIPT) | \
		sed 's|DOCKERFILE="\$$SCRIPT_DIR/claude-code-ubuntu.dockerfile"|DOCKERFILE="\$$SCRIPT_DIR/claude-code-ubuntu.dockerfile.tmp"|' | \
		sed 's|TEMPLATE_FILE="\$$SCRIPT_DIR/claude.template.json"|TEMPLATE_FILE="\$$SCRIPT_DIR/claude.template.json.tmp"|' | \
		sed '/^# Check if Dockerfile exists/i\\n# Extract embedded files\necho -e "$${GREEN}Extracting embedded files...$${NC}"\nextract_dockerfile "$$DOCKERFILE"\nextract_template "$$TEMPLATE_FILE"' | \
		sed '/^# Clean up temporary files/a\rm -f "$$DOCKERFILE" "$$TEMPLATE_FILE"' >> $(OUTPUT_SCRIPT)
	@chmod +x $(OUTPUT_SCRIPT)
	@echo "Created standalone script: $(OUTPUT_SCRIPT)"

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