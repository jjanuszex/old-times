# Old Times - Graphics and Asset Pipeline Guide

## Overview

Old Times is a 2D isometric RTS game with comprehensive graphics support for buildings, terrain, and units. This guide covers the modern asset pipeline system that handles asset generation, processing, and management through automated tools.

## Asset Pipeline System

The asset pipeline is a comprehensive Python-based toolchain that handles:
- **Asset Generation**: Download CC0 assets, generate with AI providers
- **Processing**: Normalize assets to isometric 2:1 format, create texture atlases
- **Quality Validation**: Ensure all assets meet strict quality standards
- **Metadata Generation**: Create structured metadata files for the game engine
- **Mod Support**: Generate assets into isolated mod directories

### Quick Start

```bash
# Set up the pipeline (one-time setup)
just dev-setup

# Run the complete pipeline
just all

# Or use individual commands
just link      # Create asset symlinks
just kenney    # Process Kenney asset packs
just atlas     # Create texture atlases
just validate  # Validate asset quality
```

## Asset Structure

```
assets/
├── sprites/           # Normalized game textures
│   ├── lumberjack.png # Buildings (64×96, 128×96, etc.)
│   ├── sawmill.png
│   ├── farm.png
│   ├── mill.png
│   ├── bakery.png
│   ├── quarry.png
│   ├── grass.png      # Terrain tiles (64×32)
│   ├── water.png
│   ├── stone.png
│   ├── forest.png
│   ├── road.png
│   └── worker.png     # Units (64×64 frames)
├── atlases/           # Texture atlases for animations
│   ├── worker_atlas.png    # 512×512 atlas (8×8 frames)
│   └── worker_atlas.json   # Frame coordinate map
├── data/              # Asset metadata
│   └── sprites.toml   # Complete sprite metadata
├── preview/           # Asset previews for verification
│   ├── asset_preview.png      # Grid preview of all assets
│   ├── building_alignment.png # Building alignment verification
│   └── unit_preview.png       # Animation frame previews
├── ui/                # UI elements
│   └── panel_bg.png
├── textures/          # Additional textures
└── fonts/             # Fonts (future use)
```

## Asset Standards

### Isometric Requirements

All assets must conform to strict isometric 2:1 standards:

- **Tiles**: Exactly 64×32 pixels
- **Buildings**: Multiples of tile size (64×96, 128×96, 192×96, etc.)
- **Units**: 64×64 pixels per animation frame
- **Transparency**: Completely transparent backgrounds (alpha = 0)
- **Alignment**: Perfect grid alignment for isometric projection

### Quality Standards

The pipeline enforces these quality requirements:
- **Pixel-perfect dimensions**: No deviation from required sizes
- **Transparent backgrounds**: Alpha channel validation
- **Edge sharpness**: Clean, crisp edges without anti-aliasing artifacts
- **Isometric compliance**: 2:1 aspect ratio for buildings and terrain

## Asset Pipeline Commands

### Core Commands

```bash
# Create asset directory symlink (required first step)
just link

# Download and process Kenney CC0 asset packs
just kenney

# Generate assets using AI providers (if configured)
just cloud

# Create texture atlases for animated units
just atlas

# Generate assets for a specific mod
just mod my_mod_name

# Validate all assets meet quality standards
just validate

# Run complete pipeline (recommended)
just all
```

### Configuration

The pipeline uses `scripts/asset_pipeline.toml` for configuration:

```toml
[sources]
kenney_packs = ["isometric-city-pack", "medieval-rts-pack"]
ai_provider = "none"  # or "stable-diffusion", "replicate", "openai"

[processing]
tile_size = [64, 32]        # Isometric tile dimensions
unit_frame_size = [64, 64]  # Animation frame size
atlas_padding = 0           # Atlas frame padding

[quality]
max_alpha_threshold = 0.01      # Transparency validation
edge_sharpness_threshold = 0.5  # Edge quality validation

[paths]
assets_dir = "assets"
sprites_dir = "assets/sprites"
atlases_dir = "assets/atlases"
```

