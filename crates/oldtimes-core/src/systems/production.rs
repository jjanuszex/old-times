use crate::{
    components::{Building, Producer, Stockpile},
    events::{ProductionCompletedEvent, StartProductionEvent},
    resources::{GameConfig, GameTick},
};
use bevy::prelude::*;

/// System that handles production in buildings
pub fn production_system(
    mut query: Query<(Entity, &Building, &mut Producer, &mut Stockpile)>,
    config: Res<GameConfig>,
    tick: Res<GameTick>,
    mut completed_events: EventWriter<ProductionCompletedEvent>,
) {
    let delta_time = tick.delta_time();

    for (entity, building, mut producer, mut stockpile) in query.iter_mut() {
        if !building.is_constructed || building.assigned_workers == 0 {
            producer.is_producing = false;
            continue;
        }

        // Get the current recipe
        let recipe = match config.recipes.get(&producer.recipe_id) {
            Some(recipe) => recipe,
            None => {
                log::warn!("Unknown recipe: {}", producer.recipe_id);
                continue;
            }
        };

        // Check if we have required inputs
        if !has_required_inputs(&stockpile, recipe) {
            producer.is_producing = false;
            producer.production_progress = 0.0;
            continue;
        }

        // Check if we have space for outputs
        if !has_space_for_outputs(&stockpile, recipe) {
            producer.is_producing = false;
            continue;
        }

        // Start or continue production
        if !producer.is_producing {
            producer.is_producing = true;
            producer.production_progress = 0.0;
        }

        // Advance production
        let production_speed = building.assigned_workers as f32 / building.worker_capacity as f32;
        producer.production_progress += (delta_time / recipe.production_time) * production_speed;

        // Complete production
        if producer.production_progress >= 1.0 {
            complete_production(
                entity,
                &mut producer,
                &mut stockpile,
                recipe,
                &mut completed_events,
            );
        }
    }
}

/// System that handles production start events
pub fn start_production_system(
    mut events: EventReader<StartProductionEvent>,
    mut query: Query<&mut Producer>,
) {
    for event in events.read() {
        if let Ok(mut producer) = query.get_mut(event.building) {
            producer.recipe_id = event.recipe_id.clone();
            producer.production_progress = 0.0;
            producer.is_producing = false; // Will be started by production_system
        }
    }
}

fn has_required_inputs(stockpile: &Stockpile, recipe: &crate::resources::RecipeConfig) -> bool {
    for (item, required_amount) in &recipe.inputs {
        if stockpile.get_item_count(item) < *required_amount {
            return false;
        }
    }
    true
}

fn has_space_for_outputs(stockpile: &Stockpile, recipe: &crate::resources::RecipeConfig) -> bool {
    let total_outputs: u32 = recipe.outputs.values().sum();
    stockpile.available_space() >= total_outputs
}

fn complete_production(
    entity: Entity,
    producer: &mut Producer,
    stockpile: &mut Stockpile,
    recipe: &crate::resources::RecipeConfig,
    completed_events: &mut EventWriter<ProductionCompletedEvent>,
) {
    // Consume inputs
    for (item, amount) in &recipe.inputs {
        stockpile.remove_item(item, *amount);
    }

    // Produce outputs
    let mut outputs = std::collections::HashMap::new();
    for (item, amount) in &recipe.outputs {
        let produced = stockpile.add_item(item.clone(), *amount);
        outputs.insert(item.clone(), produced);
    }

    // Reset production
    producer.production_progress = 0.0;
    producer.is_producing = false;

    // Send completion event
    completed_events.send(ProductionCompletedEvent {
        building: entity,
        recipe_id: recipe.name.clone(),
        outputs,
    });

    log::debug!(
        "Production completed: {} at building {:?}",
        recipe.name,
        entity
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::resources::RecipeConfig;
    use std::collections::HashMap;

    #[test]
    fn test_has_required_inputs() {
        let mut stockpile = Stockpile::new(100);
        stockpile.add_item("wood".to_string(), 5);
        stockpile.add_item("stone".to_string(), 3);

        let recipe = RecipeConfig {
            name: "Test Recipe".to_string(),
            production_time: 10.0,
            inputs: [("wood".to_string(), 2), ("stone".to_string(), 1)].into(),
            outputs: HashMap::new(),
            required_building: "test".to_string(),
        };

        assert!(has_required_inputs(&stockpile, &recipe));

        let recipe_insufficient = RecipeConfig {
            name: "Test Recipe".to_string(),
            production_time: 10.0,
            inputs: [("wood".to_string(), 10)].into(),
            outputs: HashMap::new(),
            required_building: "test".to_string(),
        };

        assert!(!has_required_inputs(&stockpile, &recipe_insufficient));
    }

    #[test]
    fn test_has_space_for_outputs() {
        let mut stockpile = Stockpile::new(10);
        stockpile.add_item("existing".to_string(), 8);

        let recipe = RecipeConfig {
            name: "Test Recipe".to_string(),
            production_time: 10.0,
            inputs: HashMap::new(),
            outputs: [("planks".to_string(), 2)].into(),
            required_building: "test".to_string(),
        };

        assert!(has_space_for_outputs(&stockpile, &recipe));

        let recipe_too_much = RecipeConfig {
            name: "Test Recipe".to_string(),
            production_time: 10.0,
            inputs: HashMap::new(),
            outputs: [("planks".to_string(), 5)].into(),
            required_building: "test".to_string(),
        };

        assert!(!has_space_for_outputs(&stockpile, &recipe_too_much));
    }
}
