use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use crate::components::Position;

/// Event for placing a new building
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct PlaceBuildingEvent {
    pub building_type: String,
    pub position: Position,
}

/// Event for assigning a worker to a building
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct AssignWorkerEvent {
    pub worker: Entity,
    pub building: Entity,
}

/// Event for starting production at a building
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct StartProductionEvent {
    pub building: Entity,
    pub recipe_id: String,
}

/// Event for resource transfer between stockpiles
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct TransferResourceEvent {
    pub from: Entity,
    pub to: Entity,
    pub resource: String,
    pub amount: u32,
}

/// Event for worker task completion
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct TaskCompletedEvent {
    pub worker: Entity,
    pub task_type: String,
}

/// Event for building construction completion
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct BuildingConstructedEvent {
    pub building: Entity,
    pub building_type: String,
    pub position: Position,
}

/// Event for production completion
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct ProductionCompletedEvent {
    pub building: Entity,
    pub recipe_id: String,
    pub outputs: std::collections::HashMap<String, u32>,
}

/// Event for pathfinding request
#[derive(Event, Debug, Clone)]
pub struct PathfindingRequestEvent {
    pub entity: Entity,
    pub from: Position,
    pub to: Position,
    pub priority: PathfindingPriority,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PathfindingPriority {
    Low,
    Normal,
    High,
    Critical,
}

/// Event for map changes that invalidate pathfinding cache
#[derive(Event, Debug, Clone)]
pub struct MapChangedEvent {
    pub position: Position,
    pub change_type: MapChangeType,
}

#[derive(Debug, Clone)]
pub enum MapChangeType {
    BuildingPlaced,
    BuildingRemoved,
    RoadBuilt,
    TerrainChanged,
}

/// Event for game state save/load
#[derive(Event, Debug, Clone)]
pub struct SaveGameEvent {
    pub filename: String,
}

#[derive(Event, Debug, Clone)]
pub struct LoadGameEvent {
    pub filename: String,
}

/// Event for replay recording/playback
#[derive(Event, Debug, Clone, Serialize, Deserialize)]
pub struct ReplayEvent {
    pub tick: u64,
    pub event_data: ReplayEventData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ReplayEventData {
    PlaceBuilding(PlaceBuildingEvent),
    AssignWorker(AssignWorkerEvent),
    StartProduction(StartProductionEvent),
    TransferResource(TransferResourceEvent),
}

/// Event for performance profiling
#[derive(Event, Debug, Clone)]
pub struct ProfileEvent {
    pub system_name: String,
    pub duration_ms: f32,
}

/// Event for mod loading
#[derive(Event, Debug, Clone)]
pub struct LoadModEvent {
    pub mod_path: String,
}

/// Event for configuration reload (hot-reload)
#[derive(Event, Debug, Clone)]
pub struct ReloadConfigEvent;