use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Game tick counter for deterministic simulation
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct GameTick {
    pub current: u64,
    pub target_tps: u32, // Ticks per second
}

impl Default for GameTick {
    fn default() -> Self {
        Self {
            current: 0,
            target_tps: 20, // 20 TPS default
        }
    }
}

impl GameTick {
    pub fn new(target_tps: u32) -> Self {
        Self {
            current: 0,
            target_tps,
        }
    }
    
    pub fn tick(&mut self) {
        self.current += 1;
    }
    
    pub fn delta_time(&self) -> f32 {
        1.0 / self.target_tps as f32
    }
}

/// Map dimensions and tile data
#[derive(Resource, Debug, Clone, Serialize, Deserialize, Default)]
pub struct MapData {
    pub width: u32,
    pub height: u32,
    pub tiles: Vec<Vec<crate::components::Tile>>,
}

impl MapData {
    pub fn new(width: u32, height: u32) -> Self {
        let tiles = (0..height)
            .map(|_| {
                (0..width)
                    .map(|_| crate::components::Tile {
                        tile_type: crate::components::TileType::Grass,
                        elevation: 0,
                    })
                    .collect()
            })
            .collect();
            
        Self { width, height, tiles }
    }
    
    pub fn get_tile(&self, x: i32, y: i32) -> Option<&crate::components::Tile> {
        if x >= 0 && y >= 0 && (x as u32) < self.width && (y as u32) < self.height {
            self.tiles.get(y as usize)?.get(x as usize)
        } else {
            None
        }
    }
    
    pub fn set_tile(&mut self, x: i32, y: i32, tile: crate::components::Tile) -> bool {
        if x >= 0 && y >= 0 && (x as u32) < self.width && (y as u32) < self.height {
            if let Some(row) = self.tiles.get_mut(y as usize) {
                if let Some(cell) = row.get_mut(x as usize) {
                    *cell = tile;
                    return true;
                }
            }
        }
        false
    }
    
    pub fn is_valid_position(&self, x: i32, y: i32) -> bool {
        x >= 0 && y >= 0 && (x as u32) < self.width && (y as u32) < self.height
    }
}

/// Pathfinding cache for performance
#[derive(Resource, Debug, Default)]
pub struct PathfindingCache {
    pub cache: HashMap<(crate::components::Position, crate::components::Position), Vec<crate::components::Position>>,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub max_cache_size: usize,
}

impl PathfindingCache {
    pub fn new(max_size: usize) -> Self {
        Self {
            cache: HashMap::new(),
            cache_hits: 0,
            cache_misses: 0,
            max_cache_size: max_size,
        }
    }
    
    pub fn get(&mut self, from: crate::components::Position, to: crate::components::Position) -> Option<Vec<crate::components::Position>> {
        if let Some(path) = self.cache.get(&(from, to)) {
            self.cache_hits += 1;
            Some(path.clone())
        } else {
            self.cache_misses += 1;
            None
        }
    }
    
    pub fn insert(&mut self, from: crate::components::Position, to: crate::components::Position, path: Vec<crate::components::Position>) {
        if self.cache.len() >= self.max_cache_size {
            // Simple eviction: remove oldest entry
            if let Some(key) = self.cache.keys().next().cloned() {
                self.cache.remove(&key);
            }
        }
        self.cache.insert((from, to), path);
    }
    
    pub fn clear(&mut self) {
        self.cache.clear();
    }
    
    pub fn hit_rate(&self) -> f32 {
        let total = self.cache_hits + self.cache_misses;
        if total > 0 {
            self.cache_hits as f32 / total as f32
        } else {
            0.0
        }
    }
}

/// Performance metrics for debugging
#[derive(Resource, Debug, Default)]
pub struct PerformanceMetrics {
    pub system_times: HashMap<String, f32>,
    pub tick_time: f32,
    pub entities_count: u32,
    pub pathfinding_requests: u32,
}

impl PerformanceMetrics {
    pub fn record_system_time(&mut self, system_name: String, time_ms: f32) {
        self.system_times.insert(system_name, time_ms);
    }
    
    pub fn get_total_system_time(&self) -> f32 {
        self.system_times.values().sum()
    }
}

