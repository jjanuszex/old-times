use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::fs;
use anyhow::Result;
use ron::ser::{to_string_pretty, PrettyConfig};

/// Serializable game state for save/load
#[derive(Serialize, Deserialize)]
pub struct GameState {
    pub version: String,
    pub tick: u64,
    pub map_data: crate::resources::MapData,
    pub entities: Vec<SerializableEntity>,
}

#[derive(Serialize, Deserialize)]
pub struct SerializableEntity {
    pub id: u32,
    pub components: EntityComponents,
}

#[derive(Serialize, Deserialize)]
pub struct EntityComponents {
    pub position: Option<crate::components::Position>,
    pub building: Option<crate::components::Building>,
    pub stockpile: Option<crate::components::Stockpile>,
    pub worker: Option<crate::components::Worker>,
    pub producer: Option<crate::components::Producer>,
    pub tile: Option<crate::components::Tile>,
    pub blocked: bool,
    pub road: Option<crate::components::Road>,
}

/// Save game state to file
pub fn save_game_state(world: &mut World, filename: &str) -> Result<()> {
    let tick = world.resource::<crate::resources::GameTick>().current;
    let map_data = world.resource::<crate::resources::MapData>().clone();
    
    let mut entities = Vec::new();
    
    // Query all entities and their components
    let mut query = world.query::<(
        Entity,
        Option<&crate::components::Position>,
        Option<&crate::components::Building>,
        Option<&crate::components::Stockpile>,
        Option<&crate::components::Worker>,
        Option<&crate::components::Producer>,
        Option<&crate::components::Tile>,
        Option<&crate::components::Blocked>,
        Option<&crate::components::Road>,
    )>();
    
    for (entity, position, building, stockpile, worker, producer, tile, blocked, road) in query.iter(world) {
        let serializable_entity = SerializableEntity {
            id: entity.index(),
            components: EntityComponents {
                position: position.copied(),
                building: building.cloned(),
                stockpile: stockpile.cloned(),
                worker: worker.cloned(),
                producer: producer.cloned(),
                tile: tile.cloned(),
                blocked: blocked.is_some(),
                road: road.cloned(),
            },
        };
        entities.push(serializable_entity);
    }
    
    let game_state = GameState {
        version: env!("CARGO_PKG_VERSION").to_string(),
        tick,
        map_data,
        entities,
    };
    
    let serialized = to_string_pretty(&game_state, PrettyConfig::default())?;
    fs::write(filename, serialized)?;
    
    log::info!("Game state saved to {}", filename);
    Ok(())
}

/// Load game state from file
pub fn load_game_state(world: &mut World, filename: &str) -> Result<()> {
    let content = fs::read_to_string(filename)?;
    let game_state: GameState = ron::from_str(&content)?;
    
    // Clear existing entities
    world.clear_entities();
    
    // Restore tick
    if let Some(mut tick) = world.get_resource_mut::<crate::resources::GameTick>() {
        tick.current = game_state.tick;
    }
    
    // Restore map data
    world.insert_resource(game_state.map_data);
    
    // Restore entities
    for serializable_entity in game_state.entities {
        let mut entity_commands = world.spawn_empty();
        let entity = entity_commands.id();
        
        let components = serializable_entity.components;
        
        if let Some(position) = components.position {
            entity_commands.insert(position);
        }
        
        if let Some(building) = components.building {
            entity_commands.insert(building);
        }
        
        if let Some(stockpile) = components.stockpile {
            entity_commands.insert(stockpile);
        }
        
        if let Some(worker) = components.worker {
            entity_commands.insert(worker);
        }
        
        if let Some(producer) = components.producer {
            entity_commands.insert(producer);
        }
        
        if let Some(tile) = components.tile {
            entity_commands.insert(tile);
        }
        
        if components.blocked {
            entity_commands.insert(crate::components::Blocked);
        }
        
        if let Some(road) = components.road {
            entity_commands.insert(road);
        }
    }
    
    log::info!("Game state loaded from {}", filename);
    Ok(())
}

/// Replay system for deterministic testing
#[derive(Serialize, Deserialize)]
pub struct ReplayData {
    pub version: String,
    pub initial_seed: u64,
    pub events: Vec<crate::events::ReplayEvent>,
}

/// Record replay data
pub fn start_recording() -> ReplayRecorder {
    ReplayRecorder::new()
}

