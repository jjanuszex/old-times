#!/bin/bash
# Development Asset Pipeline Workflow
# Comprehensive workflow for development and testing

set -e

echo "=== Old Times Asset Pipeline - Development Workflow ==="
echo

# Configuration
CONFIG_FILE="examples/asset_pipeline/development.toml"
PREVIEW_DIR="assets/preview"

# Step 1: Setup and validation
echo "1. Development setup and validation..."
just dev-setup

# Validate configuration
echo "Validating configuration..."
CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli config --validate
echo "✓ Configuration valid"

# Test symlink functionality
echo "Testing symlink functionality..."
just test-symlink
echo "✓ Symlink functionality working"
echo

# Step 2: Clean previous build (optional)
echo "2. Cleaning previous build..."
read -p "Clean previous assets? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    just clean
    echo "✓ Previous assets cleaned"
else
    echo "Keeping previous assets"
fi
echo

# Step 3: Run pipeline with development configuration
echo "3. Running development pipeline..."
CONFIG=$CONFIG_FILE just all
echo

# Step 4: Generate comprehensive previews
echo "4. Generating development previews..."
CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli preview \
    --output "$PREVIEW_DIR" \
    --cleanup
echo "✓ Previews generated in $PREVIEW_DIR"
echo

# Step 5: Run comprehensive validation
echo "5. Running comprehensive validation..."
CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli validate --strict
echo "✓ Validation complete"
echo

# Step 6: Display development statistics
echo "6. Development statistics..."
if [ -d "assets/sprites" ]; then
    sprite_count=$(find assets/sprites -name "*.png" 2>/dev/null | wc -l)
    echo "  Sprites: $sprite_count files"
fi

if [ -d "assets/atlases" ]; then
    atlas_count=$(find assets/atlases -name "*.png" 2>/dev/null | wc -l)
    echo "  Atlases: $atlas_count files"
fi

if [ -d "$PREVIEW_DIR" ]; then
    preview_count=$(find "$PREVIEW_DIR" -name "*.png" 2>/dev/null | wc -l)
    echo "  Previews: $preview_count files"
fi

if [ -f "assets/data/sprites.toml" ]; then
    metadata_lines=$(wc -l < "assets/data/sprites.toml")
    echo "  Metadata: $metadata_lines lines in sprites.toml"
fi
echo

# Step 7: Test game integration (optional)
echo "7. Testing game integration..."
read -p "Test with game client? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Building and testing game client..."
    if cargo build -p oldtimes-client --quiet; then
        echo "✓ Game client builds successfully with new assets"
        echo "Run 'cargo run -p oldtimes-client' to test interactively"
    else
        echo "✗ Game client build failed - check asset compatibility"
        exit 1
    fi
else
    echo "Skipping game integration test"
fi
echo

echo "=== Development Workflow Complete ==="
echo
echo "Development assets ready:"
echo "  - Assets: assets/sprites/"
echo "  - Atlases: assets/atlases/"
echo "  - Metadata: assets/data/sprites.toml"
echo "  - Previews: $PREVIEW_DIR/"
echo
echo "Development commands:"
echo "  just status          # Check pipeline status"
echo "  just validate        # Run validation"
echo "  CONFIG=$CONFIG_FILE just all  # Rerun with dev config"
echo "  just clean           # Clean generated assets"