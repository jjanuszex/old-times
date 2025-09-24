use bevy::prelude::*;
use oldtimes_core::{
    assets::SpriteMetadataResource,
    components::{Building, Position},
    events::PlaceBuildingEvent,
    resources::{GameConfig, MapData},
};

use super::{camera::CursorWorldPos, map::map_coords};

/// Plugin to handle all building-related player interactions.
pub struct BuildModePlugin;

impl Plugin for BuildModePlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<BuildingPlacer>();

        app.add_systems(
            Update,
            (handle_building_selection, place_building_on_click)
                .in_set(crate::GameSystemSet::Input),
        );
        app.add_systems(Update, ghost_manager.in_set(crate::GameSystemSet::Client));
        app.add_systems(
            Update,
            render_placed_buildings.in_set(crate::GameSystemSet::Render),
        );
    }
}

/// Resource to hold the state of the building placement mode.
#[derive(Resource, Default)]
pub struct BuildingPlacer {
    kind: Option<String>,
}

/// Marker component for the ghost building entity.
#[derive(Component)]
struct Ghost;

/// Handles keyboard input for selecting which building to place.
fn handle_building_selection(mut placer: ResMut<BuildingPlacer>, input: Res<ButtonInput<KeyCode>>) {
    if input.just_pressed(KeyCode::KeyQ) {
        placer.kind = Some("lumberjack".to_string());
    } else if input.just_pressed(KeyCode::KeyE) {
        placer.kind = Some("sawmill".to_string());
    } else if input.just_pressed(KeyCode::KeyR) {
        placer.kind = Some("farm".to_string());
    } else if input.just_pressed(KeyCode::KeyT) {
        placer.kind = Some("mill".to_string());
    } else if input.just_pressed(KeyCode::KeyY) {
        placer.kind = Some("bakery".to_string());
    } else if input.just_pressed(KeyCode::KeyU) {
        placer.kind = Some("quarry".to_string());
    } else if input.just_pressed(KeyCode::Escape) {
        placer.kind = None;
    }
}

/// Manages the ghost building preview.
fn ghost_manager(
    mut commands: Commands,
    placer: Res<BuildingPlacer>,
    cursor_pos: Res<CursorWorldPos>,
    map_data: Res<MapData>,
    game_config: Res<GameConfig>,
    asset_server: Res<AssetServer>,
    metadata: Res<SpriteMetadataResource>,
    mut ghost_query: Query<(Entity, &mut Transform, &mut Sprite), With<Ghost>>,
    building_query: Query<(&Position, &Building)>,
) {
    // If nothing is selected, despawn any existing ghost and return.
    if placer.kind.is_none() {
        if let Ok((entity, _, _)) = ghost_query.get_single_mut() {
            commands.entity(entity).despawn();
        }
        return;
    }

    let building_kind = placer.kind.as_ref().unwrap();

    // Get building footprint from config.
    let footprint = game_config
        .buildings
        .get(building_kind)
        .map_or((1, 1), |b| (b.size.0, b.size.1));

    let grid_pos = map_coords::world_to_grid(cursor_pos.x, cursor_pos.y);
    let world_pos = map_coords::grid_to_world(grid_pos.x, grid_pos.y);

    // Check for placement validity.
    let is_valid = check_placement_validity(
        &map_data,
        grid_pos,
        footprint,
        &building_query,
        &game_config,
    );

    // If a ghost exists, update it. Otherwise, spawn one.
    if let Ok((_, mut transform, mut sprite)) = ghost_query.get_single_mut() {
        transform.translation.x = world_pos.x;
        transform.translation.y = world_pos.y;
        sprite.color = if is_valid {
            Color::srgba(0.0, 1.0, 0.0, 0.5)
        } else {
            Color::srgba(1.0, 0.0, 0.0, 0.5)
        };
    } else {
        if let Some(building_meta) = metadata.get_building(building_kind) {
            if let Some(path) = &building_meta.source {
                commands.spawn((
                    SpriteBundle {
                        texture: asset_server.load(path),
                        transform: Transform::from_xyz(world_pos.x, world_pos.y, 1.0),
                        sprite: Sprite {
                            color: Color::srgba(1.0, 1.0, 1.0, 0.5),
                            ..default()
                        },
                        ..default()
                    },
                    Ghost,
                ));
            }
        }
    }
}

