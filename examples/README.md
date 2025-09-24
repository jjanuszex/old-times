# Examples

This directory contains examples and templates for various aspects of Old Times development.

## Directory Structure

### Asset Pipeline Examples
- **[asset_pipeline/](asset_pipeline/)** - Configuration examples for the asset pipeline
  - `basic.toml` - Basic asset pipeline configuration
  - `kenney-only.toml` - Using only Kenney asset packs
  - `ai-generation.toml` - AI-powered asset generation
  - `mod-development.toml` - Configuration for mod development
  - `ci-cd.toml` - CI/CD pipeline configuration

### Asset Specifications
- **[asset_specifications/](asset_specifications/)** - Templates and specifications for creating assets
  - `asset_spec.toml` - Template for asset specifications
  - `animation_spec.toml` - Animation definitions and templates
  - `README.md` - Detailed asset creation guidelines

### CLI Usage Examples
- **[cli_usage/](cli_usage/)** - Shell scripts demonstrating CLI usage
  - `basic_workflow.sh` - Basic development workflow
  - `development_workflow.sh` - Complete development setup
  - `mod_development_workflow.sh` - Mod development workflow

### Mod Examples
- **[mods/](mods/)** - Example mod structures and configurations
  - `basic_mod/` - Simple mod example
  - `advanced_mod/` - Complex mod with custom assets

## Getting Started

### Asset Pipeline

To get started with the asset pipeline, copy one of the configuration examples:

```bash
# Copy basic configuration
cp examples/asset_pipeline/basic.toml scripts/asset_pipeline.toml

# Run the pipeline
just all
```

### Creating Assets

Follow the specifications in `asset_specifications/`:

1. Read the [asset specifications README](asset_specifications/README.md)
2. Use the templates in `asset_spec.toml` and `animation_spec.toml`
3. Follow the quality guidelines
4. Test with the asset pipeline

### CLI Workflows

Run the example scripts to see common workflows:

```bash
# Basic workflow
bash examples/cli_usage/basic_workflow.sh

# Development setup
bash examples/cli_usage/development_workflow.sh

# Mod development
bash examples/cli_usage/mod_development_workflow.sh
```

### Mod Development

Start with the basic mod example:

```bash
# Copy basic mod structure
cp -r examples/mods/basic_mod mods/my-new-mod

# Edit mod configuration
nano mods/my-new-mod/mod.toml

# Generate mod assets
just mod my-new-mod
```

## Configuration Examples

### Asset Pipeline Configurations

Each configuration file in `asset_pipeline/` demonstrates different use cases:

- **Basic**: Minimal setup for getting started
- **Kenney Only**: Using only CC0 Kenney asset packs
- **AI Generation**: Leveraging AI for asset creation
- **Mod Development**: Optimized for mod creation
- **CI/CD**: Automated pipeline for continuous integration

### Asset Specifications

The `asset_specifications/` directory contains:

- Detailed pixel art guidelines
- Isometric projection requirements
- Animation frame specifications
- Quality standards and validation rules

## Best Practices

### Asset Creation

1. **Follow Standards**: Use the specifications in `asset_specifications/`
2. **Test Early**: Validate assets with `just validate`
3. **Iterate**: Use hot-reload for rapid development
4. **Document**: Update metadata and documentation

### Mod Development

1. **Start Simple**: Begin with the basic mod example
2. **Use Pipeline**: Leverage the asset pipeline for consistency
3. **Test Thoroughly**: Validate mod assets and data
4. **Share**: Consider contributing useful mods back to the community

### Development Workflow

1. **Setup**: Use the development workflow script
2. **Iterate**: Use hot-reload and fast feedback loops
3. **Validate**: Run tests and validation regularly
4. **Document**: Keep examples and documentation updated

## Contributing Examples

When contributing new examples:

1. **Clear Purpose**: Each example should have a clear use case
2. **Documentation**: Include README files explaining the example
3. **Working Code**: Ensure examples actually work
4. **Best Practices**: Demonstrate good practices and patterns

## Support

If you have questions about the examples:

1. Check the main [README.md](../README.md)
2. Read the [GRAPHICS_GUIDE.md](../GRAPHICS_GUIDE.md)
3. Look at the [CONTRIBUTING.md](../CONTRIBUTING.md)
4. Open an issue on GitHub