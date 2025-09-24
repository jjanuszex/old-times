# Contributing to Old Times

Thank you for your interest in contributing to Old Times! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Rust stable (1.70+)
- Git
- Basic familiarity with Rust and Bevy ECS

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/old-times.git
   cd old-times
   ```
3. Build the project:
   ```bash
   cargo build
   ```
4. Run tests:
   ```bash
   cargo test
   ```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

feat(core): add pathfinding cache system
fix(ui): resolve building placement visual bug
docs(readme): update installation instructions
test(economy): add production chain validation tests
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance tasks

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass: `cargo test`
5. Run formatting: `cargo fmt`
6. Run linting: `cargo clippy`
7. Update documentation if needed
8. Submit a pull request

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## Code Style Guidelines

### Rust Style

- Use `rustfmt` with default settings
- Follow `clippy` recommendations
- Prefer explicit types when it improves readability
- Use descriptive variable names
- Add documentation for public APIs

### Project Conventions

#### Component Design
```rust
#[derive(Component, Debug, Clone, Serialize, Deserialize)]
pub struct MyComponent {
    pub field: Type,
}

impl MyComponent {
    pub fn new(field: Type) -> Self {
        Self { field }
    }
}
```

#### System Design
```rust
pub fn my_system(
    query: Query<&MyComponent>,
    mut events: EventWriter<MyEvent>,
) {
    // System logic here
}
```

#### Error Handling
- Use `anyhow::Result` for functions that can fail
- Provide meaningful error messages
- Log errors appropriately

#### Testing
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_functionality() {
        // Test implementation
        assert_eq!(expected, actual);
    }
}
```

## Architecture Guidelines

### Core Principles

1. **Deterministic**: All simulation logic must be deterministic
2. **Data-driven**: Prefer configuration over hard-coded values
3. **Modular**: Keep systems loosely coupled
4. **Testable**: Write testable code with clear interfaces

### Adding New Features

#### New Building Type
1. Add definition to `assets/data/buildings.toml`
2. Add recipes to `assets/data/recipes.toml`
3. Update client UI if needed
4. Add tests for new functionality
5. Update documentation

#### New System
1. Create system in appropriate module
2. Add to simulation app
3. Write unit tests
4. Add integration tests
5. Document system behavior

#### New Component
1. Define component with proper derives
2. Add to relevant queries
3. Update save/load system
4. Add validation if needed
5. Write tests

## Testing Guidelines

### Test Categories

#### Unit Tests
- Test individual functions and components
- Mock external dependencies
- Fast execution
- High coverage of edge cases

#### Integration Tests
- Test system interactions
- Use real simulation environment
- Verify deterministic behavior
- Test complete workflows

#### Performance Tests
- Benchmark critical paths
- Verify performance requirements
- Detect regressions
- Profile memory usage

### Test Organization

```rust
// Unit tests in same file
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_unit_functionality() {
        // Test implementation
    }
}

// Integration tests in tests/ directory
// tests/integration_test.rs
use oldtimes_core::*;

#[test]
fn test_full_simulation() {
    // Integration test
}
```

### Deterministic Testing

All simulation tests must be deterministic:

```rust
#[test]
fn test_deterministic_behavior() {
    let mut sim1 = SimulationApp::new();
    let mut sim2 = SimulationApp::new();
    
    // Same inputs
    sim1.initialize_demo();
    sim2.initialize_demo();
    
    // Same operations
    sim1.run_ticks(100);
    sim2.run_ticks(100);
    
    // Same results
    assert_eq!(sim1.calculate_state_hash(), sim2.calculate_state_hash());
}
```

## Documentation Guidelines

### Code Documentation

- Document all public APIs
- Include examples for complex functions
- Explain non-obvious behavior
- Keep documentation up-to-date

```rust
/// Calculates the optimal production ratios for a target output.
/// 
/// # Arguments
/// * `target_item` - The item to produce
/// * `target_rate` - Desired production rate per second
/// 
/// # Returns
/// A map of recipe IDs to their required production rates
/// 
/// # Example
/// ```
/// let ratios = analyzer.find_production_ratios("bread", 10.0)?;
/// assert!(ratios.contains_key("bake_bread"));
/// ```
pub fn find_production_ratios(&self, target_item: &str, target_rate: f32) -> Result<HashMap<String, f32>> {
    // Implementation
}
```

### User Documentation

- Update README.md for user-facing changes
- Add examples to DATA_FORMATS.md for new data types
- Update ARCHITECTURE.md for structural changes
- Include screenshots for UI changes

## Performance Guidelines

### Optimization Priorities

1. **Correctness first**: Never sacrifice correctness for performance
2. **Profile before optimizing**: Use data to guide optimization
3. **Hot path focus**: Optimize systems that run every tick
4. **Memory efficiency**: Minimize allocations in critical paths

### Performance Requirements

- Tick time: ≤5ms for standard scenarios
- Memory: Stable usage without leaks
- Startup: ≤2 seconds for demo map
- Determinism: No performance-dependent behavior

### Profiling

```rust
// Use the profiling feature for development
#[cfg(feature = "profiling")]
let _span = info_span!("system_name").entered();
```

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes

### Release Checklist

- [ ] All tests pass
- [ ] Performance benchmarks meet requirements
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version numbers bumped
- [ ] Release notes prepared

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn
- Celebrate contributions

### Communication

- Use GitHub issues for bug reports and feature requests
- Use discussions for questions and ideas
- Be clear and specific in communications
- Provide context and examples

### Getting Help

- Check existing issues and documentation first
- Provide minimal reproducible examples
- Include relevant system information
- Be patient and respectful

## Recognition

Contributors are recognized in:
- Git commit history
- Release notes
- Contributors section (planned)
- Special thanks for significant contributions

Thank you for contributing to Old Times!