### Environment Variables

Override configuration with environment variables:

```bash
# Asset sources
export ASSET_PIPELINE_KENNEY_PACKS="pack1,pack2,pack3"
export ASSET_PIPELINE_AI_PROVIDER="stable-diffusion"

# Processing settings
export ASSET_PIPELINE_TILE_WIDTH=64
export ASSET_PIPELINE_TILE_HEIGHT=32

# Use custom configuration
CONFIG=custom.toml just all
```

## Adding New Assets

### Step-by-Step Guide

#### 1. Adding a New Building

```bash
# 1. Add the building specification to your asset source
# 2. Run the pipeline to process it
just all

# 3. The pipeline will:
#    - Download/generate the asset
#    - Normalize it to proper dimensions
#    - Add it to sprites.toml metadata
#    - Validate quality standards
```

#### 2. Adding a New Terrain Tile

```bash
# 1. Place source image in appropriate provider directory
# 2. Configure in asset_pipeline.toml if needed
# 3. Run pipeline
just all

# The tile will be automatically:
#    - Resized to 64×32 pixels
#    - Given transparent background
#    - Validated for isometric compliance
```

#### 3. Adding Animated Units

```bash
# 1. Provide 64 animation frames (8 directions × 8 walking frames)
# 2. Run atlas generation
just atlas

# This creates:
#    - 512×512 texture atlas
#    - JSON frame coordinate map
#    - Updated sprites.toml metadata
```

### Manual Asset Creation

If creating assets manually, follow these specifications:

#### Tiles (Terrain)
- **Size**: Exactly 64×32 pixels
- **Format**: PNG with alpha channel
- **Background**: Completely transparent (alpha = 0)
- **Style**: Isometric 2:1 projection
- **Edges**: Sharp, no anti-aliasing

#### Buildings
- **Size**: Multiples of 32 pixels height (64×96, 128×96, 192×96)
- **Width**: Multiples of 64 pixels for multi-tile buildings
- **Alignment**: Bottom edge aligns with isometric grid
- **Details**: Include shadows, depth, architectural details
- **Transparency**: Transparent background, solid building

#### Units
- **Frame Size**: Exactly 64×64 pixels per frame
- **Animation**: 8 directions × 8 walking frames = 64 total frames
- **Directions**: N, NE, E, SE, S, SW, W, NW (clockwise from north)
- **Centering**: Unit centered in frame
- **Consistency**: Consistent lighting and style across frames

## Animation Creation Guide

### Creating Walking Animations

The pipeline expects unit animations in a specific format:

#### Frame Layout
```
Direction Layout (8 directions):
N  (0°)   - North
NE (45°)  - Northeast  
E  (90°)  - East
SE (135°) - Southeast
S  (180°) - South
SW (225°) - Southwest
W  (270°) - West
NW (315°) - Northwest
```

#### Walking Cycle (8 frames per direction)
```
Frame 0: Contact (left foot down)
Frame 1: Recoil (left foot lifts)
Frame 2: Passing (left leg passes right)
Frame 3: High point (left foot highest)
Frame 4: Contact (right foot down)
Frame 5: Recoil (right foot lifts)
Frame 6: Passing (right leg passes left)
Frame 7: High point (right foot highest)
```

#### Creating Animation Frames

1. **Source Frames**: Create 64 individual 64×64 PNG frames
2. **Naming Convention**: `unit_name_dir_frame.png` (e.g., `worker_N_0.png`)
3. **Directory Structure**:
   ```
   source_animations/
   └── worker/
       ├── N/
       │   ├── 0.png, 1.png, ..., 7.png
       ├── NE/
       │   ├── 0.png, 1.png, ..., 7.png
       └── ... (all 8 directions)
   ```

4. **Generate Atlas**:
   ```bash
   just atlas
   ```

This creates:
- `assets/atlases/worker_atlas.png` (512×512 texture atlas)
- `assets/atlases/worker_atlas.json` (frame coordinate map)
- Updated `assets/data/sprites.toml` with animation metadata