/// Handles placing a building on left mouse click.
fn place_building_on_click(
    placer: Res<BuildingPlacer>,
    cursor_pos: Res<CursorWorldPos>,
    mouse: Res<ButtonInput<MouseButton>>,
    map_data: Res<MapData>,
    game_config: Res<GameConfig>,
    mut event_writer: EventWriter<PlaceBuildingEvent>,
    building_query: Query<(&Position, &Building)>,
) {
    if mouse.just_pressed(MouseButton::Left) {
        if let Some(kind) = &placer.kind {
            let grid_pos = map_coords::world_to_grid(cursor_pos.x, cursor_pos.y);
            let footprint = game_config
                .buildings
                .get(kind)
                .map_or((1, 1), |b| (b.size.0, b.size.1));

            if check_placement_validity(
                &map_data,
                grid_pos,
                footprint,
                &building_query,
                &game_config,
            ) {
                event_writer.send(PlaceBuildingEvent {
                    building_type: kind.clone(),
                    position: Position {
                        x: grid_pos.x,
                        y: grid_pos.y,
                    },
                });
                log::info!("Sent PlaceBuildingEvent for {} at {:?}", kind, grid_pos);
            }
        }
    }
}

/// Renders sprites for newly created buildings.
fn render_placed_buildings(
    mut commands: Commands,
    query: Query<(Entity, &Building, &Position), Added<Building>>,
    metadata: Res<SpriteMetadataResource>,
    asset_server: Res<AssetServer>,
) {
    for (_, building, position) in query.iter() {
        if let Some(building_meta) = metadata.get_building(&building.building_type) {
            if let Some(path) = &building_meta.source {
                let pos = map_coords::grid_to_world(position.x, position.y);
                commands.spawn(SpriteBundle {
                    texture: asset_server.load(path),
                    transform: Transform::from_xyz(pos.x, pos.y, 1.0),
                    ..default()
                });
                log::info!(
                    "Rendered building sprite for {} at {:?}",
                    building.building_type,
                    pos
                );
            }
        }
    }
}

/// Helper function to check if a building can be placed.
fn check_placement_validity(
    map_data: &MapData,
    grid_pos: IVec2,
    footprint: (u32, u32),
    building_query: &Query<(&Position, &Building)>,
    game_config: &GameConfig,
) -> bool {
    // 1. Check map bounds and tile types
    for y in 0..footprint.1 {
        for x in 0..footprint.0 {
            let check_pos = grid_pos + IVec2::new(x as i32, y as i32);
            if !map_data.is_valid_position(check_pos.x, check_pos.y) {
                return false; // Out of bounds
            }
            if let Some(tile) = map_data.get_tile(check_pos.x, check_pos.y) {
                if !matches!(
                    tile.tile_type,
                    oldtimes_core::components::TileType::Grass
                        | oldtimes_core::components::TileType::Road
                ) {
                    return false; // Can only build on grass or road
                }
            }
        }
    }

    // 2. Check for collision with other buildings
    let new_building_rect = Rect::from_corners(
        grid_pos.as_vec2(),
        (grid_pos + IVec2::new(footprint.0 as i32, footprint.1 as i32)).as_vec2(),
    );

    for (p, b) in building_query.iter() {
        let b_footprint = game_config
            .buildings
            .get(&b.building_type)
            .map_or((1, 1), |bc| (bc.size.0, bc.size.1));
        let existing_building_rect = Rect::from_corners(
            IVec2::new(p.x, p.y).as_vec2(),
            (IVec2::new(p.x, p.y) + IVec2::new(b_footprint.0 as i32, b_footprint.1 as i32))
                .as_vec2(),
        );

        // Simple AABB collision check
        if new_building_rect.min.x < existing_building_rect.max.x
            && new_building_rect.max.x > existing_building_rect.min.x
            && new_building_rect.min.y < existing_building_rect.max.y
            && new_building_rect.max.y > existing_building_rect.min.y
        {
            return false; // Collision detected
        }
    }

    true
}
