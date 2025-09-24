#[allow(unused_imports)]
use crate::resources::{GameConfig, RecipeConfig};
use anyhow::Result;
use std::collections::{HashMap, HashSet};

/// Economic system for analyzing production chains and resource flows
pub struct EconomyAnalyzer {
    config: GameConfig,
}

impl EconomyAnalyzer {
    pub fn new(config: GameConfig) -> Self {
        Self { config }
    }

    /// Analyze the production graph for cycles and dependencies
    pub fn analyze_production_graph(&self) -> ProductionGraphAnalysis {
        let mut analysis = ProductionGraphAnalysis::new();

        // Build dependency graph
        let mut dependencies: HashMap<String, HashSet<String>> = HashMap::new();
        let mut producers: HashMap<String, HashSet<String>> = HashMap::new();

        for (recipe_id, recipe) in &self.config.recipes {
            // Track what each recipe produces
            for output in recipe.outputs.keys() {
                producers
                    .entry(output.clone())
                    .or_default()
                    .insert(recipe_id.clone());
            }

            // Track what each recipe depends on
            for input in recipe.inputs.keys() {
                dependencies
                    .entry(recipe_id.clone())
                    .or_default()
                    .insert(input.clone());
            }
        }

        analysis.dependencies = dependencies;
        analysis.producers = producers;

        // Detect cycles
        analysis.cycles = self.detect_cycles(&analysis.dependencies);

        // Find resource sources (recipes with no inputs)
        analysis.resource_sources = self
            .config
            .recipes
            .iter()
            .filter(|(_, recipe)| recipe.inputs.is_empty())
            .map(|(id, _)| id.clone())
            .collect();

        // Find resource sinks (items that are only consumed, never produced)
        let all_inputs: HashSet<String> = self
            .config
            .recipes
            .values()
            .flat_map(|recipe| recipe.inputs.keys())
            .cloned()
            .collect();

        let all_outputs: HashSet<String> = self
            .config
            .recipes
            .values()
            .flat_map(|recipe| recipe.outputs.keys())
            .cloned()
            .collect();

        analysis.resource_sinks = all_inputs.difference(&all_outputs).cloned().collect();

        analysis
    }

    /// Calculate resource flow rates for a given production setup
    pub fn calculate_flow_rates(
        &self,
        production_rates: &HashMap<String, f32>,
    ) -> HashMap<String, f32> {
        let mut flow_rates: HashMap<String, f32> = HashMap::new();

        for (recipe_id, rate) in production_rates {
            if let Some(recipe) = self.config.recipes.get(recipe_id) {
                // Add outputs
                for (output, amount) in &recipe.outputs {
                    *flow_rates.entry(output.clone()).or_insert(0.0) += rate * (*amount as f32);
                }

                // Subtract inputs
                for (input, amount) in &recipe.inputs {
                    *flow_rates.entry(input.clone()).or_insert(0.0) -= rate * (*amount as f32);
                }
            }
        }

        flow_rates
    }

    /// Find optimal production ratios for a target output
    pub fn find_production_ratios(
        &self,
        target_item: &str,
        target_rate: f32,
    ) -> Result<HashMap<String, f32>> {
        let mut ratios: HashMap<String, f32> = HashMap::new();
        let mut visited: HashSet<String> = HashSet::new();

        self.calculate_ratios_recursive(target_item, target_rate, &mut ratios, &mut visited)?;

        Ok(ratios)
    }

    fn calculate_ratios_recursive(
        &self,
        item: &str,
        required_rate: f32,
        ratios: &mut HashMap<String, f32>,
        visited: &mut HashSet<String>,
    ) -> Result<()> {
        if visited.contains(item) {
            return Err(anyhow::anyhow!(
                "Circular dependency detected for item: {}",
                item
            ));
        }

        visited.insert(item.to_string());

        // Find recipes that produce this item
        let producers: Vec<_> = self
            .config
            .recipes
            .iter()
            .filter(|(_, recipe)| recipe.outputs.contains_key(item))
            .collect();

        if producers.is_empty() {
            // This is a raw resource
            return Ok(());
        }

        // For simplicity, use the first producer
        // In a real implementation, you might want to optimize or let the user choose
        if let Some((recipe_id, recipe)) = producers.first() {
            let output_amount = recipe.outputs.get(item).unwrap();
            let recipe_rate = required_rate / (*output_amount as f32);

            *ratios.entry(recipe_id.to_string()).or_insert(0.0) += recipe_rate;

            // Recursively calculate requirements for inputs
            for (input_item, input_amount) in &recipe.inputs {
                let input_rate = recipe_rate * (*input_amount as f32);
                self.calculate_ratios_recursive(input_item, input_rate, ratios, visited)?;
            }
        }

        visited.remove(item);
        Ok(())
    }

    fn detect_cycles(&self, dependencies: &HashMap<String, HashSet<String>>) -> Vec<Vec<String>> {
        let mut cycles = Vec::new();
        let mut visited = HashSet::new();
        let mut rec_stack = HashSet::new();

        for recipe_id in dependencies.keys() {
            if !visited.contains(recipe_id) {
                let mut path = Vec::new();
                self.dfs_cycle_detection(
                    recipe_id,
                    dependencies,
                    &mut visited,
                    &mut rec_stack,
                    &mut path,
                    &mut cycles,
                );
            }
        }

        cycles
    }

