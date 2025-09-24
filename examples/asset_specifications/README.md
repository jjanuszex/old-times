# Asset Specifications and Templates

This directory contains example asset specifications, templates, and guidelines for creating assets compatible with the Old Times asset pipeline.

## Asset Specifications

### Tiles (Terrain)
- **Dimensions**: Exactly 64×32 pixels
- **Format**: PNG with alpha channel
- **Background**: Completely transparent (alpha = 0)
- **Projection**: Isometric 2:1 aspect ratio
- **Style**: Pixel art or clean vector art
- **Edges**: Sharp, no anti-aliasing on edges

### Buildings
- **Dimensions**: Multiples of 32px height (64×96, 128×96, 192×96)
- **Width**: Multiples of 64px for multi-tile buildings
- **Format**: PNG with alpha channel
- **Background**: Transparent
- **Alignment**: Bottom edge aligns with isometric grid
- **Details**: Include shadows, depth, architectural details
- **Style**: Consistent with game's medieval/fantasy theme

### Units
- **Frame Size**: Exactly 64×64 pixels per animation frame
- **Animation**: 8 directions × 8 walking frames = 64 total frames
- **Directions**: N, NE, E, SE, S, SW, W, NW (clockwise from north)
- **Format**: PNG with alpha channel
- **Background**: Transparent
- **Centering**: Unit centered in frame
- **Consistency**: Consistent lighting and style across all frames

## Templates

### Photoshop/GIMP Templates
- `tile_template.psd` - Template for creating terrain tiles
- `building_template.psd` - Template for creating buildings
- `unit_template.psd` - Template for creating unit animations

### Sprite Sheets
- `unit_spritesheet_template.png` - Layout template for unit animations
- `building_variations_template.png` - Template for building variations

### Configuration Templates
- `asset_spec.toml` - Template for asset specifications
- `animation_spec.toml` - Template for animation definitions

## Guidelines

### Color Palette
The game uses a consistent color palette for visual coherence:
- **Earth tones**: Browns, tans, ochres for buildings and terrain
- **Natural colors**: Greens for vegetation, blues for water
- **Accent colors**: Reds, golds for important elements
- **Shadows**: Dark browns and grays, not pure black

### Lighting
- **Light source**: Top-left (northwest) for consistent shadows
- **Shadow direction**: Bottom-right (southeast)
- **Ambient lighting**: Soft, diffused light
- **Contrast**: Moderate contrast for readability

### Style Guidelines
- **Pixel art**: Clean, readable pixel art style
- **Detail level**: Appropriate detail for viewing distance
- **Consistency**: Maintain consistent style across all assets
- **Readability**: Assets must be clear at game resolution

## Quality Checklist

Before submitting assets, verify:
- [ ] Correct dimensions (64×32 for tiles, 64×64 for units, etc.)
- [ ] Transparent background (alpha = 0)
- [ ] Proper isometric projection
- [ ] Consistent lighting and shadows
- [ ] Clean edges without anti-aliasing artifacts
- [ ] Appropriate level of detail
- [ ] Consistent art style
- [ ] Proper file naming convention

## File Naming Conventions

### Tiles
```
grass.png
water.png
stone.png
forest.png
```

### Buildings
```
lumberjack.png
sawmill.png
farm.png
mill.png
```

### Units (Individual Frames)
```
worker_N_0.png, worker_N_1.png, ..., worker_N_7.png
worker_NE_0.png, worker_NE_1.png, ..., worker_NE_7.png
...
worker_NW_0.png, worker_NW_1.png, ..., worker_NW_7.png
```

### Units (Sprite Sheets)
```
worker_spritesheet.png  # 512×512 with 8×8 frame layout
```