use bevy::prelude::*;
use oldtimes_core::{assets::SpriteMetadataResource, components::TileType, resources::MapData};

/// Plugin for map generation, rendering, and coordinate systems.
pub struct MapPlugin;

impl Plugin for MapPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, spawn_map_system.in_set(crate::StartupSet::Map));
    }
}

/// A marker component for entities that represent a single map tile.
/// Holds the tile's grid coordinates.
#[derive(Component)]
#[allow(dead_code)] // This is a marker entity, the field may be used later.
pub struct TileEntity(pub IVec2);

/// Spawns sprite entities for every tile in the `MapData` resource.
fn spawn_map_system(
    mut commands: Commands,
    map_data: Res<MapData>,
    metadata: Res<SpriteMetadataResource>,
    asset_server: Res<AssetServer>,
) {
    if map_data.width == 0 || map_data.height == 0 {
        log::error!(
            "MapData is empty, cannot spawn map. Make sure it's initialized before this system."
        );
        return;
    }

    log::info!("Spawning map tiles...");

    for (ty, row) in map_data.tiles.iter().enumerate() {
        for (tx, tile) in row.iter().enumerate() {
            let tile_name = match tile.tile_type {
                TileType::Grass => "grass",
                TileType::Water => "water",
                TileType::Stone => "stone",
                TileType::Forest => "forest",
                TileType::Road => "road",
            };

            if let Some(tile_meta) = metadata.get_tile(tile_name) {
                if let Some(path) = &tile_meta.source {
                    let pos = map_coords::grid_to_world(tx as i32, ty as i32);
                    commands.spawn((
                        SpriteBundle {
                            texture: asset_server.load(path),
                            transform: Transform::from_xyz(pos.x, pos.y, 0.0),
                            ..default()
                        },
                        TileEntity(IVec2::new(tx as i32, ty as i32)),
                    ));
                }
            }
        }
    }
    log::info!(
        "Finished spawning {} map tiles.",
        map_data.width * map_data.height
    );
}

/// A module for handling isometric coordinate conversions.
pub mod map_coords {
    use bevy::prelude::*;

    // Tile dimensions in pixels.
    pub const TILE_W: f32 = 64.0;
    pub const TILE_H: f32 = 32.0;
    pub const TILE_H_HALF: f32 = TILE_H / 2.0;
    pub const TILE_W_HALF: f32 = TILE_W / 2.0;

    /// Converts grid coordinates (tile x, tile y) to world coordinates (pixel x, pixel y).
    /// This is the standard "diamond" isometric projection.
    pub fn grid_to_world(tx: i32, ty: i32) -> Vec2 {
        let world_x = (tx as f32 - ty as f32) * TILE_W_HALF;
        // We multiply by -1.0 because in Bevy's world space, the +Y axis points up,
        // but in classic isometric projections, the +Y grid axis points "down and to the right".
        // This inversion aligns the visual output with the standard isometric look.
        let world_y = (tx as f32 + ty as f32) * TILE_H_HALF * -1.0;
        Vec2::new(world_x, world_y)
    }

    /// Converts world coordinates (pixel x, pixel y) to the nearest grid coordinate (tile x, tile y).
    /// This is the inverse of the `grid_to_world` function.
    pub fn world_to_grid(world_x: f32, world_y: f32) -> IVec2 {
        // We must first "unflip" the world's Y coordinate to bring it back into the
        // isometric projection's coordinate space before applying the inverse formula.
        let iso_y = world_y * -1.0;

        let tx = ((iso_y / TILE_H_HALF) + (world_x / TILE_W_HALF)) / 2.0;
        let ty = ((iso_y / TILE_H_HALF) - (world_x / TILE_W_HALF)) / 2.0;

        IVec2::new(tx.round() as i32, ty.round() as i32)
    }
}
