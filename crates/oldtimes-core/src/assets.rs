// Asset metadata loading and management
// This module provides structures and functions to load sprite metadata from TOML files

use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use anyhow::{Result, Context};

/// Sprite metadata loaded from sprites.toml
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpriteMetadata {
    pub tiles: HashMap<String, TileMetadata>,
    pub buildings: HashMap<String, BuildingMetadata>,
    pub units: HashMap<String, UnitMetadata>,
}

/// Metadata for tile sprites
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TileMetadata {
    pub kind: String, // Should be "tile"
    pub size: [u32; 2], // [width, height] in pixels
    pub source: Option<String>, // Path to sprite file
}

/// Metadata for building sprites
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BuildingMetadata {
    pub kind: String, // Should be "building"
    pub size: [u32; 2], // [width, height] in pixels
    pub source: Option<String>, // Path to sprite file
    pub tile_footprint: Option<[u32; 2]>, // [width, height] in tiles
}

/// Metadata for unit sprites with animation support
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnitMetadata {
    pub kind: String, // Should be "unit"
    pub source: Option<String>, // Path to atlas or sprite file
    pub frame_size: Option<[u32; 2]>, // [width, height] of each frame
    pub directions: Option<Vec<String>>, // Direction names
    pub anim_walk_fps: Option<u32>, // Walking animation FPS
    pub anim_walk_len: Option<u32>, // Number of walking frames per direction
    pub layout: Option<String>, // Atlas layout type ("dirs_rows", etc.)
    pub atlas_map: Option<String>, // Path to atlas frame map JSON
}

/// Animation frame information for atlas-based sprites
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AtlasFrameMap {
    pub frames: HashMap<String, FrameData>,
    pub meta: AtlasMetadata,
}

/// Individual frame data in an atlas
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrameData {
    pub x: u32,
    pub y: u32,
    pub w: u32,
    pub h: u32,
}

/// Atlas metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AtlasMetadata {
    pub size: AtlasSize,
    pub format: String,
    pub scale: u32,
}

/// Atlas size information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AtlasSize {
    pub w: u32,
    pub h: u32,
}

/// Resource containing loaded sprite metadata
#[derive(Resource, Default)]
pub struct SpriteMetadataResource {
    pub metadata: Option<SpriteMetadata>,
    pub atlas_maps: HashMap<String, AtlasFrameMap>,
}

impl SpriteMetadataResource {
    /// Load sprite metadata from TOML file
    pub fn load_from_file(path: &str) -> Result<SpriteMetadata> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read sprites metadata from {}", path))?;
        
        let metadata: SpriteMetadata = toml::from_str(&content)
            .with_context(|| format!("Failed to parse sprites metadata from {}", path))?;
        
        log::info!("Loaded sprite metadata: {} tiles, {} buildings, {} units", 
                   metadata.tiles.len(), 
                   metadata.buildings.len(), 
                   metadata.units.len());
        
        Ok(metadata)
    }
    
    /// Load atlas frame map from JSON file
    pub fn load_atlas_map(path: &str) -> Result<AtlasFrameMap> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read atlas map from {}", path))?;
        
        let atlas_map: AtlasFrameMap = serde_json::from_str(&content)
            .with_context(|| format!("Failed to parse atlas map from {}", path))?;
        
        log::debug!("Loaded atlas map with {} frames", atlas_map.frames.len());
        
        Ok(atlas_map)
    }
    
    /// Get tile metadata by name
    pub fn get_tile(&self, name: &str) -> Option<&TileMetadata> {
        self.metadata.as_ref()?.tiles.get(name)
    }
    
    /// Get building metadata by name
    pub fn get_building(&self, name: &str) -> Option<&BuildingMetadata> {
        self.metadata.as_ref()?.buildings.get(name)
    }
    
    /// Get unit metadata by name
    pub fn get_unit(&self, name: &str) -> Option<&UnitMetadata> {
        self.metadata.as_ref()?.units.get(name)
    }
    
    /// Get atlas frame map by path
    pub fn get_atlas_map(&self, path: &str) -> Option<&AtlasFrameMap> {
        self.atlas_maps.get(path)
    }
    
    /// Get frame data for a specific animation frame
    pub fn get_frame_data(&self, atlas_path: &str, frame_name: &str) -> Option<&FrameData> {
        self.get_atlas_map(atlas_path)?.frames.get(frame_name)
    }
}

