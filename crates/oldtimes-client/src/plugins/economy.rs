use bevy::prelude::*;
use oldtimes_core::{
    components::Stockpile,
    resources::GameTick,
};
use std::collections::HashMap;

/// Plugin for managing client-side economy state and game speed.
pub struct EconomyPlugin;

impl Plugin for EconomyPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<GlobalResources>()
            .init_resource::<GameSpeed>();

        app.add_systems(
            Update,
            game_speed_control_system.in_set(crate::GameSystemSet::Input),
        );
        app.add_systems(
            Update,
            update_global_resources_system.in_set(crate::GameSystemSet::Render),
        );
    }
}

/// A global resource store for the player's assets.
#[derive(Resource, Debug, Default)]
pub struct GlobalResources {
    pub wood: i32,
    pub planks: i32,
    pub food: i32,
    pub stone: i32,
}

/// Client-side resource to control game speed and pause state.
#[derive(Resource, Debug)]
pub struct GameSpeed {
    pub paused: bool,
    pub multiplier: f32,
}

impl Default for GameSpeed {
    fn default() -> Self {
        Self {
            paused: false,
            multiplier: 1.0,
        }
    }
}

/// System to control the game's speed via keyboard shortcuts.
fn game_speed_control_system(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut game_speed: ResMut<GameSpeed>,
    mut tick: ResMut<GameTick>,
) {
    if keyboard.just_pressed(KeyCode::Space) {
        game_speed.paused = !game_speed.paused;
        log::info!("Game {}", if game_speed.paused { "paused" } else { "resumed" });
    }

    if keyboard.just_pressed(KeyCode::Digit1) {
        game_speed.multiplier = 1.0;
        tick.target_tps = 20;
        log::info!("Speed set to 1x");
    }
    if keyboard.just_pressed(KeyCode::Digit2) {
        game_speed.multiplier = 2.0;
        tick.target_tps = 40;
        log::info!("Speed set to 2x");
    }
    if keyboard.just_pressed(KeyCode::Digit4) {
        game_speed.multiplier = 4.0;
        tick.target_tps = 80;
        log::info!("Speed set to 4x");
    }
}

/// Aggregates all resources from building `Stockpile`s into the `GlobalResources` resource.
fn update_global_resources_system(
    mut global_resources: ResMut<GlobalResources>,
    stockpile_query: Query<&Stockpile>,
) {
    let mut totals: HashMap<String, u32> = HashMap::new();

    // Sum up all resources from all stockpiles
    for stockpile in stockpile_query.iter() {
        for (item, amount) in &stockpile.items {
            *totals.entry(item.clone()).or_insert(0) += *amount;
        }
    }

    // Update the global resource store
    global_resources.wood = totals.get("wood").copied().unwrap_or(0) as i32;
    global_resources.planks = totals.get("planks").copied().unwrap_or(0) as i32;
    global_resources.food = totals.get("food").copied().unwrap_or(0) as i32;
    global_resources.stone = totals.get("stone").copied().unwrap_or(0) as i32;
}
