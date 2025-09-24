# Asset Pipeline Justfile for Old Times 2D Isometric RTS Game
# Alternative to Makefile using the 'just' command runner

# Configuration
config_file := env_var_or_default("CONFIG", "scripts/asset_pipeline.toml")
python_cmd := "python -m scripts.asset_pipeline.cli"

# Default recipe
default:
    @just --list

# Show help information
help:
    @echo "Asset Pipeline Commands:"
    @echo "  just link       Create symlink between asset directories"
    @echo "  just kenney     Download and process Kenney asset packs"
    @echo "  just cloud      Generate assets using AI providers"
    @echo "  just atlas      Create texture atlases for animated units"
    @echo "  just mod NAME   Generate assets into mod directory"
    @echo "  just all        Run complete asset pipeline"
    @echo "  just validate   Validate asset quality and compliance"
    @echo "  just clean      Clean generated assets and caches"
    @echo ""
    @echo "Configuration:"
    @echo "  Set CONFIG environment variable to specify custom configuration file"
    @echo ""
    @echo "Examples:"
    @echo "  just link"
    @echo "  CONFIG=custom.toml just all"
    @echo "  just mod my_mod"

# Check if Python dependencies are installed
check-deps:
    #!/usr/bin/env bash
    if ! python -c "import scripts.asset_pipeline.cli" 2>/dev/null; then
        echo "Error: Asset pipeline dependencies not installed"
        echo "Run: just dev-setup"
        exit 1
    fi

# Create asset directory symlink
link: check-deps
    @echo "Creating asset directory symlink..."
    {{python_cmd}} link
    @echo "✓ Asset symlink creation completed successfully"

# Process Kenney asset packs
kenney: check-deps link
    @echo "Processing Kenney asset packs..."
    {{python_cmd}} kenney
    @echo "✓ Kenney asset processing completed successfully"

# Generate assets using AI providers
cloud: check-deps link
    @echo "Generating assets with AI providers..."
    {{python_cmd}} cloud
    @echo "✓ AI asset generation completed successfully"

# Create texture atlases
atlas: check-deps kenney cloud
    @echo "Creating texture atlases..."
    {{python_cmd}} atlas
    @echo "✓ Atlas generation completed successfully"

# Generate mod assets
mod NAME: check-deps
    @echo "Generating mod assets for '{{NAME}}'..."
    {{python_cmd}} mod {{NAME}}
    @echo "✓ Mod asset generation for {{NAME}} completed successfully"

# Validate assets
validate: check-deps
    @echo "Validating assets..."
    {{python_cmd}} validate
    @echo "✓ Asset validation completed successfully"

# Run complete asset pipeline
all: check-deps
    @echo "Running complete asset pipeline..."
    {{python_cmd}} all
    @echo ""
    @echo "Generated files can be found in:"
    @echo "  - assets/sprites/ (normalized assets)"
    @echo "  - assets/atlases/ (texture atlases)"
    @echo "  - assets/data/sprites.toml (metadata)"
    @echo "  - assets/preview/ (asset previews)"

# Clean generated assets and caches
clean:
    #!/usr/bin/env bash
    echo "Cleaning generated assets and caches..."
    rm -rf assets/atlases/*.png assets/atlases/*.json 2>/dev/null || true
    rm -f assets/data/sprites.toml 2>/dev/null || true
    find mods -name "sprites" -type d -exec rm -rf {} + 2>/dev/null || true
    find mods -name "data" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    rm -rf cache/* 2>/dev/null || true
    echo "✓ Cleanup complete"

# Development setup
dev-setup:
    @echo "Setting up development environment..."
    pip install -r scripts/requirements.txt
    @echo "✓ Development setup complete"

# Test symlink functionality
test-symlink: check-deps
    @echo "Testing symlink functionality..."
    {{python_cmd}} link --validate
    @echo "✓ Symlink validation completed successfully"

# Test configuration
test-config: check-deps
    @echo "Validating configuration..."
    {{python_cmd}} config --validate
    @echo "✓ Configuration validation completed successfully"

# Show pipeline status
status: check-deps
    #!/usr/bin/env bash
    echo "Asset Pipeline Status:"
    echo "======================"
    echo ""
    echo "Symlink Status:"
    {{python_cmd}} link --validate 2>/dev/null && echo "  ✓ Asset symlink is valid" || echo "  ✗ Asset symlink is invalid or missing"
    echo ""
    echo "Configuration:"
    {{python_cmd}} config --show 2>/dev/null || echo "  ✗ Configuration invalid or missing"
    echo ""
    echo "Generated Assets:"
    if [ -d "assets/sprites" ]; then echo "  ✓ Sprites directory exists ($(find assets/sprites -name "*.png" 2>/dev/null | wc -l) files)"; else echo "  ✗ Sprites directory missing"; fi
    if [ -d "assets/atlases" ]; then echo "  ✓ Atlases directory exists ($(find assets/atlases -name "*.png" 2>/dev/null | wc -l) files)"; else echo "  ✗ Atlases directory missing"; fi
    if [ -f "assets/data/sprites.toml" ]; then echo "  ✓ Sprites metadata exists"; else echo "  ✗ Sprites metadata missing"; fi

# Show detailed help
help-detailed:
    @echo "Asset Pipeline Detailed Help"
    @echo "============================"
    @echo ""
    @echo "MAIN RECIPES:"
    @echo "  just link       - Create symlink from crates/oldtimes-client/assets to ../../assets"
    @echo "  just kenney     - Download and process Kenney CC0 asset packs"
    @echo "  just cloud      - Generate assets using configured AI providers"
    @echo "  just atlas      - Create texture atlases for animated units"
    @echo "  just mod NAME   - Generate assets into mod directory"
    @echo "  just all        - Run complete pipeline (link -> kenney -> cloud -> atlas -> validate)"
    @echo "  just validate   - Validate all assets meet quality standards"
    @echo "  just clean      - Clean all generated assets and caches"
    @echo ""
    @echo "UTILITY RECIPES:"
    @echo "  just dev-setup     - Install Python dependencies"
    @echo "  just test-symlink  - Test symlink functionality"
    @echo "  just test-config   - Validate configuration file"
    @echo "  just status        - Show current pipeline status"
    @echo "  just check-deps    - Check if dependencies are installed"
    @echo ""
    @echo "CONFIGURATION:"
    @echo "  CONFIG=<file>      - Use custom configuration file"
    @echo ""
    @echo "EXAMPLES:"
    @echo "  just link                      # Create asset symlink"
    @echo "  just all                       # Run complete pipeline"
    @echo "  CONFIG=custom.toml just all    # Use custom config"
    @echo "  just mod my_mod                # Generate mod assets"
    @echo "  just status                    # Check pipeline status"
    @echo ""
    @echo "DEPENDENCIES:"
    @echo "  just all has the following dependency chain:"
    @echo "    link (required first)"
    @echo "    ├── kenney (depends on link)"
    @echo "    ├── cloud (depends on link)"
    @echo "    ├── atlas (depends on kenney + cloud)"
    @echo "    └── validate (final step)"