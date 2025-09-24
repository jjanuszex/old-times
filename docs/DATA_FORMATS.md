# Data Formats

This document describes the TOML data formats used to define game content in Old Times.

## Buildings (`buildings.toml`)

Buildings are structures that can be constructed and house workers for production.

### Format

```toml
[building_id]
name = "Display Name"
construction_time = 30.0          # Time in seconds to construct
worker_capacity = 2               # Maximum workers that can be assigned
stockpile_capacity = 20           # Maximum items that can be stored
size = [2, 2]                    # Width and height in tiles

[building_id.construction_cost]
resource_name = amount            # Resources required to build
```

### Example

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

### Fields

- **name**: Human-readable building name displayed in UI
- **construction_time**: Time in seconds for construction to complete
- **worker_capacity**: Maximum number of workers that can be assigned
- **stockpile_capacity**: Maximum number of items the building can store
- **size**: Building footprint as [width, height] in tiles
- **construction_cost**: Table of resources required to construct

## Recipes (`recipes.toml`)

Recipes define production processes that convert input resources to output resources.

### Format

```toml
[recipe_id]
name = "Display Name"
production_time = 10.0            # Time in seconds to complete
required_building = "building_id" # Building type that can use this recipe

[recipe_id.inputs]
resource_name = amount            # Resources consumed

[recipe_id.outputs]
resource_name = amount            # Resources produced
```

### Example

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

### Fields

- **name**: Human-readable recipe name
- **production_time**: Time in seconds to complete one production cycle
- **required_building**: Building type that can execute this recipe
- **inputs**: Table of resources consumed per production cycle
- **outputs**: Table of resources produced per production cycle

### Special Cases

- **Resource Sources**: Recipes with empty `inputs` table represent resource gathering
- **Multi-Output**: Recipes can produce multiple different resources
- **Efficiency**: Production speed scales with assigned workers

## Workers (`workers.toml`)

Worker types define the characteristics of units that perform tasks.

### Format

```toml
[worker_id]
name = "Display Name"
movement_speed = 1.0              # Movement speed multiplier
carrying_capacity = 5             # Maximum items that can be carried
```

### Example

```toml
[worker]
name = "Worker"
movement_speed = 1.0
carrying_capacity = 5

[fast_courier]
name = "Fast Courier"
movement_speed = 2.0
carrying_capacity = 3
```

### Fields

- **name**: Human-readable worker type name
- **movement_speed**: Speed multiplier for movement (1.0 = normal)
- **carrying_capacity**: Maximum number of items the worker can carry

## Map Generation (`mapgen.toml`)

Configuration for procedural map generation.

### Format

```toml
width = 64                        # Map width in tiles
height = 64                       # Map height in tiles
forest_density = 0.3              # Density of forest tiles (0.0-1.0)
stone_density = 0.1               # Density of stone deposits (0.0-1.0)
water_patches = 3                 # Number of water bodies
seed = 12345                      # Random seed for generation
```

### Fields

- **width**: Map width in tiles
- **height**: Map height in tiles  
- **forest_density**: Probability of forest tiles (0.0 to 1.0)
- **stone_density**: Probability of stone deposits (0.0 to 1.0)
- **water_patches**: Number of water bodies to generate
- **seed**: Random seed for reproducible generation

## Mod Metadata (`mod.toml`)

Metadata for game modifications.

### Format

```toml
name = "Mod Name"
version = "1.0.0"
description = "Mod description"
author = "Author Name"
priority = 100                    # Loading priority (higher = later)
```

### Fields

- **name**: Human-readable mod name
- **version**: Semantic version string
- **description**: Brief description of the mod
- **author**: Mod creator name
- **priority**: Loading order (higher priority mods override lower)

## Validation Rules

### General Rules
- All numeric values must be positive unless specified
- String fields cannot be empty
- Resource names must be valid identifiers (alphanumeric + underscore)

### Building Validation
- `construction_time` > 0.0
- `worker_capacity` > 0
- `stockpile_capacity` > 0
- `size` dimensions > 0
- Construction costs must have positive amounts

### Recipe Validation
- `production_time` > 0.0
- `required_building` must reference valid building
- Input/output amounts must be positive
- At least one output required
- No circular dependencies in production chains

### Worker Validation
- `movement_speed` > 0.0
- `carrying_capacity` > 0

### Map Generation Validation
- `width` and `height` > 0
- Density values between 0.0 and 1.0
- `water_patches` >= 0

## Data Loading Order

1. Load base game data from `assets/data/`
2. Scan `mods/` directory for mod folders
3. Load mod metadata and sort by priority
4. Apply mods in priority order (higher priority overrides)
5. Validate final merged configuration
6. Report any validation errors

## Hot Reloading

During development, data files can be reloaded without restarting:

```bash
# Validate data files
cargo run -p oldtimes-headless -- validate-data

# The client will automatically reload when files change (planned feature)
```

## Example Production Chain

Here's how to define a complete wood-to-planks production chain:

```toml
# buildings.toml
[lumberjack]
name = "Lumberjack"
construction_time = 30.0
worker_capacity = 2
stockpile_capacity = 20
size = [2, 2]

[sawmill]
name = "Sawmill"  
construction_time = 45.0
worker_capacity = 3
stockpile_capacity = 30
size = [3, 3]

# recipes.toml
[harvest_wood]
name = "Harvest Wood"
production_time = 10.0
required_building = "lumberjack"

[harvest_wood.outputs]
wood = 2

[make_planks]
name = "Make Planks"
production_time = 8.0
required_building = "sawmill"

[make_planks.inputs]
wood = 1

[make_planks.outputs]
planks = 2
```

This creates a production chain where:
1. Lumberjacks harvest wood from the environment
2. Sawmills convert wood into planks
3. The chain requires stone to build the structures