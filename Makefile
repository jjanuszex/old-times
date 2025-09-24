# Asset Pipeline Makefile for Old Times 2D Isometric RTS Game
# Provides targets for all asset processing operations

.PHONY: help assets-link assets-kenney assets-cloud assets-atlas assets-mod assets-all assets-validate assets-clean
.PHONY: test-symlink test-config dev-setup status help-detailed

# Default target
help:
	@echo "Asset Pipeline Commands:"
	@echo "  assets:link     Create symlink between asset directories"
	@echo "  assets:kenney   Download and process Kenney asset packs"
	@echo "  assets:cloud    Generate assets using AI providers"
	@echo "  assets:atlas    Create texture atlases for animated units"
	@echo "  assets:mod      Generate assets into mod directory (use NAME=<mod_name>)"
	@echo "  assets:all      Run complete asset pipeline"
	@echo "  assets:validate Validate asset quality and compliance"
	@echo "  assets:clean    Clean generated assets and caches"
	@echo ""
	@echo "Legacy Commands (deprecated, use colon syntax above):"
	@echo "  assets-link, assets-kenney, assets-cloud, assets-atlas, assets-mod, assets-all"
	@echo ""
	@echo "Configuration:"
	@echo "  Use CONFIG=<file> to specify custom configuration file"
	@echo "  Use NAME=<name> for mod generation target"
	@echo ""
	@echo "Examples:"
	@echo "  make assets:link"
	@echo "  make assets:all CONFIG=custom.toml"
	@echo "  make assets:mod NAME=my_mod"
	@echo ""
	@echo "Dependencies:"
	@echo "  assets:all depends on: assets:link -> assets:kenney -> assets:cloud -> assets:atlas -> assets:validate"

# Configuration file handling
CONFIG_FILE ?= scripts/asset_pipeline.toml
CONFIG_ARG = $(if $(CONFIG),--config $(CONFIG),)

# Python command for running the asset pipeline
PYTHON_CMD = python -m scripts.asset_pipeline.cli

# Error handling function
define check_python_deps
	@if ! python -c "import scripts.asset_pipeline.cli" 2>/dev/null; then \
		echo "Error: Asset pipeline dependencies not installed"; \
		echo "Run: make dev-setup"; \
		exit 1; \
	fi
endef

# Status reporting function
define report_success
	@echo "✓ $(1) completed successfully"
endef

define report_error
	@echo "✗ $(1) failed"
	@exit 1
endef

# Primary asset pipeline targets (dash syntax)
assets-link: check-deps
	@echo "Creating asset directory symlink..."
	@if $(PYTHON_CMD) link $(CONFIG_ARG); then \
		$(call report_success,Asset symlink creation); \
	else \
		$(call report_error,Asset symlink creation); \
	fi

assets-kenney: check-deps assets-link
	@echo "Processing Kenney asset packs..."
	@if $(PYTHON_CMD) kenney $(CONFIG_ARG); then \
		$(call report_success,Kenney asset processing); \
	else \
		$(call report_error,Kenney asset processing); \
	fi

assets-cloud: check-deps assets-link
	@echo "Generating assets with AI providers..."
	@if $(PYTHON_CMD) cloud $(CONFIG_ARG); then \
		$(call report_success,AI asset generation); \
	else \
		$(call report_error,AI asset generation); \
	fi

assets-atlas: check-deps assets-kenney assets-cloud
	@echo "Creating texture atlases..."
	@if $(PYTHON_CMD) atlas $(CONFIG_ARG); then \
		$(call report_success,Atlas generation); \
	else \
		$(call report_error,Atlas generation); \
	fi

assets-mod: check-deps
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME parameter required for mod generation"; \
		echo "Usage: make assets-mod NAME=<mod_name>"; \
		exit 1; \
	fi
	@echo "Generating mod assets for '$(NAME)'..."
	@if $(PYTHON_CMD) mod $(NAME) $(CONFIG_ARG); then \
		$(call report_success,Mod asset generation for $(NAME)); \
	else \
		$(call report_error,Mod asset generation for $(NAME)); \
	fi

assets-validate: check-deps
	@echo "Validating assets..."
	@if $(PYTHON_CMD) validate $(CONFIG_ARG); then \
		$(call report_success,Asset validation); \
	else \
		$(call report_error,Asset validation); \
	fi

assets-all: check-deps
	@echo "Running complete asset pipeline..."
	@$(PYTHON_CMD) all $(CONFIG_ARG) --summary
	@echo ""
	@echo "Generated files can be found in:"
	@echo "  - assets/sprites/ (normalized assets)"
	@echo "  - assets/atlases/ (texture atlases)"
	@echo "  - assets/data/sprites.toml (metadata)"
	@echo "  - assets/preview/ (asset previews)"

# Colon syntax aliases (requires escaping in some Make versions)
assets\:link: assets-link
assets\:kenney: assets-kenney  
assets\:cloud: assets-cloud
assets\:atlas: assets-atlas
assets\:mod: assets-mod
assets\:validate: assets-validate
assets\:all: assets-all

