#!/bin/bash
# Performance benchmark script for Old Times

set -e

echo "Old Times Performance Benchmark"
echo "==============================="

# Build in release mode
echo "Building in release mode..."
cargo build --release --quiet

# Create results directory
mkdir -p benchmark_results
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_FILE="benchmark_results/benchmark_$TIMESTAMP.txt"

echo "Results will be saved to: $RESULTS_FILE"
echo "" > "$RESULTS_FILE"

# System information
echo "System Information:" | tee -a "$RESULTS_FILE"
echo "==================" | tee -a "$RESULTS_FILE"
echo "Date: $(date)" | tee -a "$RESULTS_FILE"
echo "OS: $(uname -s)" | tee -a "$RESULTS_FILE"
echo "Architecture: $(uname -m)" | tee -a "$RESULTS_FILE"
echo "Rust version: $(rustc --version)" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Quick benchmark
echo "Quick Benchmark (100 ticks):" | tee -a "$RESULTS_FILE"
echo "============================" | tee -a "$RESULTS_FILE"
cargo run --release -p oldtimes-headless -- benchmark --scenario quick --iterations 3 2>&1 | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Standard benchmark
echo "Standard Benchmark (1000 ticks):" | tee -a "$RESULTS_FILE"
echo "================================" | tee -a "$RESULTS_FILE"
cargo run --release -p oldtimes-headless -- benchmark --scenario standard --iterations 5 2>&1 | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Long benchmark
echo "Long Benchmark (10000 ticks):" | tee -a "$RESULTS_FILE"
echo "=============================" | tee -a "$RESULTS_FILE"
cargo run --release -p oldtimes-headless -- benchmark --scenario long --iterations 3 2>&1 | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Determinism test
echo "Determinism Test:" | tee -a "$RESULTS_FILE"
echo "=================" | tee -a "$RESULTS_FILE"
echo "Recording replay..." | tee -a "$RESULTS_FILE"
cargo run --release -p oldtimes-headless -- run --map demo --ticks 1000 --record test_replay.rpl 2>&1 | tee -a "$RESULTS_FILE"

echo "Verifying replay..." | tee -a "$RESULTS_FILE"
cargo run --release -p oldtimes-headless -- replay test_replay.rpl --verify 2>&1 | tee -a "$RESULTS_FILE"

# Cleanup
rm -f test_replay.rpl

echo "" | tee -a "$RESULTS_FILE"
echo "Benchmark completed!" | tee -a "$RESULTS_FILE"
echo "Results saved to: $RESULTS_FILE"

# Show summary
echo ""
echo "Summary:"
echo "========"
grep -E "(Average TPS|Average time|verification)" "$RESULTS_FILE" || echo "No summary data found"