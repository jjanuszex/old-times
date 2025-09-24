# CLI Usage Examples

This directory contains example scripts and usage patterns for the Old Times asset pipeline CLI.

## Basic Usage Examples

### Quick Start
```bash
# Set up the pipeline
just dev-setup

# Create asset symlink (required first step)
just link

# Run complete pipeline
just all
```

### Individual Commands
```bash
# Process Kenney asset packs
just kenney

# Generate AI assets (if configured)
just cloud

# Create texture atlases
just atlas

# Validate asset quality
just validate

# Generate mod assets
just mod my_mod_name
```

## Advanced Usage

### Custom Configuration
```bash
# Use custom configuration file
CONFIG=my_config.toml just all

# Use environment variables
export ASSET_PIPELINE_AI_PROVIDER=stable-diffusion
just cloud

# Combine configuration methods
CONFIG=base.toml ASSET_PIPELINE_TILE_WIDTH=128 just all
```

### Specific Operations
```bash
# Validate existing symlink
python -m scripts.asset_pipeline.cli link --validate

# Generate previews only
python -m scripts.asset_pipeline.cli preview

# Run specific pipeline steps
python -m scripts.asset_pipeline.cli all --steps="kenney,atlas"

# Skip certain steps
python -m scripts.asset_pipeline.cli all --skip-validation --skip-preview
```

### Mod Development
```bash
# Create new mod
just mod my_new_mod

# Validate existing mod
python -m scripts.asset_pipeline.cli mod my_mod --validate

# Force overwrite mod directory
python -m scripts.asset_pipeline.cli mod my_mod --force
```

### Configuration Management
```bash
# Show current configuration
python -m scripts.asset_pipeline.cli config --show

# Validate configuration
python -m scripts.asset_pipeline.cli config --validate

# Show environment variables
python -m scripts.asset_pipeline.cli config --env-vars
```

### Testing and Debugging
```bash
# Check pipeline status
just status

# Test configuration
just test-config

# Test symlink functionality
just test-symlink

# Run with verbose output
python -m scripts.asset_pipeline.cli all --verbose

# Dry run (show what would be done)
python -m scripts.asset_pipeline.cli link --dry-run
```

## Workflow Examples

See the individual workflow files for complete examples:
- `basic_workflow.sh` - Simple daily workflow
- `development_workflow.sh` - Development and testing workflow
- `production_workflow.sh` - Production build workflow
- `mod_development_workflow.sh` - Mod creation workflow
- `ci_workflow.sh` - Continuous integration workflow