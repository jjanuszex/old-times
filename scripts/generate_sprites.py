#!/usr/bin/env python3
"""
Simple sprite generator for Old Times RTS game.
Creates basic colored rectangles for buildings and units.
"""

from PIL import Image, ImageDraw
import os

# Create assets directory if it doesn't exist
os.makedirs("assets/sprites", exist_ok=True)

# Tile size
TILE_SIZE = 32

# Building definitions with colors and sizes
BUILDINGS = {
    "lumberjack": {"color": (204, 102, 51), "size": (2, 2)},
    "sawmill": {"color": (153, 76, 25), "size": (3, 3)},
    "farm": {"color": (230, 204, 76), "size": (4, 4)},
    "mill": {"color": (178, 178, 178), "size": (3, 3)},
    "bakery": {"color": (230, 153, 102), "size": (2, 3)},
    "quarry": {"color": (127, 127, 127), "size": (3, 3)},
}

# Terrain types
TERRAIN = {
    "grass": (51, 204, 51),
    "water": (51, 51, 204),
    "stone": (153, 153, 153),
    "forest": (25, 153, 25),
    "road": (204, 178, 127),
}

# Unit types
UNITS = {
    "worker": (102, 178, 255),
}

def create_building_sprite(name, color, size):
    """Create a building sprite with the given color and size."""
    width = size[0] * TILE_SIZE
    height = size[1] * TILE_SIZE
    
    # Create image with transparency
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw main building body
    draw.rectangle([2, 2, width-3, height-3], fill=color, outline=(0, 0, 0))
    
    # Add some detail - roof
    roof_color = tuple(min(255, c + 30) for c in color)
    draw.rectangle([0, 0, width-1, 8], fill=roof_color, outline=(0, 0, 0))
    
    # Add door (for smaller buildings)
    if width <= 64:
        door_x = width // 2 - 4
        door_y = height - 12
        draw.rectangle([door_x, door_y, door_x + 8, height-3], fill=(101, 67, 33))
    
    # Add windows
    window_color = (255, 255, 200)
    if width >= 64:  # Larger buildings get more windows
        for i in range(1, size[0]):
            for j in range(1, size[1]):
                wx = i * TILE_SIZE - 8
                wy = j * TILE_SIZE - 8
                draw.rectangle([wx, wy, wx + 6, wy + 6], fill=window_color, outline=(0, 0, 0))
    else:
        # Single window for small buildings
        wx = width // 2 - 3
        wy = height // 2 - 6
        draw.rectangle([wx, wy, wx + 6, wy + 6], fill=window_color, outline=(0, 0, 0))
    
    return img

def create_terrain_sprite(name, color):
    """Create a terrain tile sprite."""
    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), color)
    draw = ImageDraw.Draw(img)
    
    if name == "grass":
        # Add some grass texture
        for i in range(0, TILE_SIZE, 4):
            for j in range(0, TILE_SIZE, 4):
                if (i + j) % 8 == 0:
                    grass_color = (25, 178, 25)
                    draw.rectangle([i, j, i+2, j+2], fill=grass_color)
    
    elif name == "water":
        # Add wave pattern
        for i in range(0, TILE_SIZE, 8):
            wave_color = (76, 76, 230)
            draw.line([(0, i), (TILE_SIZE, i)], fill=wave_color, width=1)
    
    elif name == "forest":
        # Draw simple tree
        trunk_color = (101, 67, 33)
        leaves_color = (0, 102, 0)
        
        # Tree trunk
        draw.rectangle([14, 20, 18, 30], fill=trunk_color)
        # Tree leaves
        draw.ellipse([8, 8, 24, 24], fill=leaves_color, outline=(0, 0, 0))
    
    elif name == "stone":
        # Add stone texture
        for i in range(0, TILE_SIZE, 6):
            for j in range(0, TILE_SIZE, 6):
                if (i + j) % 12 == 0:
                    stone_color = (178, 178, 178)
                    draw.rectangle([i, j, i+3, j+3], fill=stone_color)
    
    elif name == "road":
        # Add road lines
        line_color = (178, 153, 102)
        draw.line([(0, TILE_SIZE//2), (TILE_SIZE, TILE_SIZE//2)], fill=line_color, width=2)
    
    return img

def create_unit_sprite(name, color):
    """Create a unit sprite."""
    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw simple character
    # Head
    draw.ellipse([12, 4, 20, 12], fill=color, outline=(0, 0, 0))
    # Body
    draw.rectangle([14, 12, 18, 24], fill=color, outline=(0, 0, 0))
    # Arms
    draw.line([(10, 16), (22, 16)], fill=color, width=2)
    # Legs
    draw.line([(14, 24), (12, 30)], fill=color, width=2)
    draw.line([(18, 24), (20, 30)], fill=color, width=2)
    
    return img

def main():
    print("Generating sprites for Old Times RTS...")
    
    # Generate building sprites
    print("Creating building sprites...")
    for name, props in BUILDINGS.items():
        img = create_building_sprite(name, props["color"], props["size"])
        img.save(f"assets/sprites/{name}.png")
        print(f"  Created {name}.png ({props['size'][0]}x{props['size'][1]} tiles)")
    
    # Generate terrain sprites
    print("Creating terrain sprites...")
    for name, color in TERRAIN.items():
        img = create_terrain_sprite(name, color)
        img.save(f"assets/sprites/{name}.png")
        print(f"  Created {name}.png")
    
    # Generate unit sprites
    print("Creating unit sprites...")
    for name, color in UNITS.items():
        img = create_unit_sprite(name, color)
        img.save(f"assets/sprites/{name}.png")
        print(f"  Created {name}.png")
    
    # Create a simple UI background
    print("Creating UI elements...")
    ui_bg = Image.new('RGBA', (100, 30), (0, 0, 0, 200))
    ui_bg.save("assets/ui/panel_bg.png")
    
    print("Sprite generation complete!")
    print(f"Generated {len(BUILDINGS) + len(TERRAIN) + len(UNITS) + 1} sprites")

if __name__ == "__main__":
    main()