# Utility targets
assets-clean:
	@echo "Cleaning generated assets and caches..."
	@if [ -d "assets/atlases" ]; then rm -rf assets/atlases/*.png assets/atlases/*.json; fi
	@if [ -f "assets/data/sprites.toml" ]; then rm -f assets/data/sprites.toml; fi
	@if [ -d "mods" ]; then find mods -name "sprites" -type d -exec rm -rf {} + 2>/dev/null || true; fi
	@if [ -d "mods" ]; then find mods -name "data" -type d -exec rm -rf {} + 2>/dev/null || true; fi
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@if [ -d "cache" ]; then rm -rf cache/*; fi
	@echo "✓ Cleanup complete"

assets\:clean: assets-clean

# Dependency checking
check-deps:
	$(call check_python_deps)

# Validation and testing targets
test-symlink: check-deps
	@echo "Testing symlink functionality..."
	@if $(PYTHON_CMD) link --validate; then \
		$(call report_success,Symlink validation); \
	else \
		$(call report_error,Symlink validation); \
	fi

test-config: check-deps
	@echo "Validating configuration..."
	@if $(PYTHON_CMD) config --validate $(CONFIG_ARG); then \
		$(call report_success,Configuration validation); \
	else \
		$(call report_error,Configuration validation); \
	fi

# Development targets
dev-setup:
	@echo "Setting up development environment..."
	@if [ ! -f "scripts/requirements.txt" ]; then \
		echo "Error: scripts/requirements.txt not found"; \
		exit 1; \
	fi
	@if pip install -r scripts/requirements.txt; then \
		$(call report_success,Development environment setup); \
	else \
		$(call report_error,Development environment setup); \
	fi

# Status and information targets
status:
	@echo "Asset Pipeline Status:"
	@echo "======================"
	@echo ""
	@echo "Symlink Status:"
	@if $(PYTHON_CMD) link --validate 2>/dev/null; then \
		echo "  ✓ Asset symlink is valid"; \
	else \
		echo "  ✗ Asset symlink is invalid or missing"; \
	fi
	@echo ""
	@echo "Configuration:"
	@$(PYTHON_CMD) config --show $(CONFIG_ARG) 2>/dev/null || echo "  ✗ Configuration invalid or missing"
	@echo ""
	@echo "Generated Assets:"
	@if [ -d "assets/sprites" ]; then \
		echo "  ✓ Sprites directory exists ($(shell find assets/sprites -name "*.png" 2>/dev/null | wc -l) files)"; \
	else \
		echo "  ✗ Sprites directory missing"; \
	fi
	@if [ -d "assets/atlases" ]; then \
		echo "  ✓ Atlases directory exists ($(shell find assets/atlases -name "*.png" 2>/dev/null | wc -l) files)"; \
	else \
		echo "  ✗ Atlases directory missing"; \
	fi
	@if [ -f "assets/data/sprites.toml" ]; then \
		echo "  ✓ Sprites metadata exists"; \
	else \
		echo "  ✗ Sprites metadata missing"; \
	fi

# Help with detailed information
help-detailed:
	@echo "Asset Pipeline Detailed Help"
	@echo "============================"
	@echo ""
	@echo "MAIN TARGETS:"
	@echo "  assets:link     - Create symlink from crates/oldtimes-client/assets to ../../assets"
	@echo "  assets:kenney   - Download and process Kenney CC0 asset packs"
	@echo "  assets:cloud    - Generate assets using configured AI providers"
	@echo "  assets:atlas    - Create texture atlases for animated units"
	@echo "  assets:mod      - Generate assets into mod directory (requires NAME=<mod_name>)"
	@echo "  assets:all      - Run complete pipeline (link -> kenney -> cloud -> atlas -> validate)"
	@echo "  assets:validate - Validate all assets meet quality standards"
	@echo "  assets:clean    - Clean all generated assets and caches"
	@echo ""
	@echo "UTILITY TARGETS:"
	@echo "  dev-setup       - Install Python dependencies"
	@echo "  test-symlink    - Test symlink functionality"
	@echo "  test-config     - Validate configuration file"
	@echo "  status          - Show current pipeline status"
	@echo "  check-deps      - Check if dependencies are installed"
	@echo ""
	@echo "CONFIGURATION:"
	@echo "  CONFIG=<file>   - Use custom configuration file"
	@echo "  NAME=<name>     - Specify mod name for assets:mod target"
	@echo ""
	@echo "EXAMPLES:"
	@echo "  make assets:link                    # Create asset symlink"
	@echo "  make assets:all                     # Run complete pipeline"
	@echo "  make assets:all CONFIG=custom.toml  # Use custom config"
	@echo "  make assets:mod NAME=my_mod         # Generate mod assets"
	@echo "  make status                         # Check pipeline status"
	@echo ""
	@echo "DEPENDENCIES:"
	@echo "  assets:all has the following dependency chain:"
	@echo "    assets:link (required first)"
	@echo "    ├── assets:kenney (depends on link)"
	@echo "    ├── assets:cloud (depends on link)"
	@echo "    ├── assets:atlas (depends on kenney + cloud)"
	@echo "    └── assets:validate (final step)"