/// Game configuration loaded from files
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct GameConfig {
    pub buildings: HashMap<String, BuildingConfig>,
    pub recipes: HashMap<String, RecipeConfig>,
    pub workers: HashMap<String, WorkerConfig>,
    pub map_generation: MapGenerationConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildingConfig {
    pub name: String,
    pub construction_time: f32,
    pub construction_cost: HashMap<String, u32>,
    pub worker_capacity: u32,
    pub stockpile_capacity: u32,
    pub size: (u32, u32), // width, height in tiles
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecipeConfig {
    pub name: String,
    pub production_time: f32,
    pub inputs: HashMap<String, u32>,
    pub outputs: HashMap<String, u32>,
    pub required_building: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerConfig {
    pub name: String,
    pub movement_speed: f32,
    pub carrying_capacity: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MapGenerationConfig {
    pub width: u32,
    pub height: u32,
    pub forest_density: f32,
    pub stone_density: f32,
    pub water_patches: u32,
    pub seed: u64,
}

impl Default for GameConfig {
    fn default() -> Self {
        let mut buildings = HashMap::new();
        let mut recipes = HashMap::new();
        let mut workers = HashMap::new();
        
        // Default buildings
        buildings.insert("lumberjack".to_string(), BuildingConfig {
            name: "Lumberjack".to_string(),
            construction_time: 30.0,
            construction_cost: [("stone".to_string(), 5)].into(),
            worker_capacity: 2,
            stockpile_capacity: 20,
            size: (2, 2),
        });
        
        buildings.insert("sawmill".to_string(), BuildingConfig {
            name: "Sawmill".to_string(),
            construction_time: 45.0,
            construction_cost: [("stone".to_string(), 8), ("wood".to_string(), 10)].into(),
            worker_capacity: 3,
            stockpile_capacity: 30,
            size: (3, 3),
        });
        
        buildings.insert("farm".to_string(), BuildingConfig {
            name: "Farm".to_string(),
            construction_time: 40.0,
            construction_cost: [("stone".to_string(), 6), ("wood".to_string(), 8)].into(),
            worker_capacity: 2,
            stockpile_capacity: 25,
            size: (4, 4),
        });
        
        buildings.insert("mill".to_string(), BuildingConfig {
            name: "Mill".to_string(),
            construction_time: 50.0,
            construction_cost: [("stone".to_string(), 12), ("wood".to_string(), 15)].into(),
            worker_capacity: 2,
            stockpile_capacity: 20,
            size: (3, 3),
        });
        
        buildings.insert("bakery".to_string(), BuildingConfig {
            name: "Bakery".to_string(),
            construction_time: 35.0,
            construction_cost: [("stone".to_string(), 8), ("wood".to_string(), 6)].into(),
            worker_capacity: 3,
            stockpile_capacity: 15,
            size: (2, 3),
        });
        
        buildings.insert("quarry".to_string(), BuildingConfig {
            name: "Quarry".to_string(),
            construction_time: 60.0,
            construction_cost: [("wood".to_string(), 20)].into(),
            worker_capacity: 4,
            stockpile_capacity: 40,
            size: (3, 3),
        });
        
        // Default recipes
        recipes.insert("harvest_wood".to_string(), RecipeConfig {
            name: "Harvest Wood".to_string(),
            production_time: 10.0,
            inputs: HashMap::new(),
            outputs: [("wood".to_string(), 2)].into(),
            required_building: "lumberjack".to_string(),
        });
        
        recipes.insert("make_planks".to_string(), RecipeConfig {
            name: "Make Planks".to_string(),
            production_time: 8.0,
            inputs: [("wood".to_string(), 1)].into(),
            outputs: [("planks".to_string(), 2)].into(),
            required_building: "sawmill".to_string(),
        });
        
        recipes.insert("grow_grain".to_string(), RecipeConfig {
            name: "Grow Grain".to_string(),
            production_time: 20.0,
            inputs: HashMap::new(),
            outputs: [("grain".to_string(), 3)].into(),
            required_building: "farm".to_string(),
        });
        
        recipes.insert("mill_flour".to_string(), RecipeConfig {
            name: "Mill Flour".to_string(),
            production_time: 6.0,
            inputs: [("grain".to_string(), 2)].into(),
            outputs: [("flour".to_string(), 1)].into(),
            required_building: "mill".to_string(),
        });
        
        recipes.insert("bake_bread".to_string(), RecipeConfig {
            name: "Bake Bread".to_string(),
            production_time: 12.0,
            inputs: [("flour".to_string(), 1)].into(),
            outputs: [("bread".to_string(), 2)].into(),
            required_building: "bakery".to_string(),
        });
        
        recipes.insert("mine_stone".to_string(), RecipeConfig {
            name: "Mine Stone".to_string(),
            production_time: 15.0,
            inputs: HashMap::new(),
            outputs: [("stone".to_string(), 1)].into(),
            required_building: "quarry".to_string(),
        });
        
        // Default workers
        workers.insert("worker".to_string(), WorkerConfig {
            name: "Worker".to_string(),
            movement_speed: 1.0,
            carrying_capacity: 5,
        });
        
        Self {
            buildings,
            recipes,
            workers,
            map_generation: MapGenerationConfig {
                width: 64,
                height: 64,
                forest_density: 0.3,
                stone_density: 0.1,
                water_patches: 3,
                seed: 12345,
            },
        }
    }
}