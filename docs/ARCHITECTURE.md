# Old Times Architecture

## Overview

Old Times is built with a headless-first architecture that separates simulation logic from presentation. This design enables deterministic gameplay, easy testing, and potential multiplayer support.

## Core Principles

### 1. Deterministic Simulation
- Fixed tick rate (20 TPS default)
- No frame-rate dependent logic
- Reproducible random number generation
- State hashing for verification

### 2. ECS Architecture
- Bevy ECS for entity management
- Component-based design
- System-based logic processing
- Event-driven communication

### 3. Data-Driven Design
- TOML configuration files
- Hot-reloadable content
- Modding support
- Schema validation

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  oldtimes-client │    │oldtimes-headless│
│                 │    │                 │
│  ┌─────────────┐│    │  ┌─────────────┐│
│  │ Rendering   ││    │  │ CLI Tools   ││
│  │ UI          ││    │  │ Benchmarks  ││
│  │ Input       ││    │  │ Validation  ││
│  └─────────────┘│    │  └─────────────┘│
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────┐
          │  oldtimes-core  │
          │                 │
          │ ┌─────────────┐ │
          │ │ Simulation  │ │
          │ │ ECS Systems │ │
          │ │ Pathfinding │ │
          │ │ Economy     │ │
          │ │ Save/Load   │ │
          │ └─────────────┘ │
          └─────────────────┘
```

## Core Systems

### Tick System
- Maintains consistent simulation rate
- Advances game state deterministically
- Profiles system performance
- Handles pause/speed control

### Pathfinding System
- A* algorithm with heuristics
- Path caching for performance
- Dynamic obstacle avoidance
- Supports different movement costs

### Production System
- Recipe-based crafting
- Resource consumption/generation
- Building efficiency based on workers
- Queue management

### Transport System
- Automatic resource distribution
- Worker-based carrying
- Priority-based delivery
- Stockpile management

### Construction System
- Building placement validation
- Progressive construction
- Resource requirements
- Worker assignment

## Data Flow

### Input Processing
1. User input (keyboard/mouse)
2. Convert to game events
3. Validate and queue events
4. Process during next tick

### Simulation Tick
1. Process input events
2. Update entity components
3. Run ECS systems
4. Generate output events
5. Update performance metrics

### Rendering (Client Only)
1. Query entity states
2. Update sprite positions
3. Render UI elements
4. Display debug information

## Component Design

### Core Components
- `Position`: World coordinates
- `Building`: Structure data
- `Worker`: Unit behavior
- `Stockpile`: Resource storage
- `Producer`: Crafting capability

### Marker Components
- `Blocked`: Pathfinding obstacle
- `Road`: Movement bonus
- `Selected`: UI selection state

## Event System

### Simulation Events
- `PlaceBuildingEvent`: Building construction
- `AssignWorkerEvent`: Worker management
- `StartProductionEvent`: Recipe activation
- `TransferResourceEvent`: Resource movement

### System Events
- `PathfindingRequestEvent`: Path calculation
- `MapChangedEvent`: Terrain updates
- `ProfileEvent`: Performance tracking

## Resource Management

### Game Resources
- `GameTick`: Simulation time
- `MapData`: Terrain information
- `GameConfig`: Data definitions
- `PathfindingCache`: Performance optimization

### Performance Resources
- `PerformanceMetrics`: System timing
- Memory pools for frequent allocations
- Object recycling for entities

## Modding Architecture

### Mod Loading
1. Scan `mods/` directory
2. Load `mod.toml` metadata
3. Sort by priority
4. Merge data files
5. Validate schemas

### Data Override
- Higher priority mods override lower
- Additive for new content
- Validation prevents conflicts
- Hot-reload during development

## Save System

### State Serialization
- RON format for human readability
- Component-based serialization
- Version compatibility
- Incremental saves (planned)

### Replay System
- Event recording
- Deterministic playback
- State verification
- Debugging support

## Performance Considerations

### Hot Path Optimization
- Minimal allocations in systems
- Component access patterns
- Cache-friendly data layout
- Parallel processing where safe

### Memory Management
- Pre-allocated collections
- Object pooling for entities
- Efficient pathfinding cache
- Garbage collection avoidance

### Profiling Integration
- System timing measurement
- Memory usage tracking
- Cache hit rate monitoring
- Performance regression detection

## Testing Strategy

### Unit Tests
- Component behavior
- System logic
- Data validation
- Utility functions

### Integration Tests
- Full simulation runs
- Determinism verification
- Performance benchmarks
- Mod loading

### Property Tests
- Random input validation
- State consistency checks
- Performance bounds
- Memory leak detection

## Future Architecture

### Planned Improvements
- Network multiplayer support
- Advanced AI systems
- Streaming world loading
- Visual scripting for mods

### Scalability Considerations
- Distributed simulation
- Level-of-detail systems
- Hierarchical pathfinding
- Async resource loading