### Animation Metadata

The generated `sprites.toml` includes animation properties:

```toml
[units.worker]
kind = "unit"
source = "atlases/worker_atlas.png"
frame_size = [64, 64]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "dirs_rows"
atlas_map = "atlases/worker_atlas.json"
```

## Mod Development

### Creating Asset Mods

The pipeline supports creating isolated mod assets:

```bash
# Generate assets for a new mod
just mod my_awesome_mod

# This creates:
# mods/my_awesome_mod/
# ├── sprites/          # Mod-specific sprites
# ├── data/
# │   └── sprites.toml  # Mod sprite metadata
# └── mod.toml          # Mod manifest
```

### Mod Structure

```
mods/my_awesome_mod/
├── mod.toml              # Mod metadata and configuration
├── sprites/              # Mod sprite assets
│   ├── custom_building.png
│   ├── new_terrain.png
│   └── special_unit.png
├── data/
│   └── sprites.toml      # Sprite metadata for mod assets
└── atlases/              # Mod-specific atlases (if any)
    ├── custom_unit_atlas.png
    └── custom_unit_atlas.json
```

### Mod Configuration

Example `mod.toml`:

```toml
[mod]
name = "My Awesome Mod"
version = "1.0.0"
author = "Your Name"
description = "Adds new buildings and units to Old Times"

[assets]
sprites_count = 15
atlases_count = 2
buildings = ["custom_building", "advanced_mill"]
units = ["custom_unit"]
terrain = ["new_terrain"]

[dependencies]
game_version = ">=1.0.0"
```

### Mod Asset Processing

Mods use the same quality standards as base game assets:

1. **Asset Isolation**: Mod assets are processed separately
2. **Quality Validation**: Same strict standards apply
3. **Metadata Generation**: Mod-specific sprites.toml created
4. **Atlas Support**: Animated units get their own atlases

### Mod Development Workflow

```bash
# 1. Create mod directory structure
just mod my_mod

# 2. Add your source assets to appropriate directories
# 3. Configure mod-specific settings in mod.toml
# 4. Process mod assets
just mod my_mod

# 5. Validate mod assets
python -m scripts.asset_pipeline.cli mod my_mod --validate
```

## Troubleshooting

### Common Issues and Solutions

#### Asset Pipeline Issues

**Problem**: `ERROR: Asset pipeline dependencies not installed`
```bash
# Solution: Install dependencies
just dev-setup
```

**Problem**: `ERROR: Configuration file not found`
```bash
# Solution: Create or specify configuration file
cp scripts/asset_pipeline.toml my_config.toml
CONFIG=my_config.toml just all
```

**Problem**: `ERROR: Symlink creation failed`
```bash
# Solution: Check permissions and force recreation
just link --force
```

#### Asset Quality Issues

**Problem**: `VALIDATION ERROR: Tile size 65×33 != required 64×32`
- **Cause**: Asset doesn't meet exact dimension requirements
- **Solution**: The pipeline auto-normalizes assets, but source quality matters
- **Fix**: Provide higher quality source assets

**Problem**: `VALIDATION ERROR: Background not transparent`
- **Cause**: Asset has non-transparent background pixels
- **Solution**: Pipeline enforces transparency, check source assets

**Problem**: `VALIDATION ERROR: Building not aligned to isometric grid`
- **Cause**: Building doesn't follow 2:1 isometric projection
- **Solution**: Use proper isometric source assets or let pipeline normalize

#### Performance Issues

**Problem**: Pipeline runs slowly
- **Cause**: Large number of assets or high-resolution sources
- **Solutions**:
  - Use `--skip-preview` to skip preview generation
  - Process specific steps: `just kenney` instead of `just all`
  - Use smaller source images

**Problem**: High memory usage during processing
- **Cause**: Processing many large images simultaneously
- **Solution**: The pipeline processes assets sequentially to manage memory

#### File System Issues

**Problem**: `Permission denied` errors
- **Cause**: Insufficient file system permissions
- **Solutions**:
  - Check directory permissions
  - Run with appropriate user permissions
  - On Windows, run as administrator if needed

