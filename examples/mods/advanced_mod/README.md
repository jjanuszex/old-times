# Advanced Fantasy Mod

A comprehensive example mod demonstrating advanced features of the Old Times modding system.

## Features

- **5 New Buildings**: Wizard towers, dragon lairs, crystal mines, and more
- **5 New Units**: Wizards, dragons, golems with custom animations
- **5 New Terrain Types**: Magical landscapes and crystal formations
- **Custom Effects**: Particle effects, glowing elements, magical auras
- **Advanced Animations**: Multi-frame animations for units and buildings

## Structure

```
advanced_mod/
├── mod.toml                    # Comprehensive mod configuration
├── README.md                   # This documentation
├── CHANGELOG.md                # Version history
├── LICENSE                     # License information
├── sprites/                    # Generated mod sprites
│   ├── buildings/
│   ├── terrain/
│   ├── units/
│   └── effects/
├── atlases/                    # Generated texture atlases
│   ├── wizard_atlas.png
│   ├── dragon_atlas.png
│   └── effects_atlas.png
├── data/
│   ├── sprites.toml           # Generated sprite metadata
│   └── animations.toml        # Animation definitions
├── source_assets/             # Source files for generation
│   ├── buildings/
│   │   ├── wizard_tower/
│   │   ├── dragon_lair/
│   │   └── crystal_mine/
│   ├── units/
│   │   ├── wizard/            # 64 animation frames
│   │   ├── dragon/            # 64 animation frames
│   │   └── crystal_golem/     # 64 animation frames
│   ├── terrain/
│   └── effects/
├── localization/              # Multi-language support
│   ├── en.toml
│   ├── es.toml
│   └── fr.toml
└── docs/                      # Additional documentation
    ├── BUILDING_GUIDE.md
    ├── ANIMATION_GUIDE.md
    └── API_REFERENCE.md
```

## Installation

1. **Download the mod** or clone from repository
2. **Place in mods directory**:
   ```bash
   cp -r advanced_mod mods/
   ```
3. **Generate assets**:
   ```bash
   just mod advanced_mod
   ```

## Development

### Adding New Assets

1. **Buildings**:
   - Create source images in `source_assets/buildings/building_name/`
   - Add building definition to `mod.toml`
   - Run asset pipeline

2. **Units**:
   - Create 64 animation frames (8 directions × 8 frames)
   - Place in `source_assets/units/unit_name/`
   - Configure animation in `mod.toml`

3. **Terrain**:
   - Create isometric terrain tiles
   - Place in `source_assets/terrain/`
   - Follow 64×32 pixel requirements

### Custom Animations

This mod demonstrates advanced animation features:

```toml
[animations.wizard_spell_casting]
frames = 12
fps = 8
loop = true
effects = ["sparkles", "glow"]

[animations.dragon_flying]
frames = 16
fps = 12
loop = true
shadow = true
```

### Quality Standards

All assets follow strict quality requirements:
- **Pixel-perfect dimensions**
- **Transparent backgrounds**
- **Isometric 2:1 compliance**
- **Consistent art style**

## Configuration

The mod includes extensive configuration options in `mod.toml`:

- **Asset Management**: Detailed asset inventory
- **Build Settings**: Custom processing parameters
- **Animation Config**: Frame counts, timing, effects
- **Localization**: Multi-language support
- **Dependencies**: Version requirements

## Contributing

1. Fork the repository
2. Create feature branch
3. Add your assets following the guidelines
4. Test with the asset pipeline
5. Submit pull request

## License

This mod is licensed under CC-BY-SA-4.0. See LICENSE file for details.