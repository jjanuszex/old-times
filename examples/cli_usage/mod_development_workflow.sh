#!/bin/bash
# Mod Development Workflow
# Complete workflow for creating and testing mods

set -e

echo "=== Old Times Asset Pipeline - Mod Development Workflow ==="
echo

# Get mod name from user
if [ -z "$1" ]; then
    read -p "Enter mod name: " MOD_NAME
else
    MOD_NAME="$1"
fi

if [ -z "$MOD_NAME" ]; then
    echo "Error: Mod name is required"
    exit 1
fi

echo "Developing mod: $MOD_NAME"
echo

# Configuration
CONFIG_FILE="examples/asset_pipeline/mod-development.toml"
MOD_DIR="mods/$MOD_NAME"

# Step 1: Setup
echo "1. Setting up mod development environment..."
just dev-setup

# Validate base configuration
CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli config --validate
echo "✓ Configuration validated"
echo

# Step 2: Create or validate mod structure
echo "2. Setting up mod structure..."
if [ -d "$MOD_DIR" ]; then
    echo "Mod directory exists: $MOD_DIR"
    read -p "Overwrite existing mod? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli mod "$MOD_NAME" --force
        echo "✓ Mod structure recreated"
    else
        echo "Using existing mod structure"
    fi
else
    CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli mod "$MOD_NAME"
    echo "✓ Mod structure created"
fi
echo

# Step 3: Guide user through asset setup
echo "3. Setting up mod assets..."
echo "Mod directory structure:"
echo "  $MOD_DIR/"
echo "  ├── mod.toml              # Mod configuration"
echo "  ├── source_assets/        # Place your source assets here"
echo "  │   ├── buildings/"
echo "  │   ├── terrain/"
echo "  │   └── units/"
echo "  ├── sprites/              # Generated sprites (auto-created)"
echo "  ├── atlases/              # Generated atlases (auto-created)"
echo "  └── data/                 # Generated metadata (auto-created)"
echo

read -p "Have you added your source assets to $MOD_DIR/source_assets/? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please add your source assets to the appropriate directories:"
    echo "  - Buildings: $MOD_DIR/source_assets/buildings/"
    echo "  - Terrain: $MOD_DIR/source_assets/terrain/"
    echo "  - Units: $MOD_DIR/source_assets/units/"
    echo
    echo "Then run this script again or use: just mod $MOD_NAME"
    exit 0
fi
echo

# Step 4: Process mod assets
echo "4. Processing mod assets..."
CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli mod "$MOD_NAME"
echo "✓ Mod assets processed"
echo

# Step 5: Validate mod
echo "5. Validating mod..."
CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli mod "$MOD_NAME" --validate
echo "✓ Mod validation complete"
echo

# Step 6: Generate mod previews
echo "6. Generating mod previews..."
if [ -d "$MOD_DIR/sprites" ]; then
    CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli preview \
        --assets "$MOD_DIR/sprites" \
        --output "$MOD_DIR/preview"
    echo "✓ Mod previews generated in $MOD_DIR/preview/"
else
    echo "No sprites found - skipping preview generation"
fi
echo

# Step 7: Display mod statistics
echo "7. Mod statistics..."
echo "Mod: $MOD_NAME"

if [ -f "$MOD_DIR/mod.toml" ]; then
    if command -v python3 >/dev/null 2>&1; then
        # Extract basic info from mod.toml using Python
        python3 -c "
import sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print('  (Cannot parse mod.toml - missing TOML library)')
        sys.exit(0)

try:
    with open('$MOD_DIR/mod.toml', 'rb') as f:
        data = tomllib.load(f)
    
    mod_info = data.get('mod', {})
    print(f'  Name: {mod_info.get(\"name\", \"Unknown\")}')
    print(f'  Version: {mod_info.get(\"version\", \"Unknown\")}')
    print(f'  Author: {mod_info.get(\"author\", \"Unknown\")}')
    
    assets = data.get('assets', {})
    print(f'  Sprites: {assets.get(\"sprites_count\", 0)}')
    print(f'  Atlases: {assets.get(\"atlases_count\", 0)}')
except Exception as e:
    print(f'  (Error reading mod.toml: {e})')
"
    fi
fi

if [ -d "$MOD_DIR/sprites" ]; then
    sprite_count=$(find "$MOD_DIR/sprites" -name "*.png" 2>/dev/null | wc -l)
    echo "  Generated sprites: $sprite_count files"
fi

if [ -d "$MOD_DIR/atlases" ]; then
    atlas_count=$(find "$MOD_DIR/atlases" -name "*.png" 2>/dev/null | wc -l)
    echo "  Generated atlases: $atlas_count files"
fi
echo

# Step 8: Test mod integration (optional)
echo "8. Testing mod integration..."
read -p "Test mod with base game? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Testing mod integration..."
    # This would require game engine support for mod loading
    echo "Note: Mod integration testing requires game engine mod support"
    echo "For now, verify that mod assets follow the same standards as base game assets"
    
    # Run base game validation on mod assets
    if [ -d "$MOD_DIR/sprites" ]; then
        echo "Validating mod assets against base game standards..."
        CONFIG=$CONFIG_FILE python -m scripts.asset_pipeline.cli validate \
            --assets "$MOD_DIR/sprites" \
            --strict
        echo "✓ Mod assets meet base game standards"
    fi
else
    echo "Skipping mod integration test"
fi
echo

echo "=== Mod Development Workflow Complete ==="
echo
echo "Mod '$MOD_NAME' is ready:"
echo "  - Location: $MOD_DIR/"
echo "  - Configuration: $MOD_DIR/mod.toml"
echo "  - Assets: $MOD_DIR/sprites/"
echo "  - Metadata: $MOD_DIR/data/sprites.toml"
echo
echo "Next steps:"
echo "  - Edit $MOD_DIR/mod.toml to customize mod metadata"
echo "  - Add more assets to $MOD_DIR/source_assets/"
echo "  - Rerun: just mod $MOD_NAME"
echo "  - Package for distribution"
echo
echo "Mod development commands:"
echo "  just mod $MOD_NAME                    # Reprocess mod assets"
echo "  python -m scripts.asset_pipeline.cli mod $MOD_NAME --validate  # Validate mod"
echo "  CONFIG=$CONFIG_FILE just mod $MOD_NAME  # Use mod-dev config"