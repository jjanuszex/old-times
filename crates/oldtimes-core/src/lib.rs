// Old Times - Core simulation engine
// MIT License

#![allow(
    unused_variables,
    unused_imports,
    unused_mut,
    clippy::new_without_default,
    clippy::for_kv_map,
    clippy::crate_in_macro_def,
    clippy::cast_abs_to_unsigned
)]

pub mod assets;
pub mod components;
pub mod data;
pub mod economy;
pub mod events;
pub mod map;
pub mod pathfinding;
pub mod resources;
pub mod save;
pub mod simulation;
pub mod systems;

pub use simulation::SimulationApp;

// Re-export commonly used types
pub use bevy::prelude::*;
pub use components::*;
pub use events::*;
pub use resources::*;
