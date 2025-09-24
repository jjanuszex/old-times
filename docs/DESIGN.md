# Old Times Design Document

## Vision

Old Times is a 2D RTS/city-building game that captures the essence of classic economic simulation games like Knights & Merchants, while leveraging modern technology for improved performance, modding, and deterministic gameplay.

## Core Design Pillars

### 1. Economic Depth
- Complex production chains with interdependencies
- Resource scarcity and optimization challenges
- Meaningful trade-offs in building placement and worker allocation
- Dynamic supply and demand mechanics

### 2. Deterministic Simulation
- Reproducible gameplay for competitive play
- Reliable testing and debugging
- Replay system for learning and verification
- Frame-rate independent simulation

### 3. Modding-First Architecture
- Data-driven design enables easy content creation
- Hot-reloadable configuration files
- Clear modding APIs and documentation
- Community-driven content expansion

### 4. Performance Excellence
- Efficient ECS architecture for large-scale simulations
- Optimized pathfinding and resource management
- Scalable to hundreds of units and buildings
- Minimal system requirements

## Game Mechanics

### Resource System

#### Primary Resources
- **Wood**: Harvested from forests, used for construction and crafting
- **Stone**: Mined from quarries, primary construction material
- **Grain**: Grown on farms, food production base
- **Flour**: Processed grain, intermediate food product
- **Bread**: Final food product, consumed by population
- **Planks**: Processed wood, advanced construction material

#### Resource Properties
- **Stackable**: Resources stack in stockpiles up to capacity limits
- **Perishable**: Some resources decay over time (planned feature)
- **Quality**: Resources may have quality levels affecting recipes (planned)
- **Weight**: Affects transport capacity and speed

### Production Chains

#### Wood Chain
```
Forest → Lumberjack → Wood → Sawmill → Planks
```
- Lumberjacks harvest wood from forest tiles
- Sawmills convert wood to planks with 2:1 ratio
- Planks used for advanced construction

#### Food Chain
```
Farm → Grain → Mill → Flour → Bakery → Bread
```
- Farms produce grain over time
- Mills convert grain to flour
- Bakeries bake bread from flour
- Bread feeds population (planned feature)

#### Construction Chain
```
Quarry → Stone → Construction Sites
```
- Quarries extract stone from deposits
- Stone required for all building construction
- Limited stone deposits create strategic decisions

### Building System

#### Building Lifecycle
1. **Placement**: Player selects location and building type
2. **Construction**: Workers deliver materials and build over time
3. **Operation**: Completed buildings can be assigned workers
4. **Production**: Buildings with workers execute recipes
5. **Maintenance**: Buildings require upkeep (planned feature)

#### Building Categories

**Resource Extraction**
- Lumberjack: Harvests wood from adjacent forest
- Quarry: Mines stone from deposits
- Farm: Grows grain on fertile land

**Processing**
- Sawmill: Converts wood to planks
- Mill: Processes grain into flour
- Bakery: Bakes bread from flour

**Infrastructure**
- Warehouse: Stores large quantities of resources
- Road: Improves movement speed
- Bridge: Allows crossing water (planned)

#### Building Placement Rules
- Buildings require flat, unobstructed terrain
- Some buildings need specific terrain (farms need fertile land)
- Buildings block movement and other construction
- Strategic placement affects efficiency

### Worker System

#### Worker Behavior
- **Assignment**: Workers assigned to specific buildings
- **Tasks**: Idle workers seek tasks from assigned building
- **Transport**: Workers carry resources between buildings
- **Efficiency**: More workers increase production speed

#### Worker AI States
1. **Idle**: Waiting for tasks
2. **Moving**: Traveling to destination
3. **Working**: Performing production tasks
4. **Carrying**: Transporting resources

#### Pathfinding
- A* algorithm with terrain cost consideration
- Roads provide movement bonuses
- Dynamic obstacle avoidance
- Path caching for performance

### Economic Balance

#### Resource Flow
- Production rates balanced to create meaningful choices
- Bottlenecks encourage specialization and trade
- Seasonal variations add complexity (planned)
- Random events affect supply chains (planned)

#### Difficulty Scaling
- Map size affects resource distribution
- Terrain features create natural challenges
- Limited starting resources force prioritization
- Progressive complexity through technology trees (planned)

## Technical Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Client Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Rendering   │  │ UI System   │  │ Input       │     │
│  │ System      │  │             │  │ Handling    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                 Simulation Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ ECS Systems │  │ Pathfinding │  │ Economy     │     │
│  │             │  │ Engine      │  │ Simulation  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                   Data Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Game Data   │  │ Save System │  │ Mod Loader  │     │
│  │ (TOML)      │  │ (RON)       │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### ECS Design

