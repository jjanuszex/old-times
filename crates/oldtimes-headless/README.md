# oldtimes-headless

Headless server and CLI tools for Old Times simulation engine.

## Overview

This binary provides command-line tools for running Old Times simulations without graphics or UI. It's designed for:

- Performance benchmarking
- Automated testing
- Replay verification
- Map generation
- Data validation
- Server hosting (planned)

## Installation

```bash
cargo install --path crates/oldtimes-headless
```

Or build from source:

```bash
cargo build --release -p oldtimes-headless
```

## Commands

### Run Simulation

Run a simulation for a specified number of ticks:

```bash
# Basic simulation
oldtimes-headless run --map demo --ticks 1000

# With recording
oldtimes-headless run --map demo --ticks 1000 --record replay.rpl

# Custom TPS
oldtimes-headless run --map demo --ticks 1000 --tps 30 --verbose
```

**Options:**
- `--map`: Map to load (`demo` for generated map)
- `--ticks`: Number of simulation ticks to run
- `--record`: Record replay to file
- `--tps`: Target ticks per second (default: 20)
- `--verbose`: Enable debug logging

### Replay System

Replay recorded sessions and verify determinism:

```bash
# Simple replay
oldtimes-headless replay session.rpl

# Verify determinism
oldtimes-headless replay session.rpl --verify
```

The `--verify` flag runs the simulation twice and compares state hashes to ensure deterministic behavior.

### Performance Benchmarking

Run performance benchmarks with different scenarios:

```bash
# Quick benchmark (100 ticks)
oldtimes-headless benchmark --scenario quick

# Standard benchmark (1000 ticks)
oldtimes-headless benchmark --scenario standard --iterations 5

# Long benchmark (10000 ticks)
oldtimes-headless benchmark --scenario long
```

**Scenarios:**
- `quick`: 100 ticks, fast feedback
- `standard`: 1000 ticks, typical gameplay
- `long`: 10000 ticks, stress testing

### Map Generation

Generate custom maps with specified parameters:

```bash
# Basic map generation
oldtimes-headless generate-map --output custom_map.ron

# Custom parameters
oldtimes-headless generate-map \
  --width 128 \
  --height 128 \
  --seed 54321 \
  --output large_map.ron
```

**Options:**
- `--width`, `--height`: Map dimensions
- `--seed`: Random seed for generation
- `--output`: Output filename

### Data Validation

Validate game data files for syntax and consistency:

```bash
# Validate base game data
oldtimes-headless validate-data --data-dir assets/data

# Validate mod data
oldtimes-headless validate-data --data-dir mods/my-mod
```

This checks:
- TOML syntax validity
- Required fields presence
- Value range validation
- Production chain consistency
- Circular dependency detection

## Examples

### Performance Testing

```bash
# Run a comprehensive performance test
oldtimes-headless benchmark --scenario standard --iterations 10

# Expected output:
# Benchmark Results:
#   Average time: 45.23s
#   Average TPS: 22.1
#   Total time: 452.3s
```

### Determinism Verification

```bash
# Record a session
oldtimes-headless run --map demo --ticks 5000 --record test.rpl

# Verify it's deterministic
oldtimes-headless replay test.rpl --verify

# Expected output:
# ✓ Replay verification passed - simulation is deterministic
```

### Automated Testing

```bash
#!/bin/bash
# Automated test script

# Test different scenarios
for scenario in quick standard; do
  echo "Testing $scenario scenario..."
  oldtimes-headless benchmark --scenario $scenario --iterations 3
done

# Test determinism
oldtimes-headless run --map demo --ticks 1000 --record test.rpl
oldtimes-headless replay test.rpl --verify || exit 1

echo "All tests passed!"
```

## Output Formats

### Benchmark Results

```
Benchmark Results:
  Average time: 45.23s
  Average TPS: 22.1
  Total time: 452.3s
  
Performance Metrics:
  Final entity count: 156
  Average tick time: 2.34ms
  Pathfinding cache hit rate: 87.3%
```

### Validation Results

```
✓ Data validation passed
  Buildings: 6
  Recipes: 6
  Workers: 1
  
✓ No production cycles detected
  Resource sources: 3
  Resource sinks: 0
```

## Configuration

The headless binary uses the same data files as the main game:

```
assets/
├── data/
│   ├── buildings.toml
│   ├── recipes.toml
│   ├── workers.toml
│   └── mapgen.toml
└── ...
```

## Performance Targets

Expected performance on modern hardware:
- **Standard scenario**: >20 TPS average
- **Memory usage**: <100MB for typical maps
- **Startup time**: <2 seconds
- **Determinism**: 100% replay accuracy

## Integration

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run performance benchmark
  run: |
    cargo run --release -p oldtimes-headless -- benchmark --scenario standard
    
- name: Verify determinism
  run: |
    cargo run --release -p oldtimes-headless -- run --ticks 1000 --record test.rpl
    cargo run --release -p oldtimes-headless -- replay test.rpl --verify
```

### Scripting

The headless binary is designed to be scriptable:

```python
import subprocess
import json

# Run benchmark and parse results
result = subprocess.run([
    'oldtimes-headless', 'benchmark', 
    '--scenario', 'standard', 
    '--iterations', '5'
], capture_output=True, text=True)

# Parse performance metrics from output
# (Implementation depends on output format)
```

## Troubleshooting

### Common Issues

**Low TPS Performance:**
- Check system resources (CPU, memory)
- Reduce map size or entity count
- Use release build for benchmarking

**Determinism Failures:**
- Ensure identical starting conditions
- Check for floating-point precision issues
- Verify no external randomness sources

**Data Validation Errors:**
- Check TOML syntax with online validator
- Verify all required fields are present
- Ensure numeric values are in valid ranges

### Debug Logging

Enable verbose logging for troubleshooting:

```bash
RUST_LOG=debug oldtimes-headless run --map demo --ticks 100 --verbose
```

## Development

### Building

```bash
# Debug build
cargo build -p oldtimes-headless

# Release build (recommended for benchmarking)
cargo build --release -p oldtimes-headless
```

### Testing

```bash
# Unit tests
cargo test -p oldtimes-headless

# Integration tests
cargo test --test integration
```