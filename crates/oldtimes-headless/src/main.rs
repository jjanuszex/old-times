use clap::{Parser, Subcommand};
use oldtimes_core::{SimulationApp, save::*, data::*};
use anyhow::Result;
use std::time::Instant;
use ron::ser::{to_string_pretty, PrettyConfig};

#[derive(Parser)]
#[command(name = "oldtimes-headless")]
#[command(about = "Old Times headless simulation server")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run simulation for specified ticks
    Run {
        /// Map name to load (or 'demo' for generated map)
        #[arg(long, default_value = "demo")]
        map: String,
        
        /// Number of ticks to run
        #[arg(long, default_value = "1000")]
        ticks: u64,
        
        /// Record replay to file
        #[arg(long)]
        record: Option<String>,
        
        /// Target TPS (ticks per second)
        #[arg(long, default_value = "20")]
        tps: u32,
        
        /// Enable verbose logging
        #[arg(short, long)]
        verbose: bool,
    },
    
    /// Replay a recorded session
    Replay {
        /// Replay file to load
        replay_file: String,
        
        /// Verify determinism by comparing with fresh run
        #[arg(long)]
        verify: bool,
    },
    
    /// Run performance benchmark
    Benchmark {
        /// Benchmark scenario to run
        #[arg(long, default_value = "standard")]
        scenario: String,
        
        /// Number of iterations
        #[arg(long, default_value = "5")]
        iterations: u32,
    },
    
    /// Generate a new map
    GenerateMap {
        /// Output file name
        #[arg(long, default_value = "generated_map.ron")]
        output: String,
        
        /// Map width
        #[arg(long, default_value = "64")]
        width: u32,
        
        /// Map height  
        #[arg(long, default_value = "64")]
        height: u32,
        
        /// Random seed
        #[arg(long, default_value = "12345")]
        seed: u64,
    },
    
    /// Validate game data files
    ValidateData {
        /// Data directory to validate
        #[arg(long, default_value = "assets/data")]
        data_dir: String,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    
    match &cli.command {
        Commands::Run { map, ticks, record, tps, verbose } => {
            init_logging(*verbose);
            run_simulation(map, *ticks, record.as_deref(), *tps)
        },
        Commands::Replay { replay_file, verify } => {
            init_logging(true);
            replay_simulation(replay_file, *verify)
        },
        Commands::Benchmark { scenario, iterations } => {
            init_logging(false);
            run_benchmark(scenario, *iterations)
        },
        Commands::GenerateMap { output, width, height, seed } => {
            init_logging(false);
            generate_map(output, *width, *height, *seed)
        },
        Commands::ValidateData { data_dir } => {
            init_logging(true);
            validate_data(data_dir)
        },
    }
}

fn init_logging(verbose: bool) {
    let level = if verbose {
        log::LevelFilter::Debug
    } else {
        log::LevelFilter::Info
    };
    
    env_logger::Builder::from_default_env()
        .filter_level(level)
        .init();
}

fn run_simulation(map_name: &str, ticks: u64, record_file: Option<&str>, tps: u32) -> Result<()> {
    log::info!("Starting simulation: map={}, ticks={}, tps={}", map_name, ticks, tps);
    
    let mut sim = SimulationApp::new();
    
    // Set target TPS
    if let Some(mut tick_resource) = sim.get_resource_mut::<oldtimes_core::GameTick>() {
        tick_resource.target_tps = tps;
    }
    
    // Initialize map
    if map_name == "demo" {
        sim.initialize_demo();
    } else {
        // In a full implementation, load map from file
        log::warn!("Custom map loading not implemented, using demo map");
        sim.initialize_demo();
    }
    
    // Setup recording if requested
    let mut recorder = record_file.map(|_| start_recording());
    
    // Run simulation
    let start_time = Instant::now();
    let target_tick_duration = std::time::Duration::from_secs_f32(1.0 / tps as f32);
    
    for tick in 0..ticks {
        let tick_start = Instant::now();
        
        sim.tick();
        
        // Record events if needed
        if let Some(ref mut rec) = recorder {
            // In a full implementation, capture and record events here
        }
        
        // Progress reporting
        if tick % (tps as u64 * 5) == 0 {
            let elapsed = start_time.elapsed().as_secs_f32();
            let progress = (tick as f32 / ticks as f32) * 100.0;
            log::info!("Progress: {:.1}% ({}/{}) - {:.1}s elapsed", 
                      progress, tick, ticks, elapsed);
        }
        
        // Maintain target TPS
        let tick_duration = tick_start.elapsed();
        if tick_duration < target_tick_duration {
            std::thread::sleep(target_tick_duration - tick_duration);
        }
    }
    
    let total_time = start_time.elapsed();
    let actual_tps = ticks as f32 / total_time.as_secs_f32();
    
    log::info!("Simulation completed in {:.2}s", total_time.as_secs_f32());
    log::info!("Average TPS: {:.1} (target: {})", actual_tps, tps);
    
    // Print performance metrics
    let metrics = sim.get_metrics();
    log::info!("Final entity count: {}", metrics.entities_count);
    log::info!("Average tick time: {:.2}ms", metrics.tick_time);
    
    if let Some(cache) = sim.get_resource::<oldtimes_core::PathfindingCache>() {
        log::info!("Pathfinding cache hit rate: {:.1}%", cache.hit_rate() * 100.0);
    }
    
    // Save recording if requested
    if let (Some(recorder), Some(filename)) = (recorder, record_file) {
        recorder.save_replay(filename)?;
        log::info!("Replay saved to {}", filename);
    }
    
    Ok(())
}

