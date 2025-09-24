#![allow(dead_code, clippy::type_complexity, clippy::useless_format)]

use bevy::prelude::*;
use oldtimes_core::{components::*, events::*, resources::*};

mod input;
mod rendering;
mod ui;

use input::*;
use rendering::*;
use ui::*;

fn main() {
    env_logger::init();

    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Old Times".to_string(),
                resolution: (1024.0, 768.0).into(),
                ..default()
            }),
            ..default()
        }))
        .add_plugins(GamePlugin)
        .run();
}

pub struct GamePlugin;

impl Plugin for GamePlugin {
    fn build(&self, app: &mut App) {
        // Add core simulation resources
        app.init_resource::<GameTick>()
            .init_resource::<MapData>()
            .init_resource::<PathfindingCache>()
            .init_resource::<PerformanceMetrics>()
            .init_resource::<GameConfig>();

        // Add client-specific resources
        app.init_resource::<GameSpeed>()
            .init_resource::<CameraController>()
            .init_resource::<BuildingPlacer>()
            .init_resource::<DebugOverlay>();

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

        // Add systems
        app.add_systems(
            Startup,
            (
                oldtimes_core::assets::load_sprite_metadata_system,
                setup_camera,
                setup_ui,
                initialize_game,
                rendering::load_game_assets,
            )
                .chain(),
        )
        // Add input systems
        .add_systems(
            Update,
            (
                camera_movement_system,
                building_placement_input_system,
                ui_input_system,
            ),
        )
        // Add core simulation systems
        .add_systems(
            Update,
            (
                oldtimes_core::systems::advance_tick_system,
                oldtimes_core::systems::building_placement_system,
                oldtimes_core::systems::worker_assignment_system,
                oldtimes_core::systems::start_production_system,
                oldtimes_core::systems::construction_system,
                oldtimes_core::systems::production_system,
                oldtimes_core::systems::worker_ai_system,
                oldtimes_core::systems::pathfinding_system,
            ),
        )
        // Add more simulation systems
        .add_systems(
            Update,
            (
                oldtimes_core::systems::movement_system,
                oldtimes_core::systems::transport_system,
                oldtimes_core::systems::resource_distribution_system,
                oldtimes_core::systems::transport_completion_system,
                oldtimes_core::systems::invalidate_pathfinding_cache_system,
                oldtimes_core::systems::profile_systems_system,
                oldtimes_core::systems::spawn_workers_system,
            ),
        )
        // Add rendering and UI systems
        .add_systems(
            Update,
            (
                render_map_system,
                render_buildings_system,
                render_workers_system,
                update_ui_system,
                update_debug_overlay_system,
                game_speed_control_system,
                oldtimes_core::assets::hot_reload_sprite_metadata_system,
            ),
        );
    }
}

fn setup_camera(mut commands: Commands) {
    commands.spawn(Camera2dBundle::default());
}

fn initialize_game(mut commands: Commands, mut map: ResMut<MapData>) {
    // Generate demo map
    oldtimes_core::map::generate_demo_map(&mut map);

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

#[derive(Resource, Default)]
pub struct GameSpeed {
    pub paused: bool,
    pub speed_multiplier: f32,
}

impl GameSpeed {
    pub fn new() -> Self {
        Self {
            paused: false,
            speed_multiplier: 1.0,
        }
    }
}

#[derive(Resource, Default)]
pub struct CameraController {
    pub pan_speed: f32,
    pub zoom_speed: f32,
}

impl CameraController {
    pub fn new() -> Self {
        Self {
            pan_speed: 200.0,
            zoom_speed: 0.1,
        }
    }
}

#[derive(Resource, Default)]
pub struct BuildingPlacer {
    pub selected_building: Option<String>,
    pub preview_position: Option<Position>,
}

#[derive(Resource, Default)]
pub struct DebugOverlay {
    pub enabled: bool,
    pub show_pathfinding: bool,
    pub show_performance: bool,
}

fn game_speed_control_system(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut game_speed: ResMut<GameSpeed>,
    mut tick: ResMut<GameTick>,
) {
    if keyboard.just_pressed(KeyCode::Space) {
        game_speed.paused = !game_speed.paused;
        log::info!(
            "Game {}",
            if game_speed.paused {
                "paused"
            } else {
                "resumed"
            }
        );
    }

    if keyboard.just_pressed(KeyCode::Digit1) {
        game_speed.speed_multiplier = 1.0;
        tick.target_tps = 20;
        log::info!("Speed: 1x");
    }

    if keyboard.just_pressed(KeyCode::Digit2) {
        game_speed.speed_multiplier = 2.0;
        tick.target_tps = 40;
        log::info!("Speed: 2x");
    }

    if keyboard.just_pressed(KeyCode::Digit4) {
        game_speed.speed_multiplier = 4.0;
        tick.target_tps = 80;
        log::info!("Speed: 4x");
    }
}
