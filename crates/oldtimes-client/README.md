# oldtimes-client

Game client with rendering and UI for Old Times.

## Overview

This is the main game client that provides the visual interface and user interaction for Old Times. It combines the core simulation engine with Bevy's rendering and UI systems to create a playable game experience.

## Features

- **2D Rendering**: Tile-based graphics with sprite rendering
- **Interactive UI**: Building placement, resource management, game controls
- **Real-time Visualization**: Live view of simulation state
- **Debug Tools**: Performance metrics, pathfinding visualization
- **Input Handling**: Keyboard and mouse controls
- **Camera System**: Pan and zoom navigation

## Controls

### Camera Movement
- **WASD** or **Arrow Keys**: Pan camera
- **Mouse Wheel**: Zoom in/out (planned)

### Building Placement
- **Q**: Select Lumberjack
- **E**: Select Sawmill
- **R**: Select Farm
- **T**: Select Mill
- **Y**: Select Bakery
- **U**: Select Quarry
- **Left Click**: Place selected building
- **ESC**: Cancel building selection

### Game Speed Control
- **SPACE**: Pause/Resume simulation
- **1**: Normal speed (1x)
- **2**: Fast speed (2x)
- **4**: Very fast speed (4x)

### Debug Features
- **F1**: Toggle debug overlay
- **F2**: Toggle pathfinding visualization
- **F3**: Toggle performance metrics

## Running the Game

### Prerequisites

- Rust stable (1.70+)
- Graphics drivers supporting OpenGL 3.3+ or Vulkan
- Audio drivers (for future sound support)

### Quick Start

```bash
# Clone and build
git clone <repository>
cd old-times
cargo run -p oldtimes-client
```

### Command Line Options

```bash
# Run with specific map
cargo run -p oldtimes-client -- --map demo

# Enable debug mode
cargo run -p oldtimes-client -- --debug

# Custom window size
cargo run -p oldtimes-client -- --width 1280 --height 720
```

## Gameplay

### Getting Started

1. **Launch the game**: The demo map will load automatically
2. **Camera navigation**: Use WASD to move around the map
3. **Place buildings**: Press Q to select Lumberjack, then click to place
4. **Observe production**: Buildings will automatically start working
5. **Speed control**: Use SPACE to pause, 1/2/4 to change speed

### Building Types

**Resource Extraction:**
- **Lumberjack (Q)**: Harvests wood from nearby forests
- **Quarry (U)**: Mines stone from deposits
- **Farm (R)**: Grows grain on fertile land

**Processing:**
- **Sawmill (E)**: Converts wood into planks
- **Mill (T)**: Processes grain into flour
- **Bakery (Y)**: Bakes bread from flour

### Production Chains

The game features interconnected production chains:

1. **Wood → Planks**: Lumberjack → Sawmill
2. **Grain → Flour → Bread**: Farm → Mill → Bakery
3. **Stone**: Quarry (for construction)

### Resource Management

- **Stockpiles**: Each building stores limited resources
- **Transport**: Workers automatically move resources between buildings
- **Efficiency**: More workers increase production speed
- **Bottlenecks**: Identify and resolve production constraints

## User Interface

### Main HUD

- **Top Bar**: Game information, current tick, speed controls
- **Bottom Bar**: Building selection hotkeys and help
- **Resource Counters**: Current stockpile levels (planned)

### Debug Overlay

Press F1 to toggle the debug overlay showing:
- Current tick and TPS
- Entity count
- System performance times
- Pathfinding cache statistics

### Visual Indicators

- **Building Colors**: Different colors for each building type
- **Construction Progress**: Semi-transparent buildings during construction
- **Worker Movement**: Blue dots representing workers
- **Terrain Types**: Color-coded tiles (grass, forest, water, stone, roads)

## Graphics and Performance

### Rendering System

- **2D Sprites**: Simple, efficient tile-based rendering
- **Layered Rendering**: Terrain → Buildings → Units → UI
- **Efficient Updates**: Only re-render changed elements
- **Scalable**: Handles large maps with many entities

### Performance Optimization

- **ECS Architecture**: Efficient component-based rendering
- **Frustum Culling**: Only render visible tiles
- **Batched Rendering**: Group similar sprites for efficiency
- **LOD System**: Planned for very large maps

### System Requirements

**Minimum:**
- OpenGL 3.3 or Vulkan support
- 2GB RAM
- 1GHz CPU
- 100MB disk space

