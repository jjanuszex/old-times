use bevy::{
    input::mouse::{MouseScrollUnit, MouseWheel},
    prelude::*,
    window::PrimaryWindow,
};

/// A marker component for the main game camera.
#[derive(Component)]
pub struct MainCamera;

/// Resource to store the world position of the cursor, updated each frame.
#[derive(Resource, Default, Deref, DerefMut)]
pub struct CursorWorldPos(pub Vec2);

/// A plugin for managing the game's camera, including setup, controls, and coordinate conversion.
pub struct CameraPlugin;

impl Plugin for CameraPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<CursorWorldPos>();
        app.add_systems(Startup, setup_camera);
        app.add_systems(
            Update,
            (
                camera_pan_system,
                camera_zoom_system,
                update_cursor_world_pos_system,
            )
                .in_set(crate::GameSystemSet::Client),
        );
    }
}

/// Creates the main 2D camera entity.
fn setup_camera(mut commands: Commands) {
    let mut camera_bundle = Camera2dBundle::default();

    // Set a default zoom level. This is a likely fix for the "black screen" issue,
    // as the default scale might be inappropriate.
    camera_bundle.projection.scale = 1.0;

    commands.spawn((camera_bundle, MainCamera));
    log::info!("Main camera spawned.");
}

/// Handles camera movement via keyboard input (WASD / Arrow Keys).
fn camera_pan_system(
    mut query: Query<(&mut Transform, &OrthographicProjection), With<MainCamera>>,
    input: Res<ButtonInput<KeyCode>>,
    time: Res<Time>,
) {
    const PAN_SPEED: f32 = 400.0;
    let (mut transform, projection) = query.single_mut();

    let mut direction = Vec3::ZERO;
    if input.pressed(KeyCode::KeyW) || input.pressed(KeyCode::ArrowUp) {
        direction.y += 1.0;
    }
    if input.pressed(KeyCode::KeyS) || input.pressed(KeyCode::ArrowDown) {
        direction.y -= 1.0;
    }
    if input.pressed(KeyCode::KeyA) || input.pressed(KeyCode::ArrowLeft) {
        direction.x -= 1.0;
    }
    if input.pressed(KeyCode::KeyD) || input.pressed(KeyCode::ArrowRight) {
        direction.x += 1.0;
    }

    if direction.length_squared() > 0.0 {
        direction = direction.normalize();
        // Scale pan speed by the current zoom level to maintain consistent perceived speed.
        transform.translation += direction * PAN_SPEED * time.delta_seconds() * projection.scale;
    }
}

/// Handles camera zoom via mouse wheel input.
fn camera_zoom_system(
    mut query: Query<&mut OrthographicProjection, With<MainCamera>>,
    mut scroll_evr: EventReader<MouseWheel>,
) {
    let mut projection = query.single_mut();

    for ev in scroll_evr.read() {
        let scroll_amount = match ev.unit {
            MouseScrollUnit::Line => ev.y,
            MouseScrollUnit::Pixel => ev.y * 0.001, // Heuristic for pixel scrolling
        };

        // Decrease scale to zoom in, increase to zoom out.
        let new_scale = projection.scale - scroll_amount * 0.15 * projection.scale;

        // Clamp the zoom level to prevent zooming too far in or out.
        projection.scale = new_scale.clamp(0.5, 2.5);
    }
}

/// Updates the `CursorWorldPos` resource with the cursor's current world position.
fn update_cursor_world_pos_system(
    mut cursor_pos: ResMut<CursorWorldPos>,
    q_window: Query<&Window, With<PrimaryWindow>>,
    q_camera: Query<(&Camera, &GlobalTransform), With<MainCamera>>,
) {
    if let (Ok((camera, camera_transform)), Ok(window)) = (q_camera.get_single(), q_window.get_single()) {
        // Check if the cursor is inside the window and get its screen position.
        if let Some(screen_pos) = window.cursor_position() {
            // Use the camera to convert the screen position to a world position.
            if let Some(world_position) = camera.viewport_to_world_2d(camera_transform, screen_pos) {
                cursor_pos.0 = world_position;
            }
        }
    }
}
