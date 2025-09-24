#!/bin/bash
# Data validation script for Old Times

set -e

echo "Old Times Data Validation"
echo "========================="

# Build the project
echo "Building project..."
cargo build --quiet

# Validate base game data
echo ""
echo "Validating base game data..."
cargo run -p oldtimes-headless -- validate-data --data-dir assets/data

# Check for mods and validate them
if [ -d "mods" ]; then
    echo ""
    echo "Validating mods..."
    
    for mod_dir in mods/*/; do
        if [ -d "$mod_dir" ]; then
            mod_name=$(basename "$mod_dir")
            echo "  Checking mod: $mod_name"
            
            # Check if mod has required files
            if [ ! -f "$mod_dir/mod.toml" ]; then
                echo "    ❌ Missing mod.toml"
                continue
            fi
            
            # Validate mod data if it exists
            if [ -f "$mod_dir/buildings.toml" ] || [ -f "$mod_dir/recipes.toml" ] || [ -f "$mod_dir/workers.toml" ]; then
                cargo run -p oldtimes-headless -- validate-data --data-dir "$mod_dir" || echo "    ⚠️  Mod validation failed"
            else
                echo "    ✅ Mod structure OK (no data files)"
            fi
        fi
    done
else
    echo "No mods directory found, skipping mod validation"
fi

# Test data loading
echo ""
echo "Testing data loading..."
cargo test --lib test_create_and_load_default_data --quiet

# Check TOML syntax
echo ""
echo "Checking TOML syntax..."

check_toml_file() {
    local file="$1"
    if [ -f "$file" ]; then
        if python3 -c "import toml; toml.load('$file')" 2>/dev/null; then
            echo "  ✅ $file"
        else
            echo "  ❌ $file - Invalid TOML syntax"
            return 1
        fi
    fi
}

# Check base data files
for file in assets/data/*.toml; do
    if [ -f "$file" ]; then
        check_toml_file "$file"
    fi
done

# Check mod files
if [ -d "mods" ]; then
    for mod_dir in mods/*/; do
        if [ -d "$mod_dir" ]; then
            for file in "$mod_dir"*.toml; do
                if [ -f "$file" ]; then
                    check_toml_file "$file"
                fi
            done
        fi
    done
fi

echo ""
echo "Data validation completed!"