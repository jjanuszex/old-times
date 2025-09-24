use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Data loader for game configuration files
pub struct DataLoader {
    pub buildings: HashMap<String, crate::resources::BuildingConfig>,
    pub recipes: HashMap<String, crate::resources::RecipeConfig>,
    pub workers: HashMap<String, crate::resources::WorkerConfig>,
}

impl DataLoader {
    pub fn new() -> Self {
        Self {
            buildings: HashMap::new(),
            recipes: HashMap::new(),
            workers: HashMap::new(),
        }
    }

    /// Load all data from a directory
    pub fn load_from_directory<P: AsRef<Path>>(
        data_dir: P,
    ) -> Result<crate::resources::GameConfig> {
        let mut loader = Self::new();

        let data_path = data_dir.as_ref();

        // Load buildings
        let buildings_path = data_path.join("buildings.toml");
        if buildings_path.exists() {
            loader.load_buildings(&buildings_path)?;
        }

        // Load recipes
        let recipes_path = data_path.join("recipes.toml");
        if recipes_path.exists() {
            loader.load_recipes(&recipes_path)?;
        }

        // Load workers
        let workers_path = data_path.join("workers.toml");
        if workers_path.exists() {
            loader.load_workers(&workers_path)?;
        }

        // Load map generation config
        let mapgen_path = data_path.join("mapgen.toml");
        let map_generation = if mapgen_path.exists() {
            loader.load_mapgen_config(&mapgen_path)?
        } else {
            crate::resources::MapGenerationConfig::default()
        };

        Ok(crate::resources::GameConfig {
            buildings: loader.buildings,
            recipes: loader.recipes,
            workers: loader.workers,
            map_generation,
        })
    }

    fn load_buildings<P: AsRef<Path>>(&mut self, path: P) -> Result<()> {
        let content = fs::read_to_string(path)?;
        let buildings: HashMap<String, crate::resources::BuildingConfig> =
            toml::from_str(&content)?;

        for (id, building) in buildings {
            self.validate_building(&building)?;
            self.buildings.insert(id, building);
        }

        log::info!("Loaded {} building definitions", self.buildings.len());
        Ok(())
    }

    fn load_recipes<P: AsRef<Path>>(&mut self, path: P) -> Result<()> {
        let content = fs::read_to_string(path)?;
        let recipes: HashMap<String, crate::resources::RecipeConfig> = toml::from_str(&content)?;

        for (id, recipe) in recipes {
            self.validate_recipe(&recipe)?;
            self.recipes.insert(id, recipe);
        }

        log::info!("Loaded {} recipe definitions", self.recipes.len());
        Ok(())
    }

    fn load_workers<P: AsRef<Path>>(&mut self, path: P) -> Result<()> {
        let content = fs::read_to_string(path)?;
        let workers: HashMap<String, crate::resources::WorkerConfig> = toml::from_str(&content)?;

        for (id, worker) in workers {
            self.validate_worker(&worker)?;
            self.workers.insert(id, worker);
        }

        log::info!("Loaded {} worker definitions", self.workers.len());
        Ok(())
    }

    fn load_mapgen_config<P: AsRef<Path>>(
        &self,
        path: P,
    ) -> Result<crate::resources::MapGenerationConfig> {
        let content = fs::read_to_string(path)?;
        let config: crate::resources::MapGenerationConfig = toml::from_str(&content)?;

        log::info!("Loaded map generation config");
        Ok(config)
    }

    fn validate_building(&self, building: &crate::resources::BuildingConfig) -> Result<()> {
        if building.name.is_empty() {
            return Err(anyhow::anyhow!("Building name cannot be empty"));
        }

        if building.construction_time <= 0.0 {
            return Err(anyhow::anyhow!(
                "Building construction time must be positive"
            ));
        }

        if building.worker_capacity == 0 {
            return Err(anyhow::anyhow!("Building worker capacity must be positive"));
        }

        if building.size.0 == 0 || building.size.1 == 0 {
            return Err(anyhow::anyhow!("Building size must be positive"));
        }

        Ok(())
    }

    fn validate_recipe(&self, recipe: &crate::resources::RecipeConfig) -> Result<()> {
        if recipe.name.is_empty() {
            return Err(anyhow::anyhow!("Recipe name cannot be empty"));
        }

        if recipe.production_time <= 0.0 {
            return Err(anyhow::anyhow!("Recipe production time must be positive"));
        }

        if recipe.outputs.is_empty() {
            return Err(anyhow::anyhow!("Recipe must have at least one output"));
        }

        for (_, amount) in &recipe.inputs {
            if *amount == 0 {
                return Err(anyhow::anyhow!("Recipe input amounts must be positive"));
            }
        }

        for (_, amount) in &recipe.outputs {
            if *amount == 0 {
                return Err(anyhow::anyhow!("Recipe output amounts must be positive"));
            }
        }

        Ok(())
    }

    fn validate_worker(&self, worker: &crate::resources::WorkerConfig) -> Result<()> {
        if worker.name.is_empty() {
            return Err(anyhow::anyhow!("Worker name cannot be empty"));
        }

        if worker.movement_speed <= 0.0 {
            return Err(anyhow::anyhow!("Worker movement speed must be positive"));
        }

        if worker.carrying_capacity == 0 {
            return Err(anyhow::anyhow!("Worker carrying capacity must be positive"));
        }

        Ok(())
    }
}

