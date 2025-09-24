# Old Times

A 2D isometric RTS/city-building game inspired by Knights & Merchants, built with Rust and Bevy ECS.

## Features

- **Deterministic simulation**: Fixed tick rate ensures reproducible gameplay
- **Headless-first architecture**: Core simulation runs independently of rendering
- **Data-driven design**: Buildings, recipes, and units defined in TOML files
- **Advanced asset pipeline**: Automated asset processing with AI generation support
- **Metadata-driven rendering**: Sprites loaded from TOML metadata with hot-reload
- **Modding support**: Easy to create and load game modifications with isolated assets
- **Replay system**: Record and verify deterministic gameplay
- **Performance focused**: Optimized for large maps and many entities

## Quick Start

### Requirements

- Rust stable (1.70+)
- Python 3.8+ (for asset pipeline)
- Git
- Just (optional, for convenient commands)

### Building

```bash
git clone https://github.com/yourusername/old-times
cd old-times

# Set up asset pipeline (optional)
just dev-setup

# Build the game
cargo build --release
```

### Running the Game

```bash
# Generate assets (first time setup)
just all

# Start the client with rendering and UI
cargo run -p oldtimes-client

# Run headless simulation
cargo run -p oldtimes-headless -- run --map demo --ticks 1000

# Run performance benchmark
cargo run -p oldtimes-headless -- benchmark --scenario standard
```

## Controls

### Camera
- **WASD** or **Arrow Keys**: Move camera
- **Mouse Wheel**: Zoom in/out

### Building Placement
- **Q**: Select Lumberjack
- **E**: Select Sawmill  
- **R**: Select Farm
- **T**: Select Mill
- **Y**: Select Bakery
- **U**: Select Quarry
- **Left Click**: Place selected building
- **ESC**: Cancel building selection

### Game Speed
- **SPACE**: Pause/Resume
- **1**: Normal speed (1x)
- **2**: Fast speed (2x)
- **4**: Very fast speed (4x)

### Debug
- **F1**: Toggle debug overlay (FPS, entity count, cursor position)
- **F2**: Toggle tile highlighter under cursor
- **F3**: Toggle performance metrics (planned)

## Architecture

### Core Components

- **oldtimes-core**: Headless simulation engine (ECS, economy, pathfinding)
- **oldtimes-headless**: CLI server for testing and benchmarks
- **oldtimes-client**: Game client with rendering and UI. It is built on a modular, plugin-based architecture:
  - `MapPlugin`: Renders the isometric map.
  - `CameraPlugin`: Handles camera controls and coordinate projection.
  - `BuildModePlugin`: Manages building placement logic and UI feedback.
  - `UiPlugin`: Renders the HUD for resources.
  - `EconomyPlugin`: Manages client-side economic state and game speed.
  - `DebugPlugin`: Provides debug overlays and tools.

### Key Systems

- **Tick System**: Maintains deterministic 20 TPS simulation
- **Pathfinding**: A* with caching for efficient movement
- **Production**: Recipe-based crafting with resource chains
- **Transport**: Automatic resource distribution between buildings
- **Construction**: Building placement and construction progress

## Asset Pipeline

Old Times features a comprehensive asset pipeline that handles:

- **Asset Generation**: Download CC0 assets, generate with AI providers
- **Processing**: Normalize to isometric format, create texture atlases
- **Quality Validation**: Ensure assets meet strict standards
- **Metadata Generation**: Create structured sprite metadata
- **Mod Support**: Generate isolated mod assets

### Quick Asset Commands

```bash
# Complete asset pipeline
just all

# Individual steps
just kenney    # Process Kenney asset packs
just atlas     # Create texture atlases
just validate  # Validate asset quality
```

See [GRAPHICS_GUIDE.md](GRAPHICS_GUIDE.md) for detailed asset pipeline documentation.

## Data Files

Game content is defined in TOML files under `assets/data/`:

- `buildings.toml`: Building definitions
- `recipes.toml`: Production recipes
- `workers.toml`: Worker unit types
- `sprites.toml`: Sprite metadata (auto-generated)
- `mapgen.toml`: Map generation settings

### Example Building Definition

```toml
[lumberjack]
name = "Lumberjack"
construction_time = 30.0
worker_capacity = 2
stockpile_capacity = 20
size = [2, 2]

[lumberjack.construction_cost]
stone = 5
```

### Example Recipe Definition

```toml
[make_planks]
name = "Make Planks"
production_time = 8.0
required_building = "sawmill"

[make_planks.inputs]
wood = 1

[make_planks.outputs]
planks = 2
```

## Production Chains

The game features interconnected production chains:

1. **Wood Chain**: Forest → Lumberjack → Wood → Sawmill → Planks
2. **Food Chain**: Farm → Grain → Mill → Flour → Bakery → Bread  
3. **Stone Chain**: Quarry → Stone (used for construction)

## Modding

Create mods using the asset pipeline:

```bash
# Generate mod structure and assets
just mod my-awesome-mod
```

This creates:
```
mods/
  my-awesome-mod/
    mod.toml          # Mod metadata
    sprites/          # Mod-specific sprites
    data/
      sprites.toml    # Sprite metadata
      buildings.toml  # New buildings
      recipes.toml    # New recipes
```

Mods are loaded automatically and can override base game content. The asset pipeline ensures mod assets meet the same quality standards as base game assets.

## Testing

```bash
# Run all tests
cargo test

# Run deterministic test
cargo test test_deterministic_simulation

# Validate data files
cargo run -p oldtimes-headless -- validate-data --data-dir assets/data
```

## Performance

Target performance on a modern system:
- **Tick Time**: ≤5ms for 128×128 map with 200 workers and 50 buildings
- **Memory**: Efficient ECS with minimal allocations in hot paths
- **TPS**: Stable 20+ ticks per second

Monitor performance with:
```bash
cargo run -p oldtimes-headless -- benchmark --scenario long
```

## Development

### Project Structure

```
old-times/
├── crates/
│   ├── oldtimes-core/      # Core simulation engine
│   ├── oldtimes-headless/  # Headless binary
│   └── oldtimes-client/    # Game client
│       └── src/
│           └── plugins/    # Client-side plugins
├── assets/
│   └── data/              # Game data files
├── mods/
│   └── example/           # Example mod
├── docs/                  # Documentation
└── scripts/               # Development scripts
```

### Adding New Buildings

1. Add building definition to `assets/data/buildings.toml`
2. Add sprite metadata to `assets/data/sprites.toml` (or let pipeline generate it)
3. Add production recipes to `assets/data/recipes.toml`
4. Run asset pipeline: `just all`
5. Update client UI for building selection (optional)
6. Test with `cargo run -p oldtimes-headless -- validate-data`

### Code Style

- Use `rustfmt` for formatting
- Follow `clippy` recommendations
- Add tests for new functionality
- Document public APIs

## License

MIT License - see LICENSE file for details.

## Contributing

See CONTRIBUTING.md for development guidelines and how to submit changes.

---

**Note**: This is a work-in-progress game. Features and APIs may change during development.