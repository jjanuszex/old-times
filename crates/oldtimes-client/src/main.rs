use bevy::prelude::*;
use oldtimes_core::{
    assets as core_assets, components::*, events::*, map as core_map, resources::*,
    systems as core_systems,
};

mod plugins;

fn main() {
    env_logger::init();

    let mut app = App::new();

    // Core plugins
    app.add_plugins((
        DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Old Times".to_string(),
                resolution: (1024.0, 768.0).into(),
                ..default()
            }),
            ..default()
        }),
        bevy::diagnostic::FrameTimeDiagnosticsPlugin,
        bevy::diagnostic::EntityCountDiagnosticsPlugin,
    ));

    // Game plugins
    app.add_plugins((
        CorePlugin,
        plugins::MapPlugin,
        plugins::CameraPlugin,
        plugins::UiPlugin,
        plugins::BuildModePlugin,
        plugins::EconomyPlugin,
        plugins::DebugPlugin,
    ));

    // Configure the main game loop system sets
    app.configure_sets(
        Update,
        (
            GameSystemSet::Input,
            GameSystemSet::Client,
            GameSystemSet::Simulation,
            GameSystemSet::Render,
        )
            .chain(),
    );

    // Add the core simulation systems to their set
    app.add_systems(
        Update,
        (
            core_systems::advance_tick_system,
            core_systems::building_placement_system,
            core_systems::worker_assignment_system,
            core_systems::start_production_system,
            core_systems::construction_system,
            core_systems::production_system,
            core_systems::worker_ai_system,
            core_systems::pathfinding_system,
            core_systems::movement_system,
            core_systems::transport_system,
            core_systems::resource_distribution_system,
            core_systems::transport_completion_system,
            core_systems::invalidate_pathfinding_cache_system,
            core_systems::profile_systems_system,
            core_systems::spawn_workers_system,
            core_assets::hot_reload_sprite_metadata_system,
        )
            .in_set(GameSystemSet::Simulation),
    );

    app.run();
}

#[derive(SystemSet, Debug, Hash, PartialEq, Eq, Clone)]
pub enum StartupSet {
    Core,
    Map,
}

#[derive(SystemSet, Debug, Hash, PartialEq, Eq, Clone)]
pub enum GameSystemSet {
    /// Handles player input
    Input,
    /// Handles client-side logic before the main simulation
    Client,
    /// Runs the core game simulation
    Simulation,
    /// Runs rendering systems that depend on the simulation state
    Render,
}

/// Core plugin that sets up resources, events, and essential systems.
pub struct CorePlugin;

impl Plugin for CorePlugin {
    fn build(&self, app: &mut App) {
        // Add core simulation resources
        app.init_resource::<GameTick>()
            .init_resource::<MapData>()
            .init_resource::<PathfindingCache>()
            .init_resource::<PerformanceMetrics>()
            .init_resource::<GameConfig>();

        // Add client-specific resources that are widely used
        app.init_resource::<plugins::economy::GameSpeed>();

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

        app.configure_sets(Startup, (StartupSet::Core, StartupSet::Map).chain());

        // Add essential startup systems
        app.add_systems(
            Startup,
            (core_assets::load_sprite_metadata_system, initialize_game)
                .chain()
                .in_set(StartupSet::Core),
        );
    }
}

// TODO: Move this to a more appropriate plugin later (e.g., a "game state" plugin)
fn initialize_game(mut commands: Commands, mut map: ResMut<MapData>) {
    // Generate demo map
    core_map::generate_demo_map(&mut map);

    // Spawn some initial entities for demo
    commands.spawn((
        Position::new(15, 15),
        Building::new("lumberjack".to_string(), 2),
        Stockpile::new(20),
        Blocked,
    ));

    commands.spawn((
        Position::new(25, 25),
        Building::new("sawmill".to_string(), 3),
        Stockpile::new(30),
        Producer::new("make_planks".to_string()),
        Blocked,
    ));

    log::info!("Game initialized with demo content");
}
