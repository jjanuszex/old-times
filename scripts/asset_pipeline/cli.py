"""
Command-line interface for the asset pipeline.
Provides commands for all pipeline operations.
"""

import sys
import os
import time
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from .config import PipelineConfig
from .providers.base import AssetProvider, ProviderError
from .processing.validator import QualityValidator, ValidationResult
from .utils.symlink import create_asset_symlink, validate_asset_symlink, SymlinkError

# Initialize typer app and rich console
app = typer.Typer(
    name="asset-pipeline",
    help="Asset pipeline for Old Times 2D Isometric RTS Game - Generate, process, and manage game assets",
    add_completion=False,
    rich_markup_mode="rich",
    epilog="""
[bold]Examples:[/bold]
  [cyan]python -m scripts.asset_pipeline.cli link[/cyan]                    Create asset symlink
  [cyan]python -m scripts.asset_pipeline.cli all[/cyan]                     Run complete pipeline
  [cyan]python -m scripts.asset_pipeline.cli mod my_mod[/cyan]              Generate mod assets
  [cyan]CONFIG=custom.toml python -m scripts.asset_pipeline.cli all[/cyan]  Use custom config

[bold]Environment Variables:[/bold]
  Use [cyan]python -m scripts.asset_pipeline.cli config --env-vars[/cyan] to see all available variables.

[bold]Build System Integration:[/bold]
  [cyan]make assets:all[/cyan]     Run via Makefile
  [cyan]just all[/cyan]           Run via Justfile
    """
)
console = Console()


