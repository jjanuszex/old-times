use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Position on the tile grid
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Position {
    pub x: i32,
    pub y: i32,
}

impl Position {
    pub fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }

    pub fn distance_to(&self, other: &Position) -> f32 {
        let dx = (self.x - other.x) as f32;
        let dy = (self.y - other.y) as f32;
        (dx * dx + dy * dy).sqrt()
    }
}

/// Marks a tile as blocked for pathfinding
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Blocked;

/// Road tile that provides movement bonus
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Road {
    pub movement_cost: f32,
}

impl Default for Road {
    fn default() -> Self {
        Self { movement_cost: 0.5 }
    }
}

/// Stockpile for storing resources
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Stockpile {
    pub capacity: u32,
    pub items: std::collections::HashMap<String, u32>,
}

impl Stockpile {
    pub fn new(capacity: u32) -> Self {
        Self {
            capacity,
            items: std::collections::HashMap::new(),
        }
    }

    pub fn total_items(&self) -> u32 {
        self.items.values().sum()
    }

    pub fn available_space(&self) -> u32 {
        self.capacity.saturating_sub(self.total_items())
    }

    pub fn can_store(&self, item: &str, amount: u32) -> bool {
        self.available_space() >= amount
    }

    pub fn add_item(&mut self, item: String, amount: u32) -> u32 {
        let available = self.available_space();
        let to_add = amount.min(available);
        *self.items.entry(item).or_insert(0) += to_add;
        to_add
    }

    pub fn remove_item(&mut self, item: &str, amount: u32) -> u32 {
        let current = self.items.get(item).copied().unwrap_or(0);
        let to_remove = amount.min(current);
        if to_remove > 0 {
            let new_amount = current - to_remove;
            if new_amount == 0 {
                self.items.remove(item);
            } else {
                self.items.insert(item.to_string(), new_amount);
            }
        }
        to_remove
    }

    pub fn get_item_count(&self, item: &str) -> u32 {
        self.items.get(item).copied().unwrap_or(0)
    }
}

/// Building component
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Building {
    pub building_type: String,
    pub construction_progress: f32, // 0.0 to 1.0
    pub is_constructed: bool,
    pub worker_capacity: u32,
    pub assigned_workers: u32,
}

impl Building {
    pub fn new(building_type: String, worker_capacity: u32) -> Self {
        Self {
            building_type,
            construction_progress: 0.0,
            is_constructed: false,
            worker_capacity,
            assigned_workers: 0,
        }
    }
}

/// Production facility that converts inputs to outputs
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Producer {
    pub recipe_id: String,
    pub production_progress: f32, // 0.0 to 1.0
    pub is_producing: bool,
    pub production_queue: Vec<String>, // Queue of recipe IDs
}

impl Producer {
    pub fn new(recipe_id: String) -> Self {
        Self {
            recipe_id,
            production_progress: 0.0,
            is_producing: false,
            production_queue: Vec::new(),
        }
    }
}

/// Worker unit
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Worker {
    pub id: Uuid,
    pub worker_type: String,
    pub assigned_building: Option<Entity>,
    pub current_task: WorkerTask,
    pub carrying: Option<(String, u32)>, // (item_type, amount)
    pub movement_speed: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkerTask {
    Idle,
    MovingTo {
        target: Position,
        purpose: TaskPurpose,
    },
    Working {
        building: Entity,
        progress: f32,
    },
    Carrying {
        from: Position,
        to: Position,
        item: String,
        amount: u32,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskPurpose {
    GoToWork,
    PickupResource { item: String, amount: u32 },
    DeliverResource { item: String, amount: u32 },
    Construction,
}

impl Worker {
    pub fn new(worker_type: String) -> Self {
        Self {
            id: Uuid::new_v4(),
            worker_type,
            assigned_building: None,
            current_task: WorkerTask::Idle,
            carrying: None,
            movement_speed: 1.0,
        }
    }
}

/// Pathfinding component for moving entities
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Pathfinding {
    pub path: Vec<Position>,
    pub current_target_index: usize,
    pub recalculate: bool,
}

impl Pathfinding {
    pub fn new(path: Vec<Position>) -> Self {
        Self {
            path,
            current_target_index: 0,
            recalculate: false,
        }
    }

    pub fn current_target(&self) -> Option<Position> {
        self.path.get(self.current_target_index).copied()
    }

    pub fn advance_target(&mut self) -> bool {
        if self.current_target_index + 1 < self.path.len() {
            self.current_target_index += 1;
            true
        } else {
            false
        }
    }

    pub fn is_complete(&self) -> bool {
        self.current_target_index >= self.path.len()
    }
}

/// Tile component for map tiles
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct Tile {
    pub tile_type: TileType,
    pub elevation: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TileType {
    Grass,
    Water,
    Stone,
    Forest,
    Road,
}

impl Tile {
    pub fn movement_cost(&self) -> f32 {
        match self.tile_type {
            TileType::Grass => 1.0,
            TileType::Water => f32::INFINITY, // Impassable
            TileType::Stone => 1.5,
            TileType::Forest => 2.0,
            TileType::Road => 0.5,
        }
    }

    pub fn is_passable(&self) -> bool {
        !matches!(self.tile_type, TileType::Water)
    }
}