/// Mod loader for loading game modifications
pub struct ModLoader {
    loaded_mods: Vec<ModInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModInfo {
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: String,
    pub priority: i32,
}

impl ModLoader {
    pub fn new() -> Self {
        Self {
            loaded_mods: Vec::new(),
        }
    }

    /// Load mods from the mods directory
    pub fn load_mods<P: AsRef<Path>>(mods_dir: P) -> Result<crate::resources::GameConfig> {
        let mut base_config = crate::resources::GameConfig::default();
        let mut loader = Self::new();

        let mods_path = mods_dir.as_ref();
        if !mods_path.exists() {
            log::info!("Mods directory does not exist, using default config");
            return Ok(base_config);
        }

        // Find all mod directories
        let mut mod_dirs = Vec::new();
        for entry in fs::read_dir(mods_path)? {
            let entry = entry?;
            if entry.file_type()?.is_dir() {
                mod_dirs.push(entry.path());
            }
        }

        // Load mod info and sort by priority
        let mut mods_with_priority = Vec::new();
        for mod_dir in mod_dirs {
            if let Ok(mod_info) = loader.load_mod_info(&mod_dir) {
                mods_with_priority.push((mod_info, mod_dir));
            }
        }

        // Sort by priority (higher priority loads last, overriding earlier mods)
        mods_with_priority.sort_by_key(|(info, _)| info.priority);

        // Apply mods in priority order
        for (mod_info, mod_dir) in mods_with_priority {
            loader.apply_mod(&mut base_config, &mod_dir, &mod_info)?;
        }

        log::info!("Loaded {} mods", loader.loaded_mods.len());
        Ok(base_config)
    }

    fn load_mod_info<P: AsRef<Path>>(&self, mod_dir: P) -> Result<ModInfo> {
        let mod_info_path = mod_dir.as_ref().join("mod.toml");
        let content = fs::read_to_string(mod_info_path)?;
        let mod_info: ModInfo = toml::from_str(&content)?;
        Ok(mod_info)
    }

    fn apply_mod<P: AsRef<Path>>(
        &mut self,
        config: &mut crate::resources::GameConfig,
        mod_dir: P,
        mod_info: &ModInfo,
    ) -> Result<()> {
        let mod_path = mod_dir.as_ref();

        // Load mod data
        let mod_config = DataLoader::load_from_directory(mod_path)?;

        // Merge buildings (mod overrides base)
        for (id, building) in mod_config.buildings {
            config.buildings.insert(id, building);
        }

        // Merge recipes
        for (id, recipe) in mod_config.recipes {
            config.recipes.insert(id, recipe);
        }

        // Merge workers
        for (id, worker) in mod_config.workers {
            config.workers.insert(id, worker);
        }

        self.loaded_mods.push(mod_info.clone());
        log::info!("Applied mod: {} v{}", mod_info.name, mod_info.version);

        Ok(())
    }

    pub fn get_loaded_mods(&self) -> &[ModInfo] {
        &self.loaded_mods
    }
}

/// Create default data files for a new project
pub fn create_default_data_files<P: AsRef<Path>>(data_dir: P) -> Result<()> {
    let data_path = data_dir.as_ref();
    fs::create_dir_all(data_path)?;

    // Create default buildings.toml
    let default_config = crate::resources::GameConfig::default();

    let buildings_content = toml::to_string_pretty(&default_config.buildings)?;
    fs::write(data_path.join("buildings.toml"), buildings_content)?;

    let recipes_content = toml::to_string_pretty(&default_config.recipes)?;
    fs::write(data_path.join("recipes.toml"), recipes_content)?;

    let workers_content = toml::to_string_pretty(&default_config.workers)?;
    fs::write(data_path.join("workers.toml"), workers_content)?;

    let mapgen_content = toml::to_string_pretty(&default_config.map_generation)?;
    fs::write(data_path.join("mapgen.toml"), mapgen_content)?;

    log::info!("Created default data files in {:?}", data_path);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_create_and_load_default_data() {
        let temp_dir = TempDir::new().unwrap();
        let data_path = temp_dir.path().join("data");

        // Create default files
        create_default_data_files(&data_path).unwrap();

        // Load them back
        let config = DataLoader::load_from_directory(&data_path).unwrap();

        // Should have default buildings
        assert!(config.buildings.contains_key("lumberjack"));
        assert!(config.recipes.contains_key("harvest_wood"));
        assert!(config.workers.contains_key("worker"));
    }

    #[test]
    fn test_mod_loading() {
        let temp_dir = TempDir::new().unwrap();
        let mods_path = temp_dir.path().join("mods");
        let mod_path = mods_path.join("test_mod");

        fs::create_dir_all(&mod_path).unwrap();

        // Create mod info
        let mod_info = ModInfo {
            name: "Test Mod".to_string(),
            version: "1.0.0".to_string(),
            description: "A test mod".to_string(),
            author: "Test Author".to_string(),
            priority: 100,
        };

        let mod_info_content = toml::to_string_pretty(&mod_info).unwrap();
        fs::write(mod_path.join("mod.toml"), mod_info_content).unwrap();

        // Create empty data files
        fs::write(mod_path.join("buildings.toml"), "").unwrap();
        fs::write(mod_path.join("recipes.toml"), "").unwrap();
        fs::write(mod_path.join("workers.toml"), "").unwrap();

        // Load mods
        let config = ModLoader::load_mods(&mods_path).unwrap();

        // Should still have default config since mod files are empty
        assert!(!config.buildings.is_empty());
    }
}