fn replay_simulation(replay_file: &str, verify: bool) -> Result<()> {
    log::info!("Replaying simulation from {}", replay_file);
    
    if verify {
        let is_deterministic = load_and_verify_replay(replay_file)?;
        if is_deterministic {
            log::info!("✓ Replay verification passed - simulation is deterministic");
        } else {
            log::error!("✗ Replay verification failed - simulation is not deterministic");
            std::process::exit(1);
        }
    } else {
        // Just replay without verification
        log::info!("Replay playback (without verification) not fully implemented");
    }
    
    Ok(())
}

fn run_benchmark(scenario: &str, iterations: u32) -> Result<()> {
    log::info!("Running benchmark: scenario={}, iterations={}", scenario, iterations);
    
    let mut total_time = 0.0;
    let mut total_tps = 0.0;
    
    for i in 0..iterations {
        log::info!("Benchmark iteration {}/{}", i + 1, iterations);
        
        let mut sim = SimulationApp::new();
        sim.initialize_demo();
        
        let start_time = Instant::now();
        let benchmark_ticks = match scenario {
            "quick" => 100,
            "standard" => 1000,
            "long" => 10000,
            _ => 1000,
        };
        
        sim.run_ticks(benchmark_ticks);
        
        let elapsed = start_time.elapsed().as_secs_f32();
        let tps = benchmark_ticks as f32 / elapsed;
        
        total_time += elapsed;
        total_tps += tps;
        
        log::info!("Iteration {} completed: {:.2}s, {:.1} TPS", i + 1, elapsed, tps);
    }
    
    let avg_time = total_time / iterations as f32;
    let avg_tps = total_tps / iterations as f32;
    
    log::info!("Benchmark Results:");
    log::info!("  Average time: {:.2}s", avg_time);
    log::info!("  Average TPS: {:.1}", avg_tps);
    log::info!("  Total time: {:.2}s", total_time);
    
    Ok(())
}

fn generate_map(output: &str, width: u32, height: u32, seed: u64) -> Result<()> {
    log::info!("Generating map: {}x{}, seed={}", width, height, seed);
    
    let config = oldtimes_core::resources::MapGenerationConfig {
        width,
        height,
        forest_density: 0.3,
        stone_density: 0.1,
        water_patches: 3,
        seed,
    };
    
    let map = oldtimes_core::map::generate_map_from_config(&config);
    
    // Save map to file
    let serialized = to_string_pretty(&map, PrettyConfig::default())?;
    std::fs::write(output, serialized)?;
    
    log::info!("Map saved to {}", output);
    Ok(())
}

fn validate_data(data_dir: &str) -> Result<()> {
    log::info!("Validating data files in {}", data_dir);
    
    match DataLoader::load_from_directory(data_dir) {
        Ok(config) => {
            log::info!("✓ Data validation passed");
            log::info!("  Buildings: {}", config.buildings.len());
            log::info!("  Recipes: {}", config.recipes.len());
            log::info!("  Workers: {}", config.workers.len());
            
            // Analyze production graph
            let analyzer = oldtimes_core::economy::EconomyAnalyzer::new(config);
            let analysis = analyzer.analyze_production_graph();
            
            if analysis.has_cycles() {
                log::warn!("⚠ Production cycles detected:");
                for cycle in &analysis.cycles {
                    log::warn!("  Cycle: {}", cycle.join(" -> "));
                }
            } else {
                log::info!("✓ No production cycles detected");
            }
            
            log::info!("  Resource sources: {}", analysis.resource_sources.len());
            log::info!("  Resource sinks: {}", analysis.resource_sinks.len());
        },
        Err(e) => {
            log::error!("✗ Data validation failed: {}", e);
            std::process::exit(1);
        }
    }
    
    Ok(())
}