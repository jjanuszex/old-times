use crate::{
    components::{Tile, TileType},
    resources::MapData,
};
use noise::{NoiseFn, Perlin};

/// Generate a demo map with varied terrain
pub fn generate_demo_map(map: &mut MapData) {
    let perlin = Perlin::new(12345);
    
    for y in 0..map.height {
        for x in 0..map.width {
            let nx = x as f64 / map.width as f64;
            let ny = y as f64 / map.height as f64;
            
            // Generate base terrain using Perlin noise
            let elevation = perlin.get([nx * 4.0, ny * 4.0]) as f32;
            let forest_noise = perlin.get([nx * 8.0, ny * 8.0]) as f32;
            let stone_noise = perlin.get([nx * 6.0, ny * 6.0]) as f32;
            
            let tile_type = if elevation < -0.3 {
                TileType::Water
            } else if stone_noise > 0.4 {
                TileType::Stone
            } else if forest_noise > 0.2 {
                TileType::Forest
            } else {
                TileType::Grass
            };
            
            let tile = Tile {
                tile_type,
                elevation: ((elevation + 1.0) * 127.5) as u8,
            };
            
            map.set_tile(x as i32, y as i32, tile);
        }
    }
    
    // Add some roads for demo
    add_demo_roads(map);
    
    log::info!("Generated demo map {}x{}", map.width, map.height);
}

fn add_demo_roads(map: &mut MapData) {
    // Add a simple road network
    
    // Horizontal road
    for x in 10..50 {
        if let Some(tile) = map.get_tile(x, 20) {
            if matches!(tile.tile_type, TileType::Grass) {
                map.set_tile(x, 20, Tile {
                    tile_type: TileType::Road,
                    elevation: tile.elevation,
                });
            }
        }
    }
    
    // Vertical road
    for y in 10..50 {
        if let Some(tile) = map.get_tile(30, y) {
            if matches!(tile.tile_type, TileType::Grass) {
                map.set_tile(30, y, Tile {
                    tile_type: TileType::Road,
                    elevation: tile.elevation,
                });
            }
        }
    }
    
    log::debug!("Added demo roads to map");
}

/// Generate map from configuration
pub fn generate_map_from_config(config: &crate::resources::MapGenerationConfig) -> MapData {
    let mut map = MapData::new(config.width, config.height);
    
    let perlin = Perlin::new(config.seed as u32);
    
    for y in 0..config.height {
        for x in 0..config.width {
            let nx = x as f64 / config.width as f64;
            let ny = y as f64 / config.height as f64;
            
            let elevation = perlin.get([nx * 4.0, ny * 4.0]) as f32;
            let forest_noise = perlin.get([nx * 8.0, ny * 8.0]) as f32;
            let stone_noise = perlin.get([nx * 6.0, ny * 6.0]) as f32;
            
            let tile_type = if elevation < -0.3 {
                TileType::Water
            } else if stone_noise > (1.0 - config.stone_density * 2.0) {
                TileType::Stone
            } else if forest_noise > (1.0 - config.forest_density * 2.0) {
                TileType::Forest
            } else {
                TileType::Grass
            };
            
            let tile = Tile {
                tile_type,
                elevation: ((elevation + 1.0) * 127.5) as u8,
            };
            
            map.set_tile(x as i32, y as i32, tile);
        }
    }
    
    log::info!("Generated map {}x{} with seed {}", config.width, config.height, config.seed);
    map
}

/// Check if a position is suitable for building placement
pub fn is_suitable_for_building(map: &MapData, x: i32, y: i32, size: (u32, u32)) -> bool {
    for dy in 0..size.1 as i32 {
        for dx in 0..size.0 as i32 {
            if let Some(tile) = map.get_tile(x + dx, y + dy) {
                match tile.tile_type {
                    TileType::Water => return false,
                    TileType::Forest => return false, // Would need clearing
                    _ => {}
                }
            } else {
                return false; // Out of bounds
            }
        }
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_demo_map_generation() {
        let mut map = MapData::new(32, 32);
        generate_demo_map(&mut map);
        
        // Check that we have varied terrain
        let mut grass_count = 0;
        let mut water_count = 0;
        let mut forest_count = 0;
        let mut stone_count = 0;
        let mut road_count = 0;
        
        for y in 0..map.height {
            for x in 0..map.width {
                if let Some(tile) = map.get_tile(x as i32, y as i32) {
                    match tile.tile_type {
                        TileType::Grass => grass_count += 1,
                        TileType::Water => water_count += 1,
                        TileType::Forest => forest_count += 1,
                        TileType::Stone => stone_count += 1,
                        TileType::Road => road_count += 1,
                    }
                }
            }
        }
        
        // Should have some variety
        assert!(grass_count > 0);
        assert!(road_count > 0);
        
        // Total should equal map size
        let total = grass_count + water_count + forest_count + stone_count + road_count;
        assert_eq!(total, (map.width * map.height) as usize);
    }
    
    #[test]
    fn test_building_suitability() {
        let mut map = MapData::new(10, 10);
        
        // Fill with grass
        for y in 0..10 {
            for x in 0..10 {
                map.set_tile(x, y, Tile {
                    tile_type: TileType::Grass,
                    elevation: 100,
                });
            }
        }
        
        // Should be suitable
        assert!(is_suitable_for_building(&map, 2, 2, (2, 2)));
        
        // Add water
        map.set_tile(3, 3, Tile {
            tile_type: TileType::Water,
            elevation: 50,
        });
        
        // Should not be suitable now
        assert!(!is_suitable_for_building(&map, 2, 2, (2, 2)));
    }
    
    #[test]
    fn test_config_based_generation() {
        let config = crate::resources::MapGenerationConfig {
            width: 16,
            height: 16,
            forest_density: 0.5,
            stone_density: 0.2,
            water_patches: 2,
            seed: 54321,
        };
        
        let map = generate_map_from_config(&config);
        assert_eq!(map.width, 16);
        assert_eq!(map.height, 16);
    }
}