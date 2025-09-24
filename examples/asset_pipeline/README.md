# Asset Pipeline Configuration Examples

This directory contains example configuration files for different use cases of the Old Times asset pipeline.

## Configuration Files

### Basic Configurations
- `basic.toml` - Minimal configuration for getting started
- `development.toml` - Development-friendly configuration with previews and validation
- `production.toml` - Production configuration optimized for performance

### Asset Source Configurations
- `kenney-only.toml` - Using only Kenney CC0 asset packs
- `ai-generation.toml` - AI-powered asset generation setup
- `mixed-sources.toml` - Combination of multiple asset sources

### Specialized Configurations
- `mod-development.toml` - Configuration optimized for mod development
- `high-quality.toml` - Strict quality standards for professional assets
- `performance.toml` - Optimized for fast processing of large asset sets

### Platform-Specific
- `windows.toml` - Windows-specific paths and settings
- `linux.toml` - Linux-specific configuration
- `ci-cd.toml` - Configuration for continuous integration pipelines

## Usage

Copy any example configuration and customize it for your needs:

```bash
# Copy an example configuration
cp examples/asset_pipeline/development.toml asset_pipeline.toml

# Edit the configuration
nano asset_pipeline.toml

# Use the configuration
just all
```

Or use a configuration directly:

```bash
CONFIG=examples/asset_pipeline/kenney-only.toml just all
```

## Environment Variables

All configurations support environment variable overrides. See the main documentation for details.