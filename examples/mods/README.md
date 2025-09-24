# Mod Examples

This directory contains example mod structures and configurations for the Old Times asset pipeline.

## Example Mods

### Basic Mod (`basic_mod/`)
A minimal mod example showing the basic structure and configuration.

### Advanced Mod (`advanced_mod/`)
A comprehensive mod example with custom assets, animations, and complex configuration.

### Theme Mod (`fantasy_theme/`)
A theme mod that replaces existing assets with a different visual style.

## Creating a New Mod

1. **Generate mod structure**:
   ```bash
   just mod my_new_mod
   ```

2. **Copy an example as starting point**:
   ```bash
   cp -r examples/mods/basic_mod mods/my_new_mod
   ```

3. **Customize the mod**:
   - Edit `mod.toml` with your mod information
   - Add your assets to the appropriate directories
   - Update asset specifications

4. **Process mod assets**:
   ```bash
   just mod my_new_mod
   ```

## Mod Structure

```
mods/my_mod/
├── mod.toml              # Mod metadata and configuration
├── sprites/              # Mod sprite assets
│   ├── buildings/
│   ├── terrain/
│   └── units/
├── data/
│   └── sprites.toml      # Generated sprite metadata
├── atlases/              # Generated texture atlases
└── source_assets/        # Source files for asset generation
    ├── buildings/
    ├── terrain/
    └── units/
```

## Asset Pipeline Integration

Mods use the same asset pipeline as the base game:
- **Quality Standards**: Same strict requirements
- **Processing**: Automatic normalization and validation
- **Metadata**: Generated sprites.toml for mod assets
- **Isolation**: Mod assets are completely isolated from base game