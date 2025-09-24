# oldtimes-core

Core simulation engine for Old Times - a headless, deterministic game simulation library.

## Overview

This crate contains the core game logic, ECS systems, and simulation engine that powers Old Times. It's designed to run independently of any rendering or UI framework, making it suitable for:

- Headless servers
- Automated testing
- Performance benchmarking
- Replay verification
- AI training

## Features

- **Deterministic Simulation**: Fixed tick rate ensures reproducible gameplay
- **ECS Architecture**: Built on Bevy ECS for performance and flexibility
- **Pathfinding**: A* algorithm with caching for efficient movement
- **Economic System**: Complex production chains and resource management
- **Save/Load**: Complete game state serialization
- **Modding Support**: Data-driven configuration system

## Key Components

### Core Systems
- `TickSystem`: Maintains simulation timing and determinism
- `PathfindingSystem`: Handles unit movement and navigation
- `ProductionSystem`: Manages building production and recipes
- `TransportSystem`: Automatic resource distribution
- `ConstructionSystem`: Building placement and construction

### Components
- `Position`: World coordinates for entities
- `Building`: Structure data and production capabilities
- `Worker`: Unit behavior and task management
- `Stockpile`: Resource storage and capacity
- `Producer`: Recipe execution and crafting

### Resources
- `GameTick`: Current simulation time and TPS settings
- `MapData`: Terrain and tile information
- `GameConfig`: Buildings, recipes, and game rules
- `PathfindingCache`: Performance optimization for movement

## Usage

### Basic Simulation

```rust
use oldtimes_core::SimulationApp;

let mut sim = SimulationApp::new();
sim.initialize_demo();

// Run for 1000 ticks
sim.run_ticks(1000);

println!("Current tick: {}", sim.current_tick());
```

### Event Handling

```rust
use oldtimes_core::{SimulationApp, PlaceBuildingEvent, Position};

let mut sim = SimulationApp::new();
sim.initialize_demo();

// Place a building
sim.send_event(PlaceBuildingEvent {
    building_type: "lumberjack".to_string(),
    position: Position::new(10, 10),
});

sim.tick(); // Process the event
```

### State Management

```rust
// Save game state
sim.save_state("savegame.ron")?;

// Load game state
sim.load_state("savegame.ron")?;

// Calculate state hash for determinism verification
let hash = sim.calculate_state_hash();
```

## Performance

The simulation is optimized for:
- **Target**: ≤5ms per tick for standard scenarios
- **Scalability**: 200+ workers, 50+ buildings on 128×128 maps
- **Memory**: Minimal allocations in hot paths
- **Determinism**: Frame-rate independent simulation

## Testing

```bash
# Run all core tests
cargo test -p oldtimes-core

# Run determinism tests
cargo test test_deterministic_simulation

# Run performance tests
cargo test --release test_performance
```

## Data-Driven Configuration

Game content is defined in TOML files:

```toml
# buildings.toml
[lumberjack]
name = "Lumberjack"
construction_time = 30.0
worker_capacity = 2
stockpile_capacity = 20

# recipes.toml
[harvest_wood]
name = "Harvest Wood"
production_time = 10.0
required_building = "lumberjack"

[harvest_wood.outputs]
wood = 2
```

## Architecture

```
SimulationApp
├── ECS World (Bevy)
├── Systems (Production, Pathfinding, etc.)
├── Resources (GameTick, MapData, etc.)
├── Events (PlaceBuilding, AssignWorker, etc.)
└── Components (Position, Building, Worker, etc.)
```

## API Stability

This crate follows semantic versioning:
- **Major**: Breaking API changes
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes and optimizations

Current version: 0.1.0 (pre-release, API may change)