#### Core Components
- **Position**: World coordinates for spatial entities
- **Building**: Structure data and state
- **Worker**: Unit behavior and assignment
- **Stockpile**: Resource storage and capacity
- **Producer**: Recipe execution capability

#### System Organization
- **Tick System**: Maintains simulation timing
- **Production System**: Handles recipe execution
- **Transport System**: Manages resource movement
- **Construction System**: Building lifecycle
- **Pathfinding System**: Movement calculation

### Performance Optimization

#### Hot Path Optimization
- Minimal allocations in per-tick systems
- Component access patterns optimized for cache
- Parallel processing where determinism allows
- Efficient data structures for common operations

#### Memory Management
- Pre-allocated collections for known sizes
- Object pooling for frequently created entities
- Careful lifetime management to prevent leaks
- Profiling integration for regression detection

#### Scalability Targets
- 1000+ entities at 60 FPS
- 10,000+ tiles with efficient rendering
- Sub-millisecond pathfinding for typical requests
- Deterministic behavior regardless of performance

## User Experience Design

### Interface Philosophy
- **Clarity**: Information presented clearly without clutter
- **Efficiency**: Common actions require minimal clicks
- **Feedback**: Clear indication of game state and player actions
- **Accessibility**: Support for different input methods and abilities

### Control Scheme

#### Camera Controls
- WASD/Arrow keys for panning
- Mouse wheel for zooming
- Edge scrolling support
- Minimap for quick navigation (planned)

#### Building Placement
- Hotkeys for quick building selection
- Visual preview before placement
- Clear indication of placement validity
- Undo/redo for construction (planned)

#### Information Display
- Hover tooltips for detailed information
- Resource counters always visible
- Production status indicators
- Debug overlays for development

### Visual Design

#### Art Style
- Clean, readable 2D sprites
- Consistent color palette
- Clear visual hierarchy
- Placeholder art during development

#### UI Design
- Minimal, functional interface
- Context-sensitive panels
- Keyboard shortcuts for power users
- Scalable UI for different resolutions

## Progression and Content

### Gameplay Progression
1. **Tutorial**: Learn basic mechanics
2. **Sandbox**: Free-form building and experimentation
3. **Scenarios**: Specific challenges and objectives
4. **Campaign**: Structured progression (planned)

### Content Expansion
- **Base Game**: Core buildings and resources
- **Mods**: Community-created content
- **DLC**: Official expansions (planned)
- **User Maps**: Custom scenarios and maps

### Modding Support

#### Content Types
- New buildings and recipes
- Custom worker types
- Map generation parameters
- UI themes and layouts

#### Modding Tools
- Data validation utilities
- Hot-reload during development
- Documentation and examples
- Community mod repository (planned)

## Multiplayer Considerations

### Architecture Preparation
- Deterministic simulation enables multiplayer
- Event-based input system
- State synchronization capabilities
- Replay system for debugging desync

### Planned Features
- Local multiplayer (shared screen)
- Network multiplayer (peer-to-peer)
- Spectator mode
- Replay sharing

## Success Metrics

### Technical Metrics
- Performance: 60 FPS with 500+ entities
- Stability: No crashes in 1-hour sessions
- Determinism: 100% replay accuracy
- Load times: <2 seconds for typical maps

### User Experience Metrics
- Learning curve: Tutorial completion rate
- Engagement: Session length and retention
- Modding: Community content creation
- Performance: Frame rate consistency

### Community Metrics
- Mod ecosystem growth
- Player-created content
- Community feedback incorporation
- Long-term player retention

## Future Vision

### Short-term Goals (6 months)
- Complete core gameplay loop
- Polish user interface
- Performance optimization
- Basic modding support

### Medium-term Goals (1 year)
- Campaign mode
- Advanced AI opponents
- Multiplayer implementation
- Comprehensive mod tools

### Long-term Goals (2+ years)
- 3D graphics option
- Mobile platform support
- Esports potential
- Educational applications

## Risk Mitigation

### Technical Risks
- **Performance**: Regular profiling and optimization
- **Complexity**: Incremental development and testing
- **Platform Support**: Cross-platform testing from start
- **Modding**: Clear APIs and extensive documentation

### Design Risks
- **Scope Creep**: Strict feature prioritization
- **Balance**: Extensive playtesting and iteration
- **Accessibility**: User testing with diverse players
- **Competition**: Focus on unique strengths and community

This design document serves as a living reference for the Old Times project, guiding development decisions while remaining flexible enough to adapt based on player feedback and technical discoveries.