**Problem**: `Symlink not supported` on Windows
- **Cause**: Windows symlink restrictions
- **Solutions**:
  - Enable Developer Mode in Windows 10/11
  - Run command prompt as administrator
  - Use directory junction instead (pipeline handles this automatically)

### Validation and Testing

#### Validate Pipeline Setup
```bash
# Test configuration
just test-config

# Test symlink functionality  
just test-symlink

# Check overall pipeline status
just status

# Validate existing assets
just validate
```

#### Debug Asset Issues
```bash
# Generate previews to visually inspect assets
python -m scripts.asset_pipeline.cli preview

# Check specific asset validation
python -m scripts.asset_pipeline.cli validate --strict

# Validate specific mod
python -m scripts.asset_pipeline.cli mod my_mod --validate
```

### Getting Help

#### Command Help
```bash
# General help
just help

# Detailed help with examples
just help-detailed

# CLI command help
python -m scripts.asset_pipeline.cli --help
python -m scripts.asset_pipeline.cli COMMAND --help
```

#### Configuration Help
```bash
# Show current configuration
python -m scripts.asset_pipeline.cli config --show

# Show available environment variables
python -m scripts.asset_pipeline.cli config --env-vars

# Validate configuration
python -m scripts.asset_pipeline.cli config --validate
```

## Advanced Usage

### Custom Asset Providers

The pipeline supports multiple asset sources:

#### Kenney Asset Packs (CC0)
```toml
[sources]
kenney_packs = [
    "isometric-city-pack",
    "medieval-rts-pack", 
    "nature-pack",
    "fantasy-pack"
]
```

#### AI Asset Generation
```toml
[sources]
ai_provider = "stable-diffusion"

[sources.ai_config]
stable_diffusion_url = "http://localhost:7860"
prompt_template = "isometric {asset_type} for medieval RTS game, 2:1 aspect ratio, transparent background"
```

#### Local Asset Sources
Place assets in designated directories and the pipeline will process them automatically.

### Pipeline Customization

#### Custom Processing Steps
```bash
# Run specific pipeline steps
python -m scripts.asset_pipeline.cli all --steps="kenney,atlas,validate"

# Skip certain steps
python -m scripts.asset_pipeline.cli all --skip-validation --skip-preview
```

#### Custom Quality Standards
```toml
[quality]
max_alpha_threshold = 0.005     # Stricter transparency
edge_sharpness_threshold = 0.8  # Sharper edges required
```

### Integration with Game Engine

#### Metadata-Driven Asset Loading

The pipeline generates `sprites.toml` that the Rust game engine automatically consumes:

```rust
// Rust integration is now fully implemented
#[derive(Resource)]
pub struct SpriteMetadataResource {
    pub metadata: Option<SpriteMetadata>,
    pub atlas_maps: HashMap<String, AtlasFrameMap>,
}

// Assets are loaded based on metadata with fallback support
fn load_game_assets(
    mut commands: Commands, 
    asset_server: Res<AssetServer>,
    sprite_metadata: Option<Res<SpriteMetadataResource>>,
) {
    let assets = if let Some(metadata) = sprite_metadata {
        load_assets_from_metadata(&asset_server, &metadata)
    } else {
        load_assets_fallback(&asset_server)  // Backward compatibility
    };
    commands.insert_resource(assets);
}
```

#### Sprite Metadata Format

The `assets/data/sprites.toml` file contains complete sprite definitions:

```toml
[tiles.grass]
kind = "tile"
size = [32, 32]
source = "sprites/grass.png"

[buildings.lumberjack]
kind = "building"
size = [64, 64]
source = "sprites/lumberjack.png"
tile_footprint = [2, 2]

[units.worker]
kind = "unit"
source = "sprites/worker.png"
frame_size = [32, 32]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "single_sprite"
```

#### Hot Reload Support

The game engine includes hot-reload support for development:

