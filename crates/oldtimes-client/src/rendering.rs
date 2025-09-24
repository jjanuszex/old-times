use bevy::prelude::*;
use oldtimes_core::{assets::*, components::*, resources::*};

#[derive(Resource)]
pub struct GameAssets {
    // Building textures
    pub lumberjack: Handle<Image>,
    pub sawmill: Handle<Image>,
    pub farm: Handle<Image>,
    pub mill: Handle<Image>,
    pub bakery: Handle<Image>,
    pub quarry: Handle<Image>,

    // Terrain textures
    pub grass: Handle<Image>,
    pub water: Handle<Image>,
    pub stone: Handle<Image>,
    pub forest: Handle<Image>,
    pub road: Handle<Image>,

    // Unit textures
    pub worker: Handle<Image>,
}

const TILE_SIZE: f32 = 32.0;

pub fn load_game_assets(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    sprite_metadata: Option<Res<SpriteMetadataResource>>,
) {
    // Load assets using metadata if available, otherwise use hardcoded paths
    let assets = if let Some(metadata) = sprite_metadata {
        load_assets_from_metadata(&asset_server, &metadata)
    } else {
        load_assets_fallback(&asset_server)
    };

    commands.insert_resource(assets);
    log::info!("Game assets loaded");
}

fn load_assets_from_metadata(
    asset_server: &AssetServer,
    metadata: &SpriteMetadataResource,
) -> GameAssets {
    log::info!("Loading assets using sprite metadata");

    GameAssets {
        // Building textures - use metadata or fallback
        lumberjack: load_sprite_with_fallback(
            asset_server,
            metadata,
            "building",
            "lumberjack",
            "sprites/lumberjack.png",
        ),
        sawmill: load_sprite_with_fallback(
            asset_server,
            metadata,
            "building",
            "sawmill",
            "sprites/sawmill.png",
        ),
        farm: load_sprite_with_fallback(
            asset_server,
            metadata,
            "building",
            "farm",
            "sprites/farm.png",
        ),
        mill: load_sprite_with_fallback(
            asset_server,
            metadata,
            "building",
            "mill",
            "sprites/mill.png",
        ),
        bakery: load_sprite_with_fallback(
            asset_server,
            metadata,
            "building",
            "bakery",
            "sprites/bakery.png",
        ),
        quarry: load_sprite_with_fallback(
            asset_server,
            metadata,
            "building",
            "quarry",
            "sprites/quarry.png",
        ),

        // Terrain textures - use metadata or fallback
        grass: load_sprite_with_fallback(
            asset_server,
            metadata,
            "tile",
            "grass",
            "sprites/grass.png",
        ),
        water: load_sprite_with_fallback(
            asset_server,
            metadata,
            "tile",
            "water",
            "sprites/water.png",
        ),
        stone: load_sprite_with_fallback(
            asset_server,
            metadata,
            "tile",
            "stone",
            "sprites/stone.png",
        ),
        forest: load_sprite_with_fallback(
            asset_server,
            metadata,
            "tile",
            "forest",
            "sprites/forest.png",
        ),
        road: load_sprite_with_fallback(asset_server, metadata, "tile", "road", "sprites/road.png"),

        // Unit textures - use metadata or fallback
        worker: load_sprite_with_fallback(
            asset_server,
            metadata,
            "unit",
            "worker",
            "sprites/worker.png",
        ),
    }
}

fn load_assets_fallback(asset_server: &AssetServer) -> GameAssets {
    log::info!("Loading assets using fallback hardcoded paths");

    GameAssets {
        // Building textures
        lumberjack: asset_server.load("sprites/lumberjack.png"),
        sawmill: asset_server.load("sprites/sawmill.png"),
        farm: asset_server.load("sprites/farm.png"),
        mill: asset_server.load("sprites/mill.png"),
        bakery: asset_server.load("sprites/bakery.png"),
        quarry: asset_server.load("sprites/quarry.png"),

        // Terrain textures
        grass: asset_server.load("sprites/grass.png"),
        water: asset_server.load("sprites/water.png"),
        stone: asset_server.load("sprites/stone.png"),
        forest: asset_server.load("sprites/forest.png"),
        road: asset_server.load("sprites/road.png"),

        // Unit textures
        worker: asset_server.load("sprites/worker.png"),
    }
}

fn load_sprite_with_fallback(
    asset_server: &AssetServer,
    metadata: &SpriteMetadataResource,
    sprite_type: &str,
    name: &str,
    fallback_path: &str,
) -> Handle<Image> {
    if let Some(path) = get_sprite_path_from_metadata(metadata, sprite_type, name) {
        log::debug!("Loading {} {} from metadata: {}", sprite_type, name, path);
        asset_server.load(path)
    } else {
        log::debug!(
            "Using fallback path for {} {}: {}",
            sprite_type,
            name,
            fallback_path
        );
        asset_server.load(fallback_path.to_string())
    }
}

