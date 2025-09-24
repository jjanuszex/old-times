// Old Times - Core simulation engine
// MIT License

pub mod components;
pub mod systems;
pub mod resources;
pub mod events;
pub mod data;
pub mod pathfinding;
pub mod economy;
pub mod map;
pub mod simulation;
pub mod save;
pub mod assets;

pub use simulation::SimulationApp;

// Re-export commonly used types
pub use bevy::prelude::*;
pub use components::*;
pub use resources::*;
pub use events::*;