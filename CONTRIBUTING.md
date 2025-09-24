# Contributing to Old Times

Thank you for your interest in contributing to Old Times! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Rust stable (1.70+)
- Python 3.8+ (for asset pipeline)
- Git
- Just (recommended for convenient commands)

### Setting Up Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/old-times
   cd old-times
   ```

3. Set up the asset pipeline:
   ```bash
   just dev-setup
   ```

4. Generate assets:
   ```bash
   just all
   ```

5. Build and test:
   ```bash
   cargo build
   cargo test
   ```

## Development Workflow

### Code Style

- Use `rustfmt` for formatting: `cargo fmt`
- Follow `clippy` recommendations: `cargo clippy`
- Write tests for new functionality
- Document public APIs with doc comments

### Testing

Run tests before submitting:

```bash
# Run all tests
cargo test

# Run specific test suite
cargo test -p oldtimes-core

# Test asset pipeline
python -m pytest scripts/asset_pipeline/tests/

# Validate data files
cargo run -p oldtimes-headless -- validate-data
```

### Asset Development

When working with assets:

1. Use the asset pipeline for consistency:
   ```bash
   just all
   ```

2. Validate asset quality:
   ```bash
   just validate
   ```

3. Test with hot-reload during development:
   ```bash
   cargo run -p oldtimes-client
   # Edit assets/data/sprites.toml and see changes in real-time
   ```

## Types of Contributions

### Bug Reports

When reporting bugs, please include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Rust version)
- Relevant logs or error messages

### Feature Requests

For new features:

- Describe the feature and its use case
- Explain how it fits with the game's design
- Consider implementation complexity
- Discuss potential alternatives

### Code Contributions

#### Core Game Logic

- Located in `crates/oldtimes-core/`
- Must maintain deterministic behavior
- Add tests for new systems
- Consider performance implications

#### Asset Pipeline

- Located in `scripts/asset_pipeline/`
- Follow Python best practices
- Add tests for new functionality
- Update documentation

#### Client/UI

- Located in `crates/oldtimes-client/`
- Focus on user experience
- Test on different screen sizes
- Consider accessibility

### Documentation

- Update relevant documentation for changes
- Add examples for new features
- Keep README.md current
- Update GRAPHICS_GUIDE.md for asset changes

## Submission Guidelines

### Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes with clear, focused commits
3. Add tests for new functionality
4. Update documentation as needed
5. Run the full test suite:
   ```bash
   cargo test
   just validate
   ```

6. Push to your fork and create a pull request

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add hot-reload support for sprite metadata

- Implement hot_reload_sprite_metadata_system
- Add development-only metadata reloading
- Update documentation with hot-reload workflow

Fixes #123
```

Format: `type: brief description`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Include tests for new functionality
- Update documentation as needed
- Ensure CI passes
- Respond to review feedback promptly

## Code Organization

### Project Structure

```
old-times/
├── crates/
│   ├── oldtimes-core/      # Core simulation engine
│   │   ├── src/
│   │   │   ├── assets.rs   # Asset metadata loading
│   │   │   ├── systems/    # ECS systems
│   │   │   └── components/ # ECS components
│   │   └── Cargo.toml
│   ├── oldtimes-headless/  # Headless binary
│   └── oldtimes-client/    # Game client
├── assets/
│   ├── sprites/           # Game textures
│   ├── data/             # Game data files
│   └── atlases/          # Texture atlases
├── scripts/
│   └── asset_pipeline/   # Asset processing tools
├── examples/             # Usage examples
├── docs/                 # Additional documentation
└── mods/                 # Example mods
```

### Architecture Principles

1. **Deterministic Simulation**: Core game logic must be deterministic
2. **Headless-First**: Simulation runs independently of rendering
3. **Data-Driven**: Game content defined in TOML files
4. **Modular Design**: Clear separation between core, client, and tools
5. **Performance**: Optimize for large maps and many entities

## Asset Guidelines

### Creating New Assets

1. Follow isometric 2:1 standards
2. Use transparent backgrounds
3. Maintain consistent art style
4. Test with the asset pipeline

### Asset Standards

- **Tiles**: 64×32 pixels
- **Buildings**: Multiples of tile size
- **Units**: 64×64 pixels per frame
- **Format**: PNG with alpha channel

See [GRAPHICS_GUIDE.md](GRAPHICS_GUIDE.md) for detailed specifications.

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn
- Maintain a welcoming environment

### Communication

- Use GitHub issues for bug reports and feature requests
- Join discussions in pull requests
- Ask questions in issues or discussions
- Share your creations and mods

## Getting Help

- Check existing issues and documentation
- Ask questions in GitHub discussions
- Review the codebase for examples
- Look at existing tests for patterns

## Recognition

Contributors are recognized in:
- Git commit history
- Release notes for significant contributions
- Special thanks for major features

Thank you for contributing to Old Times!