```rust
// Hot-reload system automatically reloads sprites.toml changes
pub fn hot_reload_sprite_metadata_system(
    mut metadata_resource: ResMut<SpriteMetadataResource>,
) {
    // Automatically reloads metadata in debug builds
}
```

#### Hot Reload Support

The pipeline and game engine support development workflows:

```bash
# Watch for changes and auto-regenerate
# (Future enhancement)
python -m scripts.asset_pipeline.cli watch
```

**Game Engine Hot Reload**: The Rust game engine automatically reloads `sprites.toml` changes during development (debug builds only), allowing for rapid iteration without restarting the game.

### Performance Optimization

#### Texture Atlas Benefits
- **Reduced Draw Calls**: Multiple sprites in single texture
- **Better GPU Utilization**: Fewer texture switches
- **Memory Efficiency**: Optimized texture memory usage

#### Caching System
The pipeline includes intelligent caching:
- **Source Asset Caching**: Downloaded assets cached locally
- **Processing Cache**: Avoid reprocessing unchanged assets
- **Incremental Updates**: Only process modified assets

### Future Enhancements

The asset pipeline is designed for extensibility:

- **Additional AI Providers**: OpenAI DALL-E, Midjourney integration
- **Advanced Animations**: Multi-layer animations, particle effects
- **Procedural Generation**: Algorithmic asset generation
- **Asset Optimization**: Automatic compression, format conversion
- **Hot Reload**: Real-time asset updates during development
- **Asset Validation**: Advanced quality metrics and compliance checking
- **Batch Processing**: Parallel processing for large asset sets
- **Version Control Integration**: Git hooks for asset processing

## Running the Game

### Client (Graphical Version)

```bash
# Compile and run
cargo run -p oldtimes-client

# Or build release
cargo build --release -p oldtimes-client
./target/release/oldtimes-client
```

### Controls

- **WASD / Arrow Keys**: Move camera
- **Q**: Select Lumberjack
- **E**: Select Sawmill  
- **R**: Select Farm
- **T**: Select Mill
- **Y**: Select Bakery
- **U**: Select Quarry
- **LMB**: Place building
- **ESC**: Cancel selection
- **SPACE**: Pause/Resume
- **1/2/4**: Game speed
- **F1**: Debug overlay
- **F2**: Pathfinding debug
- **F3**: Performance metrics

### Headless Version (Server)

```bash
# Simulation without graphics
cargo run -p oldtimes-headless -- run --ticks 1000

# Performance benchmark
cargo run -p oldtimes-headless -- benchmark --scenario quick

# Data validation
cargo run -p oldtimes-headless -- validate-data
```

## Architecture Integration

### Asset Loading System

```rust
#[derive(Resource)]
pub struct GameAssets {
    // Building textures
    pub lumberjack: Handle<Image>,
    pub sawmill: Handle<Image>,
    // ... other buildings
    
    // Terrain textures  
    pub grass: Handle<Image>,
    pub water: Handle<Image>,
    // ... other terrain types
    
    // Unit textures and atlases
    pub worker: Handle<Image>,
    pub worker_atlas: Handle<TextureAtlas>,
}

// Metadata-driven loading with fallback support
#[derive(Resource)]
pub struct SpriteMetadataResource {
    pub metadata: Option<SpriteMetadata>,
    pub atlas_maps: HashMap<String, AtlasFrameMap>,
}
```

### Rendering Systems

1. **load_sprite_metadata_system**: Loads sprite metadata from `sprites.toml` at startup
2. **load_game_assets**: Loads textures using metadata or fallback paths
3. **render_map_system**: Renders map with terrain textures
4. **render_buildings_system**: Renders buildings with appropriate sprites
5. **render_workers_system**: Renders units with animation support
6. **hot_reload_sprite_metadata_system**: Hot-reloads metadata during development

### Rendering Layers

- **Z = 0.0**: Terrain (grass, water, stone, forest, road)
- **Z = 1.0**: Buildings (lumberjack, sawmill, farm, mill, bakery, quarry)
- **Z = 2.0**: Units (worker)
- **Z = 100.0**: UI