use bevy::{
    diagnostic::{DiagnosticsStore, EntityCountDiagnosticsPlugin, FrameTimeDiagnosticsPlugin},
    prelude::*,
};

use super::{camera::CursorWorldPos, map::map_coords};

/// A plugin for debug overlays and visualizations.
pub struct DebugPlugin;

impl Plugin for DebugPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<DebugOverlay>()
            .add_systems(Startup, setup_debug_ui)
            .add_systems(
                Update,
                (
                    debug_toggle_system,
                    update_debug_overlay_system.after(debug_toggle_system),
                    tile_highlighter_system.after(debug_toggle_system),
                )
                    .in_set(crate::GameSystemSet::Client),
            );
    }
}

/// Resource to hold the state of debug features.
#[derive(Resource, Default)]
pub struct DebugOverlay {
    pub show_info: bool,
    pub highlight_tile: bool,
}

#[derive(Component)]
struct DebugText;

#[derive(Component)]
struct TileHighlighter;

/// Toggles debug features on/off with F1 and F2 keys.
fn debug_toggle_system(mut debug_overlay: ResMut<DebugOverlay>, input: Res<ButtonInput<KeyCode>>) {
    if input.just_pressed(KeyCode::F1) {
        debug_overlay.show_info = !debug_overlay.show_info;
    }
    if input.just_pressed(KeyCode::F2) {
        debug_overlay.highlight_tile = !debug_overlay.highlight_tile;
    }
}

/// Creates the UI node for the debug text.
fn setup_debug_ui(mut commands: Commands) {
    commands.spawn((
        TextBundle::from_section(
            "",
            TextStyle {
                font_size: 16.0,
                color: Color::WHITE,
                ..default()
            },
        )
        .with_style(Style {
            position_type: PositionType::Absolute,
            bottom: Val::Px(5.0),
            left: Val::Px(5.0),
            ..default()
        }),
        DebugText,
    ));
}

/// Updates the debug text overlay with diagnostics and cursor info.
fn update_debug_overlay_system(
    mut query: Query<(&mut Text, &mut Visibility), With<DebugText>>,
    diagnostics: Res<DiagnosticsStore>,
    cursor_pos: Res<CursorWorldPos>,
    debug_overlay: Res<DebugOverlay>,
) {
    let (mut text, mut visibility) = query.single_mut();

    if debug_overlay.show_info {
        *visibility = Visibility::Visible;

        let grid_pos = map_coords::world_to_grid(cursor_pos.x, cursor_pos.y);

        let mut fps = 0.0;
        if let Some(fps_diagnostic) = diagnostics.get(&FrameTimeDiagnosticsPlugin::FPS) {
            if let Some(fps_smoothed) = fps_diagnostic.smoothed() {
                fps = fps_smoothed;
            }
        }

        let mut entity_count = 0;
        if let Some(entity_diagnostic) =
            diagnostics.get(&EntityCountDiagnosticsPlugin::ENTITY_COUNT)
        {
            if let Some(entity_count_value) = entity_diagnostic.value() {
                entity_count = entity_count_value as u32;
            }
        }

        text.sections[0].value = format!(
            "FPS: {:.1}\nEntities: {}\nWorld Pos: {:.1}, {:.1}\nGrid Pos: {}, {}",
            fps, entity_count, cursor_pos.x, cursor_pos.y, grid_pos.x, grid_pos.y
        );
    } else {
        *visibility = Visibility::Hidden;
    }
}

/// Manages the tile highlighter sprite.
fn tile_highlighter_system(
    mut commands: Commands,
    debug_overlay: Res<DebugOverlay>,
    cursor_pos: Res<CursorWorldPos>,
    asset_server: Res<AssetServer>,
    mut highlighter_query: Query<(Entity, &mut Transform, &mut Visibility), With<TileHighlighter>>,
) {
    if debug_overlay.highlight_tile {
        let grid_pos = map_coords::world_to_grid(cursor_pos.x, cursor_pos.y);
        let world_pos = map_coords::grid_to_world(grid_pos.x, grid_pos.y);

        if let Ok((_entity, mut transform, mut visibility)) = highlighter_query.get_single_mut() {
            *visibility = Visibility::Visible;
            transform.translation.x = world_pos.x;
            transform.translation.y = world_pos.y;
        } else {
            // Spawn a highlighter if one doesn't exist.
            // Using a simple sprite for now. A 9-patch or a mesh would be better.
            commands.spawn((
                SpriteBundle {
                    // TODO: Create a proper asset for this.
                    texture: asset_server.load("sprites/grass.png"), // Placeholder
                    sprite: Sprite {
                        color: Color::srgba(1.0, 1.0, 0.0, 0.3),
                        custom_size: Some(Vec2::new(map_coords::TILE_W, map_coords::TILE_H)),
                        ..default()
                    },
                    transform: Transform::from_xyz(world_pos.x, world_pos.y, 10.0),
                    ..default()
                },
                TileHighlighter,
            ));
        }
    } else {
        if let Ok((_entity, _, mut visibility)) = highlighter_query.get_single_mut() {
            *visibility = Visibility::Hidden;
        }
    }
}