pub struct ReplayRecorder {
    events: Vec<crate::events::ReplayEvent>,
    initial_seed: u64,
}

impl ReplayRecorder {
    pub fn new() -> Self {
        Self {
            events: Vec::new(),
            initial_seed: 12345, // Default seed
        }
    }
    
    pub fn record_event(&mut self, tick: u64, event_data: crate::events::ReplayEventData) {
        self.events.push(crate::events::ReplayEvent { tick, event_data });
    }
    
    pub fn save_replay(&self, filename: &str) -> Result<()> {
        let replay_data = ReplayData {
            version: env!("CARGO_PKG_VERSION").to_string(),
            initial_seed: self.initial_seed,
            events: self.events.clone(),
        };
        
        let serialized = to_string_pretty(&replay_data, PrettyConfig::default())?;
        fs::write(filename, serialized)?;
        
        log::info!("Replay saved to {}", filename);
        Ok(())
    }
}

/// Load and verify replay
pub fn load_and_verify_replay(filename: &str) -> Result<bool> {
    let content = fs::read_to_string(filename)?;
    let replay_data: ReplayData = ron::from_str(&content)?;
    
    // Create two identical simulations
    let mut sim1 = crate::simulation::SimulationApp::new();
    let mut sim2 = crate::simulation::SimulationApp::new();
    
    sim1.initialize_demo();
    sim2.initialize_demo();
    
    // Apply replay events to first simulation
    for event in &replay_data.events {
        // Fast-forward to event tick
        while sim1.current_tick() < event.tick {
            sim1.tick();
        }
        
        // Apply event
        match &event.event_data {
            crate::events::ReplayEventData::PlaceBuilding(e) => {
                sim1.send_event(e.clone());
            },
            crate::events::ReplayEventData::AssignWorker(e) => {
                sim1.send_event(e.clone());
            },
            crate::events::ReplayEventData::StartProduction(e) => {
                sim1.send_event(e.clone());
            },
            crate::events::ReplayEventData::TransferResource(e) => {
                sim1.send_event(e.clone());
            },
        }
    }
    
    // Run second simulation without events to the same tick
    let final_tick = replay_data.events.last().map(|e| e.tick).unwrap_or(0);
    sim2.run_ticks(final_tick);
    
    // Compare final states
    let hash1 = sim1.calculate_state_hash();
    let hash2 = sim2.calculate_state_hash();
    
    let is_deterministic = hash1 == hash2;
    
    if is_deterministic {
        log::info!("Replay verification passed - simulation is deterministic");
    } else {
        log::error!("Replay verification failed - simulation is not deterministic");
        log::error!("Hash1: {}, Hash2: {}", hash1, hash2);
    }
    
    Ok(is_deterministic)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    
    #[test]
    fn test_save_load_game_state() {
        let mut world = World::new();
        world.init_resource::<crate::resources::GameTick>();
        world.init_resource::<crate::resources::MapData>();
        
        // Add some test entities
        world.spawn((
            crate::components::Position::new(5, 5),
            crate::components::Building::new("test".to_string(), 2),
        ));
        
        // Save to temporary file
        let temp_file = NamedTempFile::new().unwrap();
        let filename = temp_file.path().to_str().unwrap();
        
        save_game_state(&world, filename).unwrap();
        
        // Load into new world
        let mut new_world = World::new();
        new_world.init_resource::<crate::resources::GameTick>();
        new_world.init_resource::<crate::resources::MapData>();
        
        load_game_state(&mut new_world, filename).unwrap();
        
        // Verify entities were loaded
        let entity_count = new_world.query::<&crate::components::Position>().iter(&new_world).count();
        assert_eq!(entity_count, 1);
    }
    
    #[test]
    fn test_replay_recording() {
        let mut recorder = ReplayRecorder::new();
        
        recorder.record_event(10, crate::events::ReplayEventData::PlaceBuilding(
            crate::events::PlaceBuildingEvent {
                building_type: "test".to_string(),
                position: crate::components::Position::new(1, 1),
            }
        ));
        
        assert_eq!(recorder.events.len(), 1);
        
        // Save to temporary file
        let temp_file = NamedTempFile::new().unwrap();
        let filename = temp_file.path().to_str().unwrap();
        
        recorder.save_replay(filename).unwrap();
        
        // File should exist and contain data
        let content = std::fs::read_to_string(filename).unwrap();
        assert!(!content.is_empty());
    }
}