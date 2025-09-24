#!/bin/bash
# Basic Asset Pipeline Workflow
# Simple daily workflow for asset processing

set -e  # Exit on any error

echo "=== Old Times Asset Pipeline - Basic Workflow ==="
echo

# Step 1: Ensure dependencies are installed
echo "1. Checking dependencies..."
if ! python -c "import scripts.asset_pipeline.cli" 2>/dev/null; then
    echo "Installing dependencies..."
    just dev-setup
fi
echo "✓ Dependencies ready"
echo

# Step 2: Create asset symlink (if needed)
echo "2. Setting up asset symlink..."
if ! python -m scripts.asset_pipeline.cli link --validate 2>/dev/null; then
    echo "Creating asset symlink..."
    just link
else
    echo "✓ Asset symlink already valid"
fi
echo

# Step 3: Run complete pipeline
echo "3. Running asset pipeline..."
just all
echo

# Step 4: Verify results
echo "4. Verifying results..."
if [ -d "assets/sprites" ] && [ -f "assets/data/sprites.toml" ]; then
    sprite_count=$(find assets/sprites -name "*.png" 2>/dev/null | wc -l)
    echo "✓ Generated $sprite_count sprite files"
    
    if [ -d "assets/atlases" ]; then
        atlas_count=$(find assets/atlases -name "*.png" 2>/dev/null | wc -l)
        echo "✓ Generated $atlas_count texture atlases"
    fi
    
    echo "✓ Generated sprites.toml metadata"
else
    echo "✗ Pipeline may have failed - missing expected files"
    exit 1
fi
echo

echo "=== Basic Workflow Complete ==="
echo "Generated assets are ready for use in the game."
echo
echo "Next steps:"
echo "  - Run 'cargo run -p oldtimes-client' to test the game"
echo "  - Check 'assets/preview/' for visual verification"
echo "  - Use 'just validate' to run additional quality checks"