/// System to load sprite metadata on startup
pub fn load_sprite_metadata_system(
    mut commands: Commands,
) {
    let metadata_resource = load_sprite_metadata_resource();
    commands.insert_resource(metadata_resource);
}

/// System to hot-reload sprite metadata during development
pub fn hot_reload_sprite_metadata_system(
    mut metadata_resource: ResMut<SpriteMetadataResource>,
) {
    // Check if sprites.toml file has been modified
    // For now, we'll just reload on every call in debug mode
    #[cfg(debug_assertions)]
    {
        if let Ok(new_metadata) = SpriteMetadataResource::load_from_file("assets/data/sprites.toml") {
            // Only reload if the content has actually changed
            // This is a simple implementation - in production you'd want to check file modification time
            let mut atlas_maps = HashMap::new();
            
            for (name, unit) in &new_metadata.units {
                if let Some(atlas_map_path) = &unit.atlas_map {
                    match SpriteMetadataResource::load_atlas_map(atlas_map_path) {
                        Ok(atlas_map) => {
                            atlas_maps.insert(atlas_map_path.clone(), atlas_map);
                        }
                        Err(e) => {
                            log::warn!("Failed to load atlas map for unit {}: {}", name, e);
                        }
                    }
                }
            }
            
            metadata_resource.metadata = Some(new_metadata);
            metadata_resource.atlas_maps = atlas_maps;
            log::debug!("Hot-reloaded sprite metadata");
        }
    }
}

/// Load sprite metadata resource with error handling
fn load_sprite_metadata_resource() -> SpriteMetadataResource {
    let mut metadata_resource = SpriteMetadataResource::default();
    
    // Try to load sprites.toml metadata
    match SpriteMetadataResource::load_from_file("assets/data/sprites.toml") {
        Ok(metadata) => {
            // Load any referenced atlas maps
            let mut atlas_maps = HashMap::new();
            
            for (name, unit) in &metadata.units {
                if let Some(atlas_map_path) = &unit.atlas_map {
                    match SpriteMetadataResource::load_atlas_map(atlas_map_path) {
                        Ok(atlas_map) => {
                            atlas_maps.insert(atlas_map_path.clone(), atlas_map);
                            log::debug!("Loaded atlas map for unit {}: {}", name, atlas_map_path);
                        }
                        Err(e) => {
                            log::warn!("Failed to load atlas map for unit {}: {}", name, e);
                        }
                    }
                }
            }
            
            metadata_resource.metadata = Some(metadata);
            metadata_resource.atlas_maps = atlas_maps;
            
            log::info!("Sprite metadata loaded successfully");
        }
        Err(e) => {
            log::warn!("Failed to load sprite metadata: {}. Using fallback asset loading.", e);
        }
    }
    
    metadata_resource
}

/// Helper function to get sprite path from metadata
pub fn get_sprite_path_from_metadata(
    metadata: &SpriteMetadataResource,
    sprite_type: &str,
    name: &str,
) -> Option<String> {
    match sprite_type {
        "tile" => metadata.get_tile(name)?.source.clone(),
        "building" => metadata.get_building(name)?.source.clone(),
        "unit" => metadata.get_unit(name)?.source.clone(),
        _ => None,
    }
}

/// Helper function to get sprite size from metadata
pub fn get_sprite_size_from_metadata(
    metadata: &SpriteMetadataResource,
    sprite_type: &str,
    name: &str,
) -> Option<[u32; 2]> {
    match sprite_type {
        "tile" => Some(metadata.get_tile(name)?.size),
        "building" => Some(metadata.get_building(name)?.size),
        "unit" => metadata.get_unit(name)?.frame_size,
        _ => None,
    }
}

#[cfg(test)]
mod integration_tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn test_metadata_driven_asset_loading() {
        let dir = tempdir().unwrap();
        let sprites_path = dir.path().join("sprites.toml");
        
        // Create test sprites.toml
        let toml_content = r#"
[tiles.grass]
kind = "tile"
size = [32, 32]
source = "test_sprites/grass.png"

[buildings.lumberjack]
kind = "building"
size = [64, 64]
source = "test_sprites/lumberjack.png"
tile_footprint = [2, 2]

[units.worker]
kind = "unit"
source = "test_sprites/worker.png"
frame_size = [32, 32]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "single_sprite"
"#;
        
        fs::write(&sprites_path, toml_content).unwrap();
        
