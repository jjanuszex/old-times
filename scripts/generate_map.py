#!/usr/bin/env python3
"""
Map generator script for Old Times
Generates custom maps with specified parameters
"""

import argparse
import json
import random
import math
from typing import List, Tuple

def generate_noise(width: int, height: int, seed: int, scale: float = 0.1) -> List[List[float]]:
    """Generate Perlin-like noise for terrain generation"""
    random.seed(seed)
    noise = []
    
    for y in range(height):
        row = []
        for x in range(width):
            # Simple noise approximation
            value = 0.0
            amplitude = 1.0
            frequency = scale
            
            for _ in range(4):  # 4 octaves
                nx = x * frequency
                ny = y * frequency
                
                # Simple hash-based noise
                hash_val = hash((int(nx), int(ny), seed)) % 1000000
                noise_val = (hash_val / 1000000.0) * 2.0 - 1.0
                
                value += noise_val * amplitude
                amplitude *= 0.5
                frequency *= 2.0
            
            row.append(value)
        noise.append(row)
    
    return noise

def generate_map(width: int, height: int, seed: int, forest_density: float, stone_density: float, water_patches: int) -> dict:
    """Generate a map with specified parameters"""
    
    # Generate base terrain noise
    elevation_noise = generate_noise(width, height, seed, 0.05)
    forest_noise = generate_noise(width, height, seed + 1, 0.1)
    stone_noise = generate_noise(width, height, seed + 2, 0.08)
    
    tiles = []
    
    for y in range(height):
        row = []
        for x in range(width):
            elevation = elevation_noise[y][x]
            forest_val = forest_noise[y][x]
            stone_val = stone_noise[y][x]
            
            # Determine tile type
            if elevation < -0.3:
                tile_type = "Water"
            elif stone_val > (1.0 - stone_density * 2.0):
                tile_type = "Stone"
            elif forest_val > (1.0 - forest_density * 2.0):
                tile_type = "Forest"
            else:
                tile_type = "Grass"
            
            tile = {
                "tile_type": tile_type,
                "elevation": int((elevation + 1.0) * 127.5)
            }
            row.append(tile)
        tiles.append(row)
    
    # Add some roads
    add_roads(tiles, width, height)
    
    map_data = {
        "width": width,
        "height": height,
        "tiles": tiles
    }
    
    return map_data

def add_roads(tiles: List[List[dict]], width: int, height: int):
    """Add road network to the map"""
    
    # Horizontal road
    road_y = height // 2
    for x in range(width // 4, 3 * width // 4):
        if tiles[road_y][x]["tile_type"] == "Grass":
            tiles[road_y][x]["tile_type"] = "Road"
    
    # Vertical road
    road_x = width // 2
    for y in range(height // 4, 3 * height // 4):
        if tiles[y][road_x]["tile_type"] == "Grass":
            tiles[y][road_x]["tile_type"] = "Road"

def save_map_ron(map_data: dict, filename: str):
    """Save map in RON format"""
    
    # Convert to RON-like format
    ron_content = f"""(
    width: {map_data['width']},
    height: {map_data['height']},
    tiles: [
"""
    
    for row in map_data['tiles']:
        ron_content += "        [\n"
        for tile in row:
            ron_content += f"            (tile_type: {tile['tile_type']}, elevation: {tile['elevation']}),\n"
        ron_content += "        ],\n"
    
    ron_content += """    ],
)"""
    
    with open(filename, 'w') as f:
        f.write(ron_content)

def main():
    parser = argparse.ArgumentParser(description='Generate maps for Old Times')
    parser.add_argument('--width', type=int, default=64, help='Map width')
    parser.add_argument('--height', type=int, default=64, help='Map height')
    parser.add_argument('--seed', type=int, default=12345, help='Random seed')
    parser.add_argument('--forest-density', type=float, default=0.3, help='Forest density (0.0-1.0)')
    parser.add_argument('--stone-density', type=float, default=0.1, help='Stone density (0.0-1.0)')
    parser.add_argument('--water-patches', type=int, default=3, help='Number of water patches')
    parser.add_argument('--output', type=str, default='generated_map.ron', help='Output filename')
    parser.add_argument('--format', type=str, choices=['ron', 'json'], default='ron', help='Output format')
    
    args = parser.parse_args()
    
    print(f"Generating map: {args.width}x{args.height}, seed={args.seed}")
    
    map_data = generate_map(
        args.width, 
        args.height, 
        args.seed, 
        args.forest_density, 
        args.stone_density, 
        args.water_patches
    )
    
    if args.format == 'ron':
        save_map_ron(map_data, args.output)
    else:
        with open(args.output, 'w') as f:
            json.dump(map_data, f, indent=2)
    
    print(f"Map saved to {args.output}")
    
    # Print statistics
    tile_counts = {}
    for row in map_data['tiles']:
        for tile in row:
            tile_type = tile['tile_type']
            tile_counts[tile_type] = tile_counts.get(tile_type, 0) + 1
    
    total_tiles = args.width * args.height
    print("\nTile distribution:")
    for tile_type, count in sorted(tile_counts.items()):
        percentage = (count / total_tiles) * 100
        print(f"  {tile_type}: {count} ({percentage:.1f}%)")

if __name__ == '__main__':
    main()