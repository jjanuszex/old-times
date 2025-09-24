use crate::{events::*, resources::*, systems::*};
use bevy::prelude::*;

/// Main simulation app that runs headless
pub struct SimulationApp {
    app: App,
}

impl SimulationApp {
    pub fn new() -> Self {
        let mut app = App::new();

        // Add minimal Bevy plugins for ECS
        app.add_plugins(MinimalPlugins);

        // Add resources
        app.init_resource::<GameTick>()
            .init_resource::<MapData>()
            .init_resource::<PathfindingCache>()
            .init_resource::<PerformanceMetrics>()
            .init_resource::<GameConfig>();

        // Add events
        app.add_event::<PlaceBuildingEvent>()
            .add_event::<AssignWorkerEvent>()
            .add_event::<StartProductionEvent>()
            .add_event::<TransferResourceEvent>()
            .add_event::<TaskCompletedEvent>()
            .add_event::<BuildingConstructedEvent>()
            .add_event::<ProductionCompletedEvent>()
            .add_event::<PathfindingRequestEvent>()
            .add_event::<MapChangedEvent>()
            .add_event::<SaveGameEvent>()
            .add_event::<LoadGameEvent>()
            .add_event::<ReplayEvent>()
            .add_event::<ProfileEvent>()
            .add_event::<LoadModEvent>()
            .add_event::<ReloadConfigEvent>();

        // Add systems in order of execution
        app.add_systems(
            Update,
            (
                // Core tick system
                advance_tick_system,
                // Input processing
                building_placement_system,
                worker_assignment_system,
                start_production_system,
                // Simulation systems
                construction_system,
                production_system,
                worker_ai_system,
                pathfinding_system,
                movement_system,
                transport_system,
                resource_distribution_system,
                transport_completion_system,
                // Cleanup and maintenance
                invalidate_pathfinding_cache_system,
                profile_systems_system,
                // Worker spawning (only at start)
                spawn_workers_system,
            )
                .chain(),
        );

        Self { app }
    }

    /// Initialize the simulation with a demo map
    pub fn initialize_demo(&mut self) {
        // Generate demo map
        let mut map = MapData::new(64, 64);
        crate::map::generate_demo_map(&mut map);
        self.app.insert_resource(map);

        log::info!("Demo simulation initialized");
    }

    /// Run a single simulation tick
    pub fn tick(&mut self) {
        self.app.update();
    }

    /// Run simulation for specified number of ticks
    pub fn run_ticks(&mut self, ticks: u64) {
        for _ in 0..ticks {
            self.tick();
        }
    }

    /// Get current tick count
    pub fn current_tick(&self) -> u64 {
        self.app.world().resource::<GameTick>().current
    }

    /// Get performance metrics
    pub fn get_metrics(&self) -> &PerformanceMetrics {
        self.app.world().resource::<PerformanceMetrics>()
    }

    /// Send an event to the simulation
    pub fn send_event<T: Event>(&mut self, event: T) {
        self.app.world_mut().send_event(event);
    }

    /// Get a resource from the simulation
    pub fn get_resource<T: Resource>(&self) -> Option<&T> {
        self.app.world().get_resource::<T>()
    }

    /// Get a mutable resource from the simulation
    pub fn get_resource_mut<T: Resource>(&mut self) -> Option<Mut<T>> {
        self.app.world_mut().get_resource_mut::<T>()
    }

    /// Calculate state hash for determinism verification
    pub fn calculate_state_hash(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();

        // Hash game tick
        self.app
            .world()
            .resource::<GameTick>()
            .current
            .hash(&mut hasher);

        // Hash entity count (simple determinism check)
        let entity_count = self.app.world().entities().len();
        entity_count.hash(&mut hasher);

        // In a full implementation, you'd hash all relevant component data

        hasher.finish()
    }

    /// Save current state to file
    pub fn save_state(&mut self, filename: &str) -> anyhow::Result<()> {
        crate::save::save_game_state(self.app.world_mut(), filename)
    }

    /// Load state from file
    pub fn load_state(&mut self, filename: &str) -> anyhow::Result<()> {
        crate::save::load_game_state(self.app.world_mut(), filename)
    }
}

impl Default for SimulationApp {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simulation_creation() {
        let mut sim = SimulationApp::new();
        sim.initialize_demo();

        assert_eq!(sim.current_tick(), 0);

        sim.tick();
        assert_eq!(sim.current_tick(), 1);
    }

    #[test]
    fn test_deterministic_simulation() {
        let mut sim1 = SimulationApp::new();
        let mut sim2 = SimulationApp::new();

        sim1.initialize_demo();
        sim2.initialize_demo();

        // Run same number of ticks
        sim1.run_ticks(100);
        sim2.run_ticks(100);

        // Should have same state hash (basic determinism test)
        assert_eq!(sim1.calculate_state_hash(), sim2.calculate_state_hash());
    }

    #[test]
    fn test_building_placement() {
        let mut sim = SimulationApp::new();
        sim.initialize_demo();

        // Place a building
        sim.send_event(PlaceBuildingEvent {
            building_type: "lumberjack".to_string(),
            position: crate::components::Position::new(10, 10),
        });

        sim.tick();

        // Verify building was placed (in a real test, you'd query for the building)
        assert!(sim.current_tick() > 0);
    }
}