pub fn render_map_system(
    mut commands: Commands,
    map: Res<MapData>,
    existing_tiles: Query<Entity, With<TileRenderer>>,
    assets: Option<Res<GameAssets>>,
) {
    // Wait for assets to load
    let Some(assets) = assets else {
        return;
    };

    // Clear existing tile renderers if map changed
    if map.is_changed() {
        for entity in existing_tiles.iter() {
            commands.entity(entity).despawn();
        }

        // Render new map
        for y in 0..map.height {
            for x in 0..map.width {
                if let Some(tile) = map.get_tile(x as i32, y as i32) {
                    let texture = get_tile_texture(&assets, &tile.tile_type);

                    commands.spawn((
                        SpriteBundle {
                            texture: texture.clone(),
                            transform: Transform::from_xyz(
                                x as f32 * TILE_SIZE,
                                y as f32 * TILE_SIZE,
                                0.0,
                            ),
                            ..default()
                        },
                        TileRenderer,
                    ));
                }
            }
        }
    }
}

pub fn render_buildings_system(
    mut commands: Commands,
    buildings: Query<
        (Entity, &Position, &Building),
        (Changed<Building>, Without<BuildingRenderer>),
    >,
    existing_renderers: Query<Entity, With<BuildingRenderer>>,
    assets: Option<Res<GameAssets>>,
) {
    // Wait for assets to load
    let Some(assets) = assets else {
        return;
    };

    // Spawn renderers for new buildings
    for (entity, position, building) in buildings.iter() {
        let texture = get_building_texture(&assets, &building.building_type);
        let alpha = if building.is_constructed { 1.0 } else { 0.5 };

        commands.spawn((
            SpriteBundle {
                texture: texture.clone(),
                sprite: Sprite {
                    color: Color::srgba(1.0, 1.0, 1.0, alpha),
                    ..default()
                },
                transform: Transform::from_xyz(
                    position.x as f32 * TILE_SIZE,
                    position.y as f32 * TILE_SIZE,
                    1.0,
                ),
                ..default()
            },
            BuildingRenderer {
                building_entity: entity,
            },
        ));
    }

    // Update existing building renderers
    let _renderer_query = existing_renderers.iter().collect::<Vec<_>>();
    // In a full implementation, update building appearance based on state
}

pub fn render_workers_system(
    mut commands: Commands,
    workers: Query<(Entity, &Position, &Worker), (Changed<Position>, Without<WorkerRenderer>)>,
    mut existing_renderers: Query<(&mut Transform, &WorkerRenderer)>,
    assets: Option<Res<GameAssets>>,
) {
    // Wait for assets to load
    let Some(assets) = assets else {
        return;
    };

    // Spawn renderers for new workers
    for (entity, position, _worker) in workers.iter() {
        commands.spawn((
            SpriteBundle {
                texture: assets.worker.clone(),
                transform: Transform::from_xyz(
                    position.x as f32 * TILE_SIZE,
                    position.y as f32 * TILE_SIZE,
                    2.0,
                ),
                ..default()
            },
            WorkerRenderer {
                worker_entity: entity,
            },
        ));
    }

    // Update positions of existing worker renderers
    for (mut transform, renderer) in existing_renderers.iter_mut() {
        if let Ok((_, position, _)) = workers.get(renderer.worker_entity) {
            transform.translation.x = position.x as f32 * TILE_SIZE;
            transform.translation.y = position.y as f32 * TILE_SIZE;
        }
    }
}

fn get_tile_texture(assets: &GameAssets, tile_type: &TileType) -> Handle<Image> {
    match tile_type {
        TileType::Grass => assets.grass.clone(),
        TileType::Water => assets.water.clone(),
        TileType::Stone => assets.stone.clone(),
        TileType::Forest => assets.forest.clone(),
        TileType::Road => assets.road.clone(),
    }
}

fn get_building_texture(assets: &GameAssets, building_type: &str) -> Handle<Image> {
    match building_type {
        "lumberjack" => assets.lumberjack.clone(),
        "sawmill" => assets.sawmill.clone(),
        "farm" => assets.farm.clone(),
        "mill" => assets.mill.clone(),
        "bakery" => assets.bakery.clone(),
        "quarry" => assets.quarry.clone(),
        _ => assets.lumberjack.clone(), // Default fallback
    }
}

// Keep the old color functions for fallback
fn get_tile_color(tile_type: &TileType) -> Color {
    match tile_type {
        TileType::Grass => Color::srgb(0.2, 0.8, 0.2),
        TileType::Water => Color::srgb(0.2, 0.2, 0.8),
        TileType::Stone => Color::srgb(0.6, 0.6, 0.6),
        TileType::Forest => Color::srgb(0.1, 0.6, 0.1),
        TileType::Road => Color::srgb(0.8, 0.7, 0.5),
    }
}

fn get_building_color(building_type: &str) -> Color {
    match building_type {
        "lumberjack" => Color::srgb(0.8, 0.4, 0.2),
        "sawmill" => Color::srgb(0.6, 0.3, 0.1),
        "farm" => Color::srgb(0.9, 0.8, 0.3),
        "mill" => Color::srgb(0.7, 0.7, 0.7),
        "bakery" => Color::srgb(0.9, 0.6, 0.4),
        "quarry" => Color::srgb(0.5, 0.5, 0.5),
        _ => Color::srgb(0.8, 0.8, 0.8),
    }
}

// Marker components for renderers
#[derive(Component)]
pub struct TileRenderer;

#[derive(Component)]
pub struct BuildingRenderer {
    pub building_entity: Entity,
}

#[derive(Component)]
pub struct WorkerRenderer {
    pub worker_entity: Entity,
}