        // Load metadata
        let metadata = SpriteMetadataResource::load_from_file(sprites_path.to_str().unwrap()).unwrap();
        let resource = SpriteMetadataResource {
            metadata: Some(metadata),
            atlas_maps: HashMap::new(),
        };
        
        // Test sprite path retrieval
        assert_eq!(
            get_sprite_path_from_metadata(&resource, "tile", "grass"),
            Some("test_sprites/grass.png".to_string())
        );
        
        assert_eq!(
            get_sprite_path_from_metadata(&resource, "building", "lumberjack"),
            Some("test_sprites/lumberjack.png".to_string())
        );
        
        assert_eq!(
            get_sprite_path_from_metadata(&resource, "unit", "worker"),
            Some("test_sprites/worker.png".to_string())
        );
        
        // Test fallback for non-existent sprites
        assert_eq!(
            get_sprite_path_from_metadata(&resource, "tile", "nonexistent"),
            None
        );
        
        // Test sprite size retrieval
        assert_eq!(
            get_sprite_size_from_metadata(&resource, "tile", "grass"),
            Some([32, 32])
        );
        
        assert_eq!(
            get_sprite_size_from_metadata(&resource, "building", "lumberjack"),
            Some([64, 64])
        );
        
        assert_eq!(
            get_sprite_size_from_metadata(&resource, "unit", "worker"),
            Some([32, 32])
        );
    }

    #[test]
    fn test_backward_compatibility() {
        // Test that the system works when no sprites.toml exists
        let resource = SpriteMetadataResource::default();
        
        // Should return None for all lookups when no metadata is loaded
        assert_eq!(
            get_sprite_path_from_metadata(&resource, "tile", "grass"),
            None
        );
        
        assert_eq!(
            get_sprite_size_from_metadata(&resource, "building", "lumberjack"),
            None
        );
    }

    #[test]
    fn test_atlas_support() {
        let dir = tempdir().unwrap();
        let sprites_path = dir.path().join("sprites.toml");
        let atlas_path = dir.path().join("worker_atlas.json");
        
        // Create test atlas JSON
        let atlas_content = r#"
{
  "frames": {
    "walk_N_0": {"x": 0, "y": 0, "w": 32, "h": 32},
    "walk_N_1": {"x": 32, "y": 0, "w": 32, "h": 32},
    "walk_E_0": {"x": 0, "y": 32, "w": 32, "h": 32},
    "walk_E_1": {"x": 32, "y": 32, "w": 32, "h": 32}
  },
  "meta": {
    "size": {"w": 256, "h": 256},
    "format": "RGBA8888",
    "scale": 1
  }
}
"#;
        
        fs::write(&atlas_path, atlas_content).unwrap();
        
        // Create test sprites.toml with atlas reference
        let toml_content = format!(r#"
[units.worker]
kind = "unit"
source = "test_sprites/worker_atlas.png"
frame_size = [32, 32]
directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
anim_walk_fps = 10
anim_walk_len = 8
layout = "dirs_rows"
atlas_map = "{}"
"#, atlas_path.to_str().unwrap());
        
        fs::write(&sprites_path, toml_content).unwrap();
        
        // Load metadata
        let metadata = SpriteMetadataResource::load_from_file(sprites_path.to_str().unwrap()).unwrap();
        let atlas_map = SpriteMetadataResource::load_atlas_map(atlas_path.to_str().unwrap()).unwrap();
        
        let mut atlas_maps = HashMap::new();
        atlas_maps.insert(atlas_path.to_str().unwrap().to_string(), atlas_map);
        
        let resource = SpriteMetadataResource {
            metadata: Some(metadata),
            atlas_maps,
        };
        
        // Test atlas frame retrieval
        let frame_data = resource.get_frame_data(atlas_path.to_str().unwrap(), "walk_N_0");
        assert!(frame_data.is_some());
        
        let frame = frame_data.unwrap();
        assert_eq!(frame.x, 0);
        assert_eq!(frame.y, 0);
        assert_eq!(frame.w, 32);
        assert_eq!(frame.h, 32);
        
        // Test unit metadata
        let worker = resource.get_unit("worker").unwrap();
        assert_eq!(worker.anim_walk_fps, Some(10));
        assert_eq!(worker.anim_walk_len, Some(8));
        assert_eq!(worker.layout, Some("dirs_rows".to_string()));
    }
}