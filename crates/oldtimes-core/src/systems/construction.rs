use crate::{
    components::{Blocked, Building, Position, Stockpile},
    events::{BuildingConstructedEvent, PlaceBuildingEvent},
    resources::{GameConfig, GameTick},
};
use bevy::prelude::*;

/// System that handles building placement
pub fn building_placement_system(
    mut commands: Commands,
    mut events: EventReader<PlaceBuildingEvent>,
    config: Res<GameConfig>,
    existing_buildings: Query<&Position, With<Building>>,
) {
    for event in events.read() {
        let building_config = match config.buildings.get(&event.building_type) {
            Some(config) => config,
            None => {
                log::warn!("Unknown building type: {}", event.building_type);
                continue;
            }
        };

        // Check if position is available
        if is_position_occupied(&existing_buildings, event.position, building_config.size) {
            log::warn!(
                "Cannot place building at {:?} - position occupied",
                event.position
            );
            continue;
        }

        // Create building entity
        let building_entity = commands
            .spawn((
                event.position,
                Building::new(event.building_type.clone(), building_config.worker_capacity),
                Stockpile::new(building_config.stockpile_capacity),
                Blocked, // Buildings block movement
            ))
            .id();

        log::info!("Placed {} at {:?}", building_config.name, event.position);
    }
}

/// System that handles building construction progress
pub fn construction_system(
    mut query: Query<(Entity, &mut Building, &Position)>,
    config: Res<GameConfig>,
    tick: Res<GameTick>,
    mut completed_events: EventWriter<BuildingConstructedEvent>,
) {
    let delta_time = tick.delta_time();

    for (entity, mut building, position) in query.iter_mut() {
        if building.is_constructed {
            continue;
        }

        let building_config = match config.buildings.get(&building.building_type) {
            Some(config) => config,
            None => continue,
        };

        // For now, construction is automatic without requiring workers/materials
        // In a full implementation, you'd check for assigned workers and materials
        building.construction_progress += delta_time / building_config.construction_time;

        if building.construction_progress >= 1.0 {
            building.construction_progress = 1.0;
            building.is_constructed = true;

            completed_events.send(BuildingConstructedEvent {
                building: entity,
                building_type: building.building_type.clone(),
                position: *position,
            });

            log::info!(
                "Construction completed: {} at {:?}",
                building_config.name,
                position
            );
        }
    }
}

fn is_position_occupied(
    existing_buildings: &Query<&Position, With<Building>>,
    position: Position,
    size: (u32, u32),
) -> bool {
    // Check if any existing building overlaps with the proposed building area
    for existing_pos in existing_buildings.iter() {
        // Simple overlap check - in a real game you'd check the actual building sizes
        if existing_pos.x == position.x && existing_pos.y == position.y {
            return true;
        }

        // Check if within building footprint
        let dx = (existing_pos.x - position.x).abs() as u32;
        let dy = (existing_pos.y - position.y).abs() as u32;

        if dx < size.0 && dy < size.1 {
            return true;
        }
    }

    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_position_occupation() {
        let mut world = World::new();

        // Add a building at (5, 5)
        world.spawn((Position::new(5, 5), Building::new("test".to_string(), 1)));

        let mut query = world.query_filtered::<&Position, With<Building>>();

        // Test that we have one building at the expected position
        let positions: Vec<Position> = query.iter(&world).cloned().collect();
        assert_eq!(positions.len(), 1);
        assert_eq!(positions[0], Position::new(5, 5));
    }
}