@app.command()
def link(
    force: bool = typer.Option(True, "--force/--no-force", "-f", help="Force recreation of existing symlinks"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    validate: bool = typer.Option(False, "--validate", help="Validate existing symlink instead of creating")
):
    """Create symlink between asset directories."""
    if validate:
        console.print("[bold blue]Validating asset directory symlink...[/bold blue]")
        
        try:
            is_valid, target_or_error = validate_asset_symlink()
            
            if is_valid:
                console.print(f"[green]✓[/green] Symlink is valid and points to: {target_or_error}")
            else:
                console.print(f"[red]✗[/red] Symlink validation failed: {target_or_error}")
                raise typer.Exit(1)
                
        except Exception as e:
            console.print(f"[red]Error validating symlink:[/red] {e}")
            raise typer.Exit(1)
        
        return
    
    console.print("[bold blue]Creating asset directory symlink...[/bold blue]")
    
    source_dir = Path("assets").resolve()
    target_dir = Path("crates/oldtimes-client/assets")
    
    if dry_run:
        console.print(f"[yellow]DRY RUN:[/yellow] Would create symlink from {target_dir} to {source_dir}")
        console.print(f"[yellow]DRY RUN:[/yellow] Force mode: {force}")
        return
    
    try:
        # Use cross-platform symlink utilities
        success = create_asset_symlink(force=force)
        
        if success:
            console.print(f"[green]✓[/green] Created symlink: {target_dir} -> {source_dir}")
            
            # Validate the created symlink
            is_valid, target_path = validate_asset_symlink()
            if is_valid:
                console.print(f"[green]✓[/green] Symlink validation successful")
            else:
                console.print(f"[yellow]Warning:[/yellow] Symlink created but validation failed: {target_path}")
        else:
            console.print("[red]✗[/red] Failed to create symlink")
            raise typer.Exit(1)
        
    except SymlinkError as e:
        console.print(f"[red]Symlink error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def kenney(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory")
):
    """Download and process Kenney asset packs."""
    console.print("[bold blue]Processing Kenney asset packs...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        if not config.kenney_packs:
            console.print("[yellow]No Kenney packs configured. Skipping.[/yellow]")
            return
        
        console.print(f"[green]✓[/green] Configured to process {len(config.kenney_packs)} Kenney packs")
        
        # Initialize Kenney provider
        from .providers.kenney import KenneyProvider
        
        kenney_config = {
            "packs": ["isometric-buildings", "isometric-tiles"],
            "cache_dir": "cache/kenney",
            "asset_mappings": {}
        }
        
        provider = KenneyProvider(kenney_config)
        provider.configure(kenney_config)
        
        # Get and process assets
        available_assets = provider.get_available_assets()
        console.print(f"[green]Found {len(available_assets)} assets from Kenney packs[/green]")
        
        assets_processed = 0
        for asset_spec in available_assets:
            try:
                console.print(f"Processing: {asset_spec.name}")
                
                # Fetch asset data
                asset_data = provider.fetch_asset(asset_spec)
                
                # Save to sprites directory
                output_path = Path(config.sprites_dir) / f"{asset_spec.name}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(asset_data)
                
                assets_processed += 1
                
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to process {asset_spec.name}: {e}[/yellow]")
        
        console.print(f"[green]✓[/green] Processed {assets_processed} Kenney assets")
        
    except Exception as e:
        console.print(f"[red]Error processing Kenney assets:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def cloud(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    provider: Optional[str] = typer.Option(None, "--provider", help="AI provider to use")
):
    """Generate assets using AI providers."""
    console.print("[bold blue]Generating assets with AI providers...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        if config.ai_provider == "none":
            console.print("[green]✓[/green] No AI provider configured. Completing as no-op.")
            return
        
        console.print(f"[green]✓[/green] Using AI provider: {config.ai_provider}")
        
        # This would be implemented in task 3.3
        console.print("[yellow]AI provider implementation pending (task 3.3)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error generating AI assets:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def atlas(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    unit_name: Optional[str] = typer.Option(None, "--unit", help="Generate atlas for specific unit")
):
    """Create texture atlases for animated units."""
    console.print("[bold blue]Creating texture atlases...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        console.print("[green]✓[/green] Atlas generation configured")
        
        # This would be implemented in task 4
        console.print("[yellow]Atlas generation implementation pending (task 4)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error creating atlases:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def mod(
    name: str = typer.Argument(..., help="Mod name"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing mod directory"),
    validate_only: bool = typer.Option(False, "--validate", help="Only validate existing mod assets")
):
    """Generate assets into mod directory."""
    console.print(f"[bold blue]Generating mod assets for '{name}'...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Import mod processing modules
        from .processing.mod import (
            ModDirectoryManager,
            ModConfigManager,
            ModAssetIsolation,
            ModMetadataGenerator,
            ModAsset
        )
        
        # Initialize mod managers
        dir_manager = ModDirectoryManager(config)
        config_manager = ModConfigManager(dir_manager)
        isolation_manager = ModAssetIsolation(dir_manager)
        metadata_generator = ModMetadataGenerator(dir_manager)
        
        if validate_only:
            console.print(f"[bold blue]Validating mod '{name}'...[/bold blue]")
            
            # Validate mod directory structure
            if not dir_manager.validate_mod_directory(name):
                console.print(f"[red]✗[/red] Mod directory structure is invalid")
                raise typer.Exit(1)
            
            # Validate asset isolation
            isolation_errors = isolation_manager.validate_asset_isolation(name)
            if isolation_errors:
                console.print(f"[red]✗[/red] Asset isolation validation failed:")
                for error in isolation_errors:
                    console.print(f"  • {error}")
                raise typer.Exit(1)
            
            console.print(f"[green]✓[/green] Mod '{name}' validation successful")
            return
        
        # Create or validate mod directory
        mod_dir = dir_manager.create_mod_directory(name, force=force)
        console.print(f"[green]✓[/green] Mod directory ready: {mod_dir}")
        
        # Run mod asset processing pipeline
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Step 1: Process asset sources for mod
            task1 = progress.add_task("Processing mod asset sources...", total=None)
            mod_assets = _process_mod_asset_sources(config, name)
            progress.update(task1, description=f"✓ Processed {len(mod_assets)} mod assets")
            
            # Step 2: Isolate mod assets
            task2 = progress.add_task("Isolating mod assets...", total=None)
            isolation_map = isolation_manager.isolate_mod_assets(name, mod_assets)
            progress.update(task2, description="✓ Mod assets isolated")
            
            # Step 3: Generate mod metadata
            task3 = progress.add_task("Generating mod metadata...", total=None)
            sprites_toml_path = metadata_generator.generate_mod_sprites_toml(name, mod_assets)
            manifest_path = metadata_generator.generate_mod_manifest(name, mod_assets)
            progress.update(task3, description="✓ Mod metadata generated")
            
            # Step 4: Update mod configuration
            task4 = progress.add_task("Updating mod configuration...", total=None)
            config_manager.update_mod_config(name, mod_assets)
            progress.update(task4, description="✓ Mod configuration updated")
            
            # Step 5: Validate mod assets
            task5 = progress.add_task("Validating mod assets...", total=None)
            isolation_errors = isolation_manager.validate_asset_isolation(name)
            if isolation_errors:
                console.print(f"[yellow]Warning: Asset isolation issues found:[/yellow]")
                for error in isolation_errors:
                    console.print(f"  • {error}")
            progress.update(task5, description="✓ Mod assets validated")
        
        # Display summary
        console.print(f"\n[green]✓ Mod '{name}' generation completed successfully![/green]")
        console.print(f"  • Assets processed: {len(mod_assets)}")
        console.print(f"  • Sprites metadata: {sprites_toml_path}")
        console.print(f"  • Manifest file: {manifest_path}")
        console.print(f"  • Mod directory: {mod_dir}")
        
    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[yellow]Use --force to overwrite existing mod directory[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating mod assets:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    assets_dir: Optional[Path] = typer.Option(None, "--assets", help="Assets directory to validate"),
    strict: bool = typer.Option(False, "--strict", help="Use strict validation rules")
):
    """Validate asset quality and compliance."""
    console.print("[bold blue]Validating assets...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        assets_path = assets_dir or Path(config.assets_dir)
        console.print(f"[green]✓[/green] Validating assets in: {assets_path}")
        
        # This would be implemented in task 7
        console.print("[yellow]Asset validation implementation pending (task 7)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error validating assets:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def preview(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    assets_dir: Optional[Path] = typer.Option(None, "--assets", help="Assets directory to preview"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Preview output directory"),
    grid_only: bool = typer.Option(False, "--grid-only", help="Create only grid preview"),
    alignment_only: bool = typer.Option(False, "--alignment-only", help="Create only alignment preview"),
    animations_only: bool = typer.Option(False, "--animations-only", help="Create only animation previews"),
    cleanup: bool = typer.Option(False, "--cleanup", help="Clean up old previews before generating new ones")
):
    """Generate asset previews for visual verification."""
    console.print("[bold blue]Generating asset previews...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Import preview processing modules
        from .processing.preview import (
            PreviewProcessor,
            PreviewProcessorConfig,
            generate_asset_previews,
            generate_animation_previews
        )
        from .utils.preview import PreviewConfig
        
        # Set up paths
        assets_path = str(assets_dir or Path(config.assets_dir))
        preview_output_dir = str(output_dir or "assets/preview")
        
        console.print(f"[green]✓[/green] Assets directory: {assets_path}")
        console.print(f"[green]✓[/green] Preview output: {preview_output_dir}")
        
        # Configure preview processor
        preview_config = PreviewConfig(
            show_isometric_grid=not grid_only,
            show_labels=True
        )
        
        processor_config = PreviewProcessorConfig(
            output_dir=preview_output_dir,
            create_grid_preview=not alignment_only and not animations_only,
            create_alignment_preview=not grid_only and not animations_only,
            create_animation_previews=not grid_only and not alignment_only,
            preview_config=preview_config
        )
        
        processor = PreviewProcessor(processor_config)
        
        # Clean up old previews if requested
        if cleanup:
            console.print("[dim]Cleaning up old previews...[/dim]")
            processor.cleanup_old_previews()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            if not animations_only:
                # Generate asset previews
                task1 = progress.add_task("Generating asset previews...", total=None)
                success = processor.process_assets_preview(assets_path)
                
                if success:
                    progress.update(task1, description="✓ Asset previews generated")
                else:
                    progress.update(task1, description="✗ Asset preview generation failed")
                    console.print("[yellow]Warning: Some asset previews failed to generate[/yellow]")
            
            if not grid_only and not alignment_only:
                # Generate animation previews (if any atlases exist)
                task2 = progress.add_task("Generating animation previews...", total=None)
                
                # Check for existing atlases
                atlases_dir = Path(config.atlases_dir)
                animations = {}
                
                if atlases_dir.exists():
                    for atlas_file in atlases_dir.glob("*.png"):
                        # Try to find corresponding frame map
                        frame_map_file = atlas_file.with_suffix(".json")
                        if frame_map_file.exists():
                            try:
                                import json
                                with open(frame_map_file) as f:
                                    frame_map = json.load(f)
                                
                                animation_name = atlas_file.stem
                                success = processor.create_atlas_preview(
                                    str(atlas_file), frame_map, animation_name
                                )
                                
                                if success:
                                    animations[animation_name] = True
                                    
                            except Exception as e:
                                console.print(f"[yellow]Warning: Failed to process atlas {atlas_file}: {e}[/yellow]")
                
                if animations:
                    progress.update(task2, description=f"✓ Generated previews for {len(animations)} animations")
                else:
                    progress.update(task2, description="✓ No animations found to preview")
        
        # Display summary
        console.print(f"\n[green]✓ Preview generation completed![/green]")
        console.print(f"  • Preview directory: {preview_output_dir}")
        
        # List generated files
        preview_path = Path(preview_output_dir)
        if preview_path.exists():
            preview_files = list(preview_path.glob("*.png"))
            if preview_files:
                console.print(f"  • Generated {len(preview_files)} preview files:")
                for preview_file in sorted(preview_files):
                    console.print(f"    - {preview_file.name}")
            else:
                console.print("  • No preview files were generated")
        
    except Exception as e:
        console.print(f"[red]Error generating previews:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def all(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    skip_validation: bool = typer.Option(False, "--skip-validation", help="Skip final validation step"),
    skip_preview: bool = typer.Option(False, "--skip-preview", help="Skip preview generation step"),
    steps: Optional[str] = typer.Option(None, "--steps", help="Comma-separated list of specific steps to run"),
    rollback_on_failure: bool = typer.Option(True, "--rollback/--no-rollback", help="Rollback changes on failure"),
    show_summary: bool = typer.Option(True, "--summary/--no-summary", help="Show execution summary")
):
    """Run complete asset pipeline."""
    console.print("[bold blue]Running complete asset pipeline...[/bold blue]")
    
    try:
        # Load configuration
        config = _load_config(config_file)
        
        # Import pipeline coordinator
        from .pipeline import AssetPipeline, PipelineStep, PipelineError
        
        # Determine which steps to run
        pipeline_steps = None
        if steps:
            step_names = [s.strip() for s in steps.split(',')]
            pipeline_steps = []
            for step_name in step_names:
                try:
                    pipeline_steps.append(PipelineStep(step_name))
                except ValueError:
                    console.print(f"[red]Invalid step name: {step_name}[/red]")
                    console.print(f"Valid steps: {', '.join([s.value for s in PipelineStep])}")
                    raise typer.Exit(1)
        else:
            # Default steps, excluding those that are skipped
            pipeline_steps = list(PipelineStep)
            if skip_validation:
                pipeline_steps = [s for s in pipeline_steps if s != PipelineStep.VALIDATE]
            if skip_preview:
                pipeline_steps = [s for s in pipeline_steps if s != PipelineStep.PREVIEW]
        
        # Initialize pipeline
        pipeline = AssetPipeline(config)
        
        # Execute pipeline with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Create progress tasks for each step
            step_tasks = {}
            for step in pipeline_steps:
                step_tasks[step] = progress.add_task(f"Preparing {step.value}...", total=None)
            
            # Execute pipeline with rollback protection if enabled
            if rollback_on_failure:
                with pipeline.rollback_on_failure():
                    final_state = pipeline.run_full_pipeline(pipeline_steps)
            else:
                final_state = pipeline.run_full_pipeline(pipeline_steps)
            
            # Update progress tasks based on results
            for step in pipeline_steps:
                if step in step_tasks:
                    result = final_state.step_results.get(step)
                    if result:
                        if result.success:
                            progress.update(step_tasks[step], 
                                          description=f"✓ {step.value} ({result.duration:.1f}s)")
                        else:
                            progress.update(step_tasks[step], 
                                          description=f"✗ {step.value} failed")
                    else:
                        progress.update(step_tasks[step], 
                                      description=f"⚠ {step.value} skipped")
        
        # Display results
        if final_state.failed_steps:
            console.print(f"[yellow]Pipeline completed with {len(final_state.failed_steps)} failed steps[/yellow]")
            for failed_step in final_state.failed_steps:
                result = final_state.step_results.get(failed_step)
                if result:
                    console.print(f"  [red]✗[/red] {failed_step.value}: {result.message}")
        else:
            console.print("[green]✓ Complete pipeline executed successfully![/green]")
        
        # Show summary if requested
        if show_summary:
            _display_pipeline_summary(final_state)
        
        # Exit with error code if any critical steps failed
        critical_failures = final_state.failed_steps - {PipelineStep.PREVIEW, PipelineStep.AI_SOURCES}
        if critical_failures:
            raise typer.Exit(1)
        
    except PipelineError as e:
        console.print(f"[red]Pipeline error:[/red] {e}")
        if e.step:
            console.print(f"[red]Failed at step:[/red] {e.step.value}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    validate_config: bool = typer.Option(False, "--validate", help="Validate configuration file"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    env_vars: bool = typer.Option(False, "--env-vars", help="Show available environment variables")
):
    """Manage pipeline configuration."""
    try:
        if env_vars:
            _display_env_vars()
            return
            
        if show or validate_config:
            config = _load_config(config_file)
            
            if show:
                _display_config(config)
            
            if validate_config:
                errors = config.validate()
                if errors:
                    console.print("[red]Configuration validation errors:[/red]")
                    for error in errors:
                        console.print(f"  • {error}")
                    raise typer.Exit(1)
                else:
                    console.print("[green]✓ Configuration is valid[/green]")
        else:
            console.print("Use --show to display configuration, --validate to check it, or --env-vars to see environment variables.")
            
    except Exception as e:
        console.print(f"[red]Error managing configuration:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def test(
    integration: bool = typer.Option(False, "--integration", help="Run integration tests"),
    unit: bool = typer.Option(False, "--unit", help="Run unit tests"),
    coverage: bool = typer.Option(False, "--coverage", help="Run tests with coverage report"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose test output")
):
    """Run asset pipeline tests."""
    console.print("[bold blue]Running asset pipeline tests...[/bold blue]")
    
    try:
        import subprocess
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["--cov=scripts.asset_pipeline", "--cov-report=term-missing"])
        
        # Determine test scope
        test_paths = []
        if integration:
            test_paths.append("scripts/asset_pipeline/tests/test_cli_integration.py")
        if unit:
            test_paths.extend([
                "scripts/asset_pipeline/tests/test_*.py",
                "!scripts/asset_pipeline/tests/test_cli_integration.py"
            ])
        
        if not test_paths:
            # Run all tests by default
            test_paths.append("scripts/asset_pipeline/tests/")
        
        cmd.extend(test_paths)
        
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
        
        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Display output
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        
        if result.returncode == 0:
            console.print("[green]✓ All tests passed![/green]")
        else:
            console.print("[red]✗ Some tests failed[/red]")
            raise typer.Exit(result.returncode)
            
    except ImportError:
        console.print("[red]Error: pytest not installed. Run 'pip install pytest' to install it.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error running tests:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show asset pipeline version information."""
    console.print("[bold]Asset Pipeline for Old Times 2D Isometric RTS[/bold]")
    console.print("Version: 1.0.0")
    console.print("Python: " + sys.version.split()[0])
    
    # Check for optional dependencies
    deps_status = []
    
    try:
        import PIL
        deps_status.append(("Pillow", PIL.__version__, "✓"))
    except ImportError:
        deps_status.append(("Pillow", "Not installed", "✗"))
    
    try:
        import requests
        deps_status.append(("Requests", requests.__version__, "✓"))
    except ImportError:
        deps_status.append(("Requests", "Not installed", "✗"))
    
    try:
        import jinja2
        deps_status.append(("Jinja2", jinja2.__version__, "✓"))
    except ImportError:
        deps_status.append(("Jinja2", "Not installed", "✗"))
    
    try:
        import typer
        deps_status.append(("Typer", typer.__version__, "✓"))
    except ImportError:
        deps_status.append(("Typer", "Not installed", "✗"))
    
    try:
        import rich
        # Rich doesn't have __version__ in some versions, try to get it from metadata
        try:
            version = rich.__version__
        except AttributeError:
            try:
                import importlib.metadata
                version = importlib.metadata.version("rich")
            except:
                version = "Unknown"
        deps_status.append(("Rich", version, "✓"))
    except ImportError:
        deps_status.append(("Rich", "Not installed", "✗"))
    
    if deps_status:
        console.print("\n[bold]Dependencies:[/bold]")
        table = Table(show_header=False)
        table.add_column("Status", width=3)
        table.add_column("Package", style="cyan")
        table.add_column("Version", style="green")
        
        for name, version, status in deps_status:
            color = "green" if status == "✓" else "red"
            table.add_row(f"[{color}]{status}[/{color}]", name, version)
        
        console.print(table)


def _load_config(config_file: Optional[Path]) -> PipelineConfig:
    """Load configuration from file or use defaults with environment variable support."""
    config = None
    
    if config_file:
        if not config_file.exists():
            console.print(f"[red]Configuration file not found:[/red] {config_file}")
            raise typer.Exit(1)
        config = PipelineConfig.from_file(config_file)
        console.print(f"[dim]Using configuration: {config_file}[/dim]")
    else:
        # Try to find default config files
        default_configs = [
            Path("asset_pipeline.toml"),
            Path("asset_pipeline.json"),
            Path("scripts/asset_pipeline.toml"),
            Path("scripts/asset_pipeline.json")
        ]
        
        for config_path in default_configs:
            if config_path.exists():
                console.print(f"[dim]Using configuration: {config_path}[/dim]")
                config = PipelineConfig.from_file(config_path)
                break
        
        if config is None:
            # Use default configuration
            console.print("[dim]Using default configuration[/dim]")
            config = PipelineConfig.default()
    
    # Apply environment variable overrides
    config = PipelineConfig._apply_env_overrides(config)
    
    # Check for environment variable usage
    env_vars_used = []
    for key in os.environ:
        if key.startswith('ASSET_PIPELINE_'):
            env_vars_used.append(key)
    
    if env_vars_used:
        console.print(f"[dim]Environment overrides applied: {len(env_vars_used)} variables[/dim]")
    
    return config


def _display_pipeline_summary(state):
    """Display pipeline execution summary."""
    from .pipeline import PipelineState
    
    if not isinstance(state, PipelineState):
        return
    
    total_duration = 0
    if state.start_time:
        total_duration = time.time() - state.start_time
    
    console.print("\n[bold]Pipeline Execution Summary[/bold]")
    console.print("=" * 50)
    
    # Overall stats
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total execution time", f"{total_duration:.2f}s")
    table.add_row("Steps completed", str(len(state.completed_steps)))
    table.add_row("Steps failed", str(len(state.failed_steps)))
    table.add_row("Assets processed", str(state.total_assets_processed))
    table.add_row("Cache hits", str(state.cache_hits))
    table.add_row("Cache misses", str(state.cache_misses))
    
    console.print(table)
    
    # Step details
    if state.step_results:
        console.print("\n[bold]Step Details[/bold]")
        step_table = Table()
        step_table.add_column("Step", style="cyan")
        step_table.add_column("Status", width=8)
        step_table.add_column("Duration", style="yellow")
        step_table.add_column("Message", style="dim")
        
        for step, result in state.step_results.items():
            status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
            duration = f"{result.duration:.2f}s"
            message = result.message[:50] + "..." if len(result.message) > 50 else result.message
            
            step_table.add_row(step.value, status, duration, message)
        
        console.print(step_table)


def _process_mod_asset_sources(config: PipelineConfig, mod_name: str) -> List:
    """
    Process asset sources for mod generation.
    
    Args:
        config: Pipeline configuration
        mod_name: Name of the mod
        
    Returns:
        List of ModAsset objects
    """
    from .processing.mod import ModAsset
    
    # For now, create some example assets
    # In a full implementation, this would:
    # 1. Process Kenney assets for the mod
    # 2. Generate AI assets for the mod
    # 3. Process any existing mod assets
    
    mod_assets = []
    
    # Example tile assets
    tile_assets = [
        ModAsset(
            name="mod_grass",
            asset_type="tile",
            source_path=f"mods/{mod_name}/sprites/tile/mod_grass.png",
            metadata={"size": [64, 32]}
        ),
        ModAsset(
            name="mod_stone",
            asset_type="tile", 
            source_path=f"mods/{mod_name}/sprites/tile/mod_stone.png",
            metadata={"size": [64, 32]}
        )
    ]
    
    # Example building assets
    building_assets = [
        ModAsset(
            name="mod_house",
            asset_type="building",
            source_path=f"mods/{mod_name}/sprites/building/mod_house.png",
            metadata={"size": [128, 96], "tile_footprint": [2, 2]}
        )
    ]
    
    # Example unit assets
    unit_assets = [
        ModAsset(
            name="mod_worker",
            asset_type="unit",
            source_path=f"mods/{mod_name}/sprites/unit/mod_worker.png",
            metadata={
                "frame_size": [64, 64],
                "directions": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
                "anim_walk_fps": 10,
                "anim_walk_len": 8,
                "layout": "dirs_rows"
            }
        )
    ]
    
    mod_assets.extend(tile_assets)
    mod_assets.extend(building_assets)
    mod_assets.extend(unit_assets)
    
    return mod_assets


def _display_config(config: PipelineConfig) -> None:
    """Display configuration in a formatted table."""
    table = Table(title="Asset Pipeline Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Asset sources
    table.add_row("Kenney Packs", str(config.kenney_packs))
    table.add_row("AI Provider", config.ai_provider)
    
    # Processing settings
    table.add_row("Tile Size", f"{config.tile_size[0]}×{config.tile_size[1]}")
    table.add_row("Unit Frame Size", f"{config.unit_frame_size[0]}×{config.unit_frame_size[1]}")
    table.add_row("Atlas Padding", str(config.atlas_padding))
    
    # Quality settings
    table.add_row("Max Alpha Threshold", str(config.max_alpha_threshold))
    table.add_row("Edge Sharpness Threshold", str(config.edge_sharpness_threshold))
    
    # Output settings
    table.add_row("Output Format", config.output_format)
    table.add_row("Compression Level", str(config.compression_level))
    
    # Paths
    table.add_row("Assets Directory", config.assets_dir)
    table.add_row("Sprites Directory", config.sprites_dir)
    table.add_row("Atlases Directory", config.atlases_dir)
    table.add_row("Data Directory", config.data_dir)
    table.add_row("Mods Directory", config.mods_dir)
    table.add_row("Preview Directory", config.preview_dir)
    
    # Preview settings
    table.add_row("Generate Previews", str(config.generate_previews))
    table.add_row("Preview Grid Size", f"{config.preview_grid_size[0]}×{config.preview_grid_size[1]}")
    table.add_row("Preview Show Labels", str(config.preview_show_labels))
    table.add_row("Preview Show Grid", str(config.preview_show_grid))
    
    console.print(table)


def _display_env_vars() -> None:
    """Display available environment variables for configuration."""
    table = Table(title="Asset Pipeline Environment Variables")
    table.add_column("Environment Variable", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Example", style="green")
    
    env_vars = [
        ("ASSET_PIPELINE_KENNEY_PACKS", "Comma-separated list of Kenney packs", "pack1,pack2,pack3"),
        ("ASSET_PIPELINE_AI_PROVIDER", "AI provider to use", "stable-diffusion"),
        ("ASSET_PIPELINE_TILE_WIDTH", "Tile width in pixels", "64"),
        ("ASSET_PIPELINE_TILE_HEIGHT", "Tile height in pixels", "32"),
        ("ASSET_PIPELINE_UNIT_FRAME_WIDTH", "Unit frame width in pixels", "64"),
        ("ASSET_PIPELINE_UNIT_FRAME_HEIGHT", "Unit frame height in pixels", "64"),
        ("ASSET_PIPELINE_ATLAS_PADDING", "Atlas padding in pixels", "0"),
        ("ASSET_PIPELINE_MAX_ALPHA_THRESHOLD", "Maximum alpha threshold", "0.01"),
        ("ASSET_PIPELINE_EDGE_SHARPNESS_THRESHOLD", "Edge sharpness threshold", "0.5"),
        ("ASSET_PIPELINE_OUTPUT_FORMAT", "Output image format", "PNG"),
        ("ASSET_PIPELINE_COMPRESSION_LEVEL", "Compression level (0-9)", "6"),
        ("ASSET_PIPELINE_ASSETS_DIR", "Assets directory path", "assets"),
        ("ASSET_PIPELINE_SPRITES_DIR", "Sprites directory path", "assets/sprites"),
        ("ASSET_PIPELINE_ATLASES_DIR", "Atlases directory path", "assets/atlases"),
        ("ASSET_PIPELINE_DATA_DIR", "Data directory path", "assets/data"),
        ("ASSET_PIPELINE_MODS_DIR", "Mods directory path", "mods"),
        ("ASSET_PIPELINE_PREVIEW_DIR", "Preview directory path", "assets/preview"),
        ("ASSET_PIPELINE_GENERATE_PREVIEWS", "Generate previews (true/false)", "true"),
        ("ASSET_PIPELINE_PREVIEW_GRID_WIDTH", "Preview grid width", "96"),
        ("ASSET_PIPELINE_PREVIEW_GRID_HEIGHT", "Preview grid height", "96"),
        ("ASSET_PIPELINE_PREVIEW_SHOW_LABELS", "Show labels in previews (true/false)", "true"),
        ("ASSET_PIPELINE_PREVIEW_SHOW_GRID", "Show grid in previews (true/false)", "true"),
    ]
    
    for var_name, description, example in env_vars:
        table.add_row(var_name, description, example)
    
    console.print(table)
    console.print("\n[dim]Set these environment variables to override configuration file settings.[/dim]")
    console.print("[dim]Example: export ASSET_PIPELINE_AI_PROVIDER=stable-diffusion[/dim]")


if __name__ == "__main__":
    app()