    fn dfs_cycle_detection(
        &self,
        recipe_id: &str,
        dependencies: &HashMap<String, HashSet<String>>,
        visited: &mut HashSet<String>,
        rec_stack: &mut HashSet<String>,
        path: &mut Vec<String>,
        cycles: &mut Vec<Vec<String>>,
    ) {
        visited.insert(recipe_id.to_string());
        rec_stack.insert(recipe_id.to_string());
        path.push(recipe_id.to_string());

        if let Some(deps) = dependencies.get(recipe_id) {
            for dep in deps {
                // Find recipes that produce this dependency
                let dep_producers: Vec<_> = self
                    .config
                    .recipes
                    .iter()
                    .filter(|(_, recipe)| recipe.outputs.contains_key(dep))
                    .map(|(id, _)| id)
                    .collect();

                for producer_id in dep_producers {
                    if rec_stack.contains(producer_id) {
                        // Found a cycle
                        let cycle_start = path.iter().position(|x| x == producer_id).unwrap();
                        let cycle = path[cycle_start..].to_vec();
                        cycles.push(cycle);
                    } else if !visited.contains(producer_id) {
                        self.dfs_cycle_detection(
                            producer_id,
                            dependencies,
                            visited,
                            rec_stack,
                            path,
                            cycles,
                        );
                    }
                }
            }
        }

        path.pop();
        rec_stack.remove(recipe_id);
    }
}

#[derive(Debug)]
pub struct ProductionGraphAnalysis {
    pub dependencies: HashMap<String, HashSet<String>>,
    pub producers: HashMap<String, HashSet<String>>,
    pub cycles: Vec<Vec<String>>,
    pub resource_sources: Vec<String>,
    pub resource_sinks: Vec<String>,
}

impl ProductionGraphAnalysis {
    fn new() -> Self {
        Self {
            dependencies: HashMap::new(),
            producers: HashMap::new(),
            cycles: Vec::new(),
            resource_sources: Vec::new(),
            resource_sinks: Vec::new(),
        }
    }

    pub fn has_cycles(&self) -> bool {
        !self.cycles.is_empty()
    }

    pub fn is_resource_available(&self, resource: &str) -> bool {
        self.producers.contains_key(resource)
            || self.resource_sources.iter().any(|recipe_id| {
                if let Some(recipe) = self.producers.get(resource) {
                    recipe.contains(recipe_id)
                } else {
                    false
                }
            })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::resources::{GameConfig, RecipeConfig};

    #[test]
    fn test_production_graph_analysis() {
        let mut config = GameConfig::default();

        // Add a simple production chain: wood -> planks -> furniture
        config.recipes.insert(
            "make_planks".to_string(),
            RecipeConfig {
                name: "Make Planks".to_string(),
                production_time: 5.0,
                inputs: [("wood".to_string(), 1)].into(),
                outputs: [("planks".to_string(), 2)].into(),
                required_building: "sawmill".to_string(),
            },
        );

        config.recipes.insert(
            "make_furniture".to_string(),
            RecipeConfig {
                name: "Make Furniture".to_string(),
                production_time: 10.0,
                inputs: [("planks".to_string(), 3)].into(),
                outputs: [("furniture".to_string(), 1)].into(),
                required_building: "workshop".to_string(),
            },
        );

        let analyzer = EconomyAnalyzer::new(config);
        let analysis = analyzer.analyze_production_graph();

        // Should have dependencies
        assert!(analysis.dependencies.contains_key("make_planks"));
        assert!(analysis.dependencies.contains_key("make_furniture"));

        // Should have producers
        assert!(analysis.producers.contains_key("planks"));
        assert!(analysis.producers.contains_key("furniture"));

        // Should not have cycles in this simple chain
        assert!(!analysis.has_cycles());
    }

    #[test]
    fn test_production_ratios() {
        let mut config = GameConfig::default();

        config.recipes.insert(
            "make_planks".to_string(),
            RecipeConfig {
                name: "Make Planks".to_string(),
                production_time: 5.0,
                inputs: [("wood".to_string(), 1)].into(),
                outputs: [("planks".to_string(), 2)].into(),
                required_building: "sawmill".to_string(),
            },
        );

        let analyzer = EconomyAnalyzer::new(config);
        let ratios = analyzer.find_production_ratios("planks", 10.0).unwrap();

        // Should need 5 units of make_planks recipe to produce 10 planks (2 per recipe)
        assert_eq!(ratios.get("make_planks"), Some(&5.0));
    }

    #[test]
    fn test_flow_rates() {
        let config = GameConfig::default();
        let analyzer = EconomyAnalyzer::new(config);

        let mut production_rates = HashMap::new();
        production_rates.insert("harvest_wood".to_string(), 2.0); // 2 recipes per second

        let flow_rates = analyzer.calculate_flow_rates(&production_rates);

        // Should produce 4 wood per second (2 recipes * 2 wood per recipe)
        assert_eq!(flow_rates.get("wood"), Some(&4.0));
    }
}