**Recommended:**
- Dedicated graphics card
- 4GB RAM
- Multi-core CPU
- SSD storage

## Customization

### Graphics Settings

Currently hardcoded, planned settings:
- Window resolution
- Fullscreen mode
- VSync enable/disable
- Graphics quality levels

### UI Scaling

The UI automatically scales based on window size. Future versions will support:
- Manual UI scale factor
- Different UI themes
- Customizable hotkeys

## Development

### Architecture

```
Client App (Bevy)
├── Core Systems (from oldtimes-core)
├── Rendering Systems
│   ├── Map Renderer
│   ├── Building Renderer
│   └── Worker Renderer
├── UI Systems
│   ├── HUD Management
│   ├── Debug Overlay
│   └── Input Handling
└── Game State
    ├── Camera Controller
    ├── Building Placer
    └── Debug Settings
```

### Adding New Features

#### New Building Renderer

```rust
pub fn render_new_building_system(
    buildings: Query<(&Position, &NewBuilding), Changed<NewBuilding>>,
    mut commands: Commands,
) {
    for (position, building) in buildings.iter() {
        // Spawn sprite for new building type
        commands.spawn(SpriteBundle {
            sprite: Sprite {
                color: Color::PURPLE,
                custom_size: Some(Vec2::new(TILE_SIZE, TILE_SIZE)),
                ..default()
            },
            transform: Transform::from_xyz(
                position.x as f32 * TILE_SIZE,
                position.y as f32 * TILE_SIZE,
                1.0,
            ),
            ..default()
        });
    }
}
```

#### New UI Element

```rust
fn setup_new_ui_element(mut commands: Commands) {
    commands.spawn(NodeBundle {
        style: Style {
            position_type: PositionType::Absolute,
            top: Val::Px(10.0),
            right: Val::Px(10.0),
            // ... other style properties
        },
        background_color: Color::rgba(0.0, 0.0, 0.0, 0.8).into(),
        ..default()
    }).with_children(|parent| {
        parent.spawn(TextBundle::from_section(
            "New UI Element",
            TextStyle {
                font_size: 16.0,
                color: Color::WHITE,
                ..default()
            },
        ));
    });
}
```

### Building and Testing

```bash
# Debug build (faster compilation)
cargo build -p oldtimes-client

# Release build (better performance)
cargo build --release -p oldtimes-client

# Run tests
cargo test -p oldtimes-client

# Run with logging
RUST_LOG=debug cargo run -p oldtimes-client
```

### Platform Support

**Currently Supported:**
- Windows (x86_64)
- Linux (x86_64)
- macOS (x86_64, aarch64)

**Planned:**
- Web (WASM)
- Mobile (Android, iOS)

## Troubleshooting

### Common Issues

**Game Won't Start:**
- Check graphics driver updates
- Verify OpenGL/Vulkan support
- Try running with `RUST_LOG=error` for error details

**Poor Performance:**
- Use release build: `cargo run --release -p oldtimes-client`
- Close other applications
- Reduce window size
- Check system requirements

**Graphics Issues:**
- Update graphics drivers
- Try different rendering backends (planned feature)
- Check for hardware acceleration

**Input Not Working:**
- Ensure window has focus
- Check for conflicting software
- Try different input devices

### Debug Information

Enable debug logging to troubleshoot issues:

```bash
# Full debug logging
RUST_LOG=debug cargo run -p oldtimes-client

# Specific module logging
RUST_LOG=oldtimes_client::rendering=debug cargo run -p oldtimes-client

# Performance profiling
RUST_LOG=oldtimes_core::systems=trace cargo run -p oldtimes-client
```

### Performance Profiling

Use the built-in debug overlay (F1) to monitor:
- Frame rate and frame time
- System execution times
- Entity counts
- Memory usage (planned)

## Future Features

### Planned Improvements

**Graphics:**
- Improved sprite artwork
- Particle effects
- Lighting system
- Weather effects

**UI/UX:**
- Resource flow visualization
- Building upgrade system
- Technology tree
- Tutorial system

**Gameplay:**
- Save/load functionality
- Scenario editor
- Multiplayer support
- AI opponents

**Technical:**
- Asset hot-reloading
- Mod support in client
- Performance profiler
- Accessibility features

### Contributing

See the main CONTRIBUTING.md for guidelines on:
- Code style and conventions
- Testing requirements
- Pull request process
- Development setup

The client welcomes contributions in:
- UI/UX improvements
- Graphics and visual effects
- Performance optimizations
- Accessibility features
- Platform support