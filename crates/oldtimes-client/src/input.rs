use crate::{BuildingPlacer, CameraController, DebugOverlay};
use bevy::prelude::*;
use oldtimes_core::{components::*, events::*};

pub fn camera_movement_system(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut camera_query: Query<&mut Transform, With<Camera>>,
    controller: Res<CameraController>,
    time: Res<Time>,
) {
    let mut camera_transform = camera_query.single_mut();
    let mut movement = Vec3::ZERO;

    if keyboard.pressed(KeyCode::KeyW) || keyboard.pressed(KeyCode::ArrowUp) {
        movement.y += 1.0;
    }
    if keyboard.pressed(KeyCode::KeyS) || keyboard.pressed(KeyCode::ArrowDown) {
        movement.y -= 1.0;
    }
    if keyboard.pressed(KeyCode::KeyA) || keyboard.pressed(KeyCode::ArrowLeft) {
        movement.x -= 1.0;
    }
    if keyboard.pressed(KeyCode::KeyD) || keyboard.pressed(KeyCode::ArrowRight) {
        movement.x += 1.0;
    }

    if movement != Vec3::ZERO {
        movement = movement.normalize();
        camera_transform.translation += movement * controller.pan_speed * time.delta_seconds();
    }
}

pub fn building_placement_input_system(
    keyboard: Res<ButtonInput<KeyCode>>,
    mouse: Res<ButtonInput<MouseButton>>,
    windows: Query<&Window>,
    camera_query: Query<(&Camera, &GlobalTransform)>,
    mut placer: ResMut<BuildingPlacer>,
    mut placement_events: EventWriter<PlaceBuildingEvent>,
) {
    // Building selection hotkeys
    if keyboard.just_pressed(KeyCode::KeyQ) {
        placer.selected_building = Some("lumberjack".to_string());
        log::info!("Selected: Lumberjack");
    }
    if keyboard.just_pressed(KeyCode::KeyE) {
        placer.selected_building = Some("sawmill".to_string());
        log::info!("Selected: Sawmill");
    }
    if keyboard.just_pressed(KeyCode::KeyR) {
        placer.selected_building = Some("farm".to_string());
        log::info!("Selected: Farm");
    }
    if keyboard.just_pressed(KeyCode::KeyT) {
        placer.selected_building = Some("mill".to_string());
        log::info!("Selected: Mill");
    }
    if keyboard.just_pressed(KeyCode::KeyY) {
        placer.selected_building = Some("bakery".to_string());
        log::info!("Selected: Bakery");
    }
    if keyboard.just_pressed(KeyCode::KeyU) {
        placer.selected_building = Some("quarry".to_string());
        log::info!("Selected: Quarry");
    }

    // Cancel selection
    if keyboard.just_pressed(KeyCode::Escape) {
        placer.selected_building = None;
        placer.preview_position = None;
        log::info!("Building selection cancelled");
    }

    // Get mouse position in world coordinates
    if let Some(building_type) = placer.selected_building.clone() {
        let window = windows.single();
        let (camera, camera_transform) = camera_query.single();

        if let Some(cursor_pos) = window.cursor_position() {
            if let Some(world_pos) = camera.viewport_to_world_2d(camera_transform, cursor_pos) {
                // Convert to tile coordinates
                let tile_x = (world_pos.x / 32.0).floor() as i32;
                let tile_y = (world_pos.y / 32.0).floor() as i32;
                let tile_pos = Position::new(tile_x, tile_y);

                placer.preview_position = Some(tile_pos);

                // Place building on left click
                if mouse.just_pressed(MouseButton::Left) {
                    placement_events.send(PlaceBuildingEvent {
                        building_type: building_type.clone(),
                        position: tile_pos,
                    });

                    log::info!("Placed {} at {:?}", building_type, tile_pos);
                }
            }
        }
    }
}

pub fn ui_input_system(
    keyboard: Res<ButtonInput<KeyCode>>,
    mut debug_overlay: ResMut<DebugOverlay>,
) {
    // Toggle debug overlay
    if keyboard.just_pressed(KeyCode::F1) {
        debug_overlay.enabled = !debug_overlay.enabled;
        log::info!(
            "Debug overlay: {}",
            if debug_overlay.enabled { "ON" } else { "OFF" }
        );
    }

    // Toggle pathfinding visualization
    if keyboard.just_pressed(KeyCode::F2) {
        debug_overlay.show_pathfinding = !debug_overlay.show_pathfinding;
        log::info!(
            "Pathfinding debug: {}",
            if debug_overlay.show_pathfinding {
                "ON"
            } else {
                "OFF"
            }
        );
    }

    // Toggle performance metrics
    if keyboard.just_pressed(KeyCode::F3) {
        debug_overlay.show_performance = !debug_overlay.show_performance;
        log::info!(
            "Performance debug: {}",
            if debug_overlay.show_performance {
                "ON"
            } else {
                "OFF"
            }
        );
    }
}
