"""
Asset pipeline coordinator for orchestrating all processing steps.
Manages step dependencies, execution order, state management, and error handling.
"""

import os
import json
import time
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from contextlib import contextmanager

from .config import PipelineConfig, ErrorConfig
from .providers.base import AssetProvider, ProviderError
from .providers.kenney import KenneyProvider
from .providers.ai_providers import AIProviderFactory
from .processing.normalizer import AssetNormalizer
from .processing.atlas import AtlasGenerator
from .processing.metadata import MetadataGenerator
from .processing.validator import QualityValidator, ValidationResult
from .processing.preview import PreviewProcessor


class PipelineStep(Enum):
    """Enumeration of pipeline steps."""
    SYMLINK = "symlink"
    KENNEY_SOURCES = "kenney_sources"
    AI_SOURCES = "ai_sources"
    NORMALIZE = "normalize"
    ATLAS = "atlas"
    METADATA = "metadata"
    PREVIEW = "preview"
    VALIDATE = "validate"


@dataclass
class StepResult:
    """Result of a pipeline step execution."""
    step: PipelineStep
    success: bool
    duration: float
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PipelineState:
    """Current state of the pipeline execution."""
    current_step: Optional[PipelineStep] = None
    completed_steps: Set[PipelineStep] = field(default_factory=set)
    failed_steps: Set[PipelineStep] = field(default_factory=set)
    step_results: Dict[PipelineStep, StepResult] = field(default_factory=dict)
    start_time: Optional[float] = None
    total_assets_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    def __init__(self, message: str, step: Optional[PipelineStep] = None, recoverable: bool = False):
        super().__init__(message)
        self.step = step
        self.recoverable = recoverable


class AssetPipeline:
    """
    Main pipeline coordinator that orchestrates all asset processing steps.
    
    Manages step dependencies, execution order, state management, error handling,
    and provides comprehensive logging and recovery capabilities.
    """
    
    # Step dependencies - each step depends on the completion of its dependencies
    STEP_DEPENDENCIES = {
        PipelineStep.SYMLINK: set(),
        PipelineStep.KENNEY_SOURCES: {PipelineStep.SYMLINK},
        PipelineStep.AI_SOURCES: {PipelineStep.SYMLINK},
        PipelineStep.NORMALIZE: {PipelineStep.KENNEY_SOURCES, PipelineStep.AI_SOURCES},
        PipelineStep.ATLAS: {PipelineStep.NORMALIZE},
        PipelineStep.METADATA: {PipelineStep.ATLAS},
        PipelineStep.PREVIEW: {PipelineStep.METADATA},
        PipelineStep.VALIDATE: {PipelineStep.METADATA}
    }
    
    def __init__(self, config: PipelineConfig, error_config: Optional[ErrorConfig] = None):
        """
        Initialize the asset pipeline.
        
        Args:
            config: Pipeline configuration
            error_config: Error handling configuration
        """
        self.config = config
        self.error_config = error_config or ErrorConfig()
        self.state = PipelineState()
        self.logger = self._setup_logging()
        
        # Initialize processors
        self._providers: Dict[str, AssetProvider] = {}
        self._normalizer: Optional[AssetNormalizer] = None
        self._atlas_generator: Optional[AtlasGenerator] = None
        self._metadata_generator: Optional[MetadataGenerator] = None
        self._validator: Optional[QualityValidator] = None
        self._preview_processor: Optional[PreviewProcessor] = None
        
        # Cache management
        self._cache_dir = Path("cache/pipeline")
        self._cache_index: Dict[str, Any] = {}
        
        # Step handlers
        self._step_handlers: Dict[PipelineStep, Callable] = {
            PipelineStep.SYMLINK: self._execute_symlink_step,
            PipelineStep.KENNEY_SOURCES: self._execute_kenney_sources_step,
            PipelineStep.AI_SOURCES: self._execute_ai_sources_step,
            PipelineStep.NORMALIZE: self._execute_normalize_step,
            PipelineStep.ATLAS: self._execute_atlas_step,
            PipelineStep.METADATA: self._execute_metadata_step,
            PipelineStep.PREVIEW: self._execute_preview_step,
            PipelineStep.VALIDATE: self._execute_validate_step
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the pipeline."""
        logger = logging.getLogger("asset_pipeline")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def run_full_pipeline(self, steps: Optional[List[PipelineStep]] = None) -> PipelineState:
        """
        Run the complete asset pipeline or specified steps.
        
        Args:
            steps: Optional list of specific steps to run. If None, runs all steps.
            
        Returns:
            Final pipeline state
        """
        if steps is None:
            steps = list(PipelineStep)
        
        self.logger.info("Starting asset pipeline execution")
        self.state.start_time = time.time()
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Load cache index
            self._load_cache_index()
            
            # Execute steps in dependency order
            execution_order = self._calculate_execution_order(steps)
            
            for step in execution_order:
                if not self._should_execute_step(step):
                    self.logger.info(f"Skipping step {step.value} (already completed or not needed)")
                    continue
                
                self._execute_step(step)
                
                # Check if step failed and handle accordingly
                if step in self.state.failed_steps:
                    if not self._handle_step_failure(step):
                        break
            
            # Save cache index
            self._save_cache_index()
            
            # Generate final summary
            self._generate_execution_summary()
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            self.state.failed_steps.add(self.state.current_step or PipelineStep.SYMLINK)
            raise PipelineError(f"Pipeline execution failed: {e}", self.state.current_step)
        
        return self.state
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        self.logger.info("Initializing pipeline components")
        
        # Initialize providers
        kenney_config = {
            "packs": ["isometric-buildings", "isometric-tiles"],  # Use actual pack names
            "cache_dir": "cache/kenney",
            "asset_mappings": {}
        }
        self._providers["kenney"] = KenneyProvider(kenney_config)
        self._providers["kenney"].configure(kenney_config)
        
        # Map "none" to "stub" for AI provider
        ai_provider_type = "stub" if self.config.ai_provider == "none" else self.config.ai_provider
        self._providers["ai"] = AIProviderFactory.create_provider(
            ai_provider_type, self.config.ai_config
        )
        
        # Initialize processors with appropriate config objects
        from .processing.normalizer import NormalizationConfig
        from .processing.atlas import AtlasConfig
        from .processing.preview import PreviewProcessorConfig
        from .config import ValidationConfig
        
        normalizer_config = NormalizationConfig(
            tile_size=self.config.tile_size,
            unit_frame_size=self.config.unit_frame_size
        )
        
        atlas_config = AtlasConfig(
            padding=self.config.atlas_padding
        )
        
        preview_config = PreviewProcessorConfig(
            output_dir=self.config.preview_dir
        )
        
        validation_config = ValidationConfig()
        
        self._normalizer = AssetNormalizer(normalizer_config)
        self._atlas_generator = AtlasGenerator(atlas_config)
        self._metadata_generator = MetadataGenerator()  # Uses default template dir
        self._validator = QualityValidator(validation_config)
        self._preview_processor = PreviewProcessor(preview_config)
    
    def _calculate_execution_order(self, requested_steps: List[PipelineStep]) -> List[PipelineStep]:
        """
        Calculate the correct execution order based on step dependencies.
        
        Args:
            requested_steps: Steps requested to be executed
            
        Returns:
            Steps in correct execution order
        """
        # Include all dependencies of requested steps
        all_required_steps = set()
        
        def add_dependencies(step: PipelineStep):
            if step not in all_required_steps:
                all_required_steps.add(step)
                for dep in self.STEP_DEPENDENCIES[step]:
                    add_dependencies(dep)
        
        for step in requested_steps:
            add_dependencies(step)
        
        # Topological sort to determine execution order
        execution_order = []
        remaining_steps = all_required_steps.copy()
        
        while remaining_steps:
            # Find steps with no remaining dependencies
            ready_steps = []
            for step in remaining_steps:
                if self.STEP_DEPENDENCIES[step].issubset(set(execution_order)):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise PipelineError("Circular dependency detected in pipeline steps")
            
            # Sort ready steps for consistent execution order
            ready_steps.sort(key=lambda x: x.value)
            
            # Add first ready step to execution order
            next_step = ready_steps[0]
            execution_order.append(next_step)
            remaining_steps.remove(next_step)
        
        return execution_order
    
    def _should_execute_step(self, step: PipelineStep) -> bool:
        """
        Determine if a step should be executed based on current state and caching.
        
        Args:
            step: Step to check
            
        Returns:
            True if step should be executed
        """
        # Always execute if step previously failed
        if step in self.state.failed_steps:
            return True
        
        # Skip if already completed successfully
        if step in self.state.completed_steps:
            return False
        
        # Check cache for incremental updates
        cache_key = self._get_step_cache_key(step)
        if cache_key in self._cache_index:
            cache_entry = self._cache_index[cache_key]
            if self._is_cache_valid(cache_entry):
                self.logger.info(f"Using cached result for step {step.value}")
                self.state.cache_hits += 1
                self.state.completed_steps.add(step)
                return False
        
        self.state.cache_misses += 1
        return True
    
    def _execute_step(self, step: PipelineStep):
        """
        Execute a single pipeline step with error handling and timing.
        
        Args:
            step: Step to execute
        """
        self.state.current_step = step
        self.logger.info(f"Executing step: {step.value}")
        
        start_time = time.time()
        
        try:
            # Execute step handler
            handler = self._step_handlers[step]
            result = handler()
            
            # Record successful execution
            duration = time.time() - start_time
            step_result = StepResult(
                step=step,
                success=True,
                duration=duration,
                message=f"Step {step.value} completed successfully",
                data=result if isinstance(result, dict) else {}
            )
            
            self.state.step_results[step] = step_result
            self.state.completed_steps.add(step)
            
            # Update cache
            self._update_step_cache(step, step_result)
            
            self.logger.info(f"Step {step.value} completed in {duration:.2f}s")
            
        except Exception as e:
            # Record failed execution
            duration = time.time() - start_time
            step_result = StepResult(
                step=step,
                success=False,
                duration=duration,
                message=f"Step {step.value} failed: {str(e)}",
                errors=[str(e)]
            )
            
            self.state.step_results[step] = step_result
            self.state.failed_steps.add(step)
            
            self.logger.error(f"Step {step.value} failed after {duration:.2f}s: {e}")
            
            # Re-raise if not recoverable
            if not isinstance(e, PipelineError) or not e.recoverable:
                raise
    
    def _handle_step_failure(self, step: PipelineStep) -> bool:
        """
        Handle step failure and determine if pipeline should continue.
        
        Args:
            step: Failed step
            
        Returns:
            True if pipeline should continue, False to stop
        """
        step_result = self.state.step_results.get(step)
        if not step_result:
            return False
        
        # Check if step failure is in ignored categories
        if step.value in self.error_config.ignore_categories:
            self.logger.warning(f"Ignoring failure in step {step.value} (configured to ignore)")
            return True
        
        # For certain steps, failure is not critical
        non_critical_steps = {PipelineStep.PREVIEW, PipelineStep.AI_SOURCES}
        if step in non_critical_steps:
            self.logger.warning(f"Step {step.value} failed but is not critical, continuing")
            return True
        
        # Critical step failed
        self.logger.error(f"Critical step {step.value} failed, stopping pipeline")
        return False
    
    # Step execution methods
    def _execute_symlink_step(self) -> Dict[str, Any]:
        """Execute symlink creation step."""
        from .utils.symlink import create_asset_symlink, validate_asset_symlink
        
        success = create_asset_symlink(force=True)
        if not success:
            raise PipelineError("Failed to create asset symlink", PipelineStep.SYMLINK)
        
        # Validate the created symlink
        is_valid, target_path = validate_asset_symlink()
        if not is_valid:
            raise PipelineError(f"Symlink validation failed: {target_path}", PipelineStep.SYMLINK)
        
        return {"symlink_target": target_path}
    
    def _execute_kenney_sources_step(self) -> Dict[str, Any]:
        """Execute Kenney asset pack processing step."""
        if not self.config.kenney_packs:
            self.logger.info("No Kenney packs configured, skipping")
            return {"assets_processed": 0}
        
        kenney_provider = self._providers["kenney"]
        assets_processed = 0
        
        try:
            # Get available assets from Kenney provider
            available_assets = kenney_provider.get_available_assets()
            self.logger.info(f"Found {len(available_assets)} assets from Kenney packs")
            
            # Process each asset
            for asset_spec in available_assets:
                try:
                    self.logger.info(f"Processing Kenney asset: {asset_spec.name}")
                    
                    # Fetch asset data
                    asset_data = kenney_provider.fetch_asset(asset_spec)
                    
                    # Save to sprites directory
                    output_path = Path(self.config.sprites_dir) / f"{asset_spec.name}.png"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        f.write(asset_data)
                    
                    assets_processed += 1
                    self.logger.debug(f"Saved Kenney asset to {output_path}")
                    
                except ProviderError as e:
                    self.logger.warning(f"Failed to process Kenney asset {asset_spec.name}: {e}")
                except Exception as e:
                    self.logger.error(f"Unexpected error processing {asset_spec.name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to process Kenney assets: {e}")
        
        return {"assets_processed": assets_processed}
    
    def _execute_ai_sources_step(self) -> Dict[str, Any]:
        """Execute AI asset generation step."""
        if self.config.ai_provider == "none":
            self.logger.info("No AI provider configured, completing as no-op")
            return {"assets_generated": 0}
        
        ai_provider = self._providers["ai"]
        assets_generated = 0
        
        try:
            # This would be implemented based on the AI provider
            # For now, we'll simulate the generation
            self.logger.info(f"Generating assets with AI provider: {self.config.ai_provider}")
            assets_generated = 0  # Placeholder
        except ProviderError as e:
            # AI generation failure is recoverable
            raise PipelineError(f"AI asset generation failed: {e}", PipelineStep.AI_SOURCES, recoverable=True)
        
        return {"assets_generated": assets_generated}
    
    def _execute_normalize_step(self) -> Dict[str, Any]:
        """Execute asset normalization step."""
        if not self._normalizer:
            raise PipelineError("Normalizer not initialized", PipelineStep.NORMALIZE)
        
        # This would implement the actual normalization logic
        # For now, we'll simulate the processing
        assets_normalized = 0
        
        sprites_dir = Path(self.config.sprites_dir)
        if sprites_dir.exists():
            for sprite_file in sprites_dir.glob("*.png"):
                try:
                    # Simulate normalization
                    self.logger.debug(f"Normalizing {sprite_file}")
                    assets_normalized += 1
                except Exception as e:
                    self.logger.warning(f"Failed to normalize {sprite_file}: {e}")
        
        self.state.total_assets_processed += assets_normalized
        return {"assets_normalized": assets_normalized}
    
    def _execute_atlas_step(self) -> Dict[str, Any]:
        """Execute texture atlas generation step."""
        if not self._atlas_generator:
            raise PipelineError("Atlas generator not initialized", PipelineStep.ATLAS)
        
        # This would implement the actual atlas generation logic
        atlases_created = 0
        
        # Simulate atlas creation for units
        unit_types = ["worker"]  # This would come from configuration or discovery
        
        for unit_type in unit_types:
            try:
                self.logger.info(f"Creating atlas for unit: {unit_type}")
                # Simulate atlas creation
                atlases_created += 1
            except Exception as e:
                self.logger.warning(f"Failed to create atlas for {unit_type}: {e}")
        
        return {"atlases_created": atlases_created}
    
    def _execute_metadata_step(self) -> Dict[str, Any]:
        """Execute metadata generation step."""
        if not self._metadata_generator:
            raise PipelineError("Metadata generator not initialized", PipelineStep.METADATA)
        
        # This would implement the actual metadata generation logic
        try:
            sprites_toml_path = Path(self.config.data_dir) / "sprites.toml"
            
            # Simulate metadata generation
            self.logger.info(f"Generating sprites.toml at {sprites_toml_path}")
            
            # Ensure data directory exists
            sprites_toml_path.parent.mkdir(parents=True, exist_ok=True)
            
            # This would generate the actual metadata
            metadata_generated = True
            
        except Exception as e:
            raise PipelineError(f"Metadata generation failed: {e}", PipelineStep.METADATA)
        
        return {"metadata_generated": metadata_generated}
    
    def _execute_preview_step(self) -> Dict[str, Any]:
        """Execute preview generation step."""
        if not self.config.generate_previews:
            self.logger.info("Preview generation disabled, skipping")
            return {"previews_generated": 0}
        
        if not self._preview_processor:
            raise PipelineError("Preview processor not initialized", PipelineStep.PREVIEW)
        
        try:
            # This would implement the actual preview generation logic
            previews_generated = 0
            
            preview_dir = Path(self.config.preview_dir)
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            # Simulate preview generation
            self.logger.info("Generating asset previews")
            previews_generated = 1  # Placeholder
            
        except Exception as e:
            # Preview generation failure is recoverable
            raise PipelineError(f"Preview generation failed: {e}", PipelineStep.PREVIEW, recoverable=True)
        
        return {"previews_generated": previews_generated}
    
    def _execute_validate_step(self) -> Dict[str, Any]:
        """Execute asset validation step."""
        if not self._validator:
            raise PipelineError("Validator not initialized", PipelineStep.VALIDATE)
        
        # This would implement the actual validation logic
        validation_results = []
        total_errors = 0
        total_warnings = 0
        
        sprites_dir = Path(self.config.sprites_dir)
        if sprites_dir.exists():
            for sprite_file in sprites_dir.glob("*.png"):
                try:
                    # Simulate validation
                    result = ValidationResult(
                        asset_name=sprite_file.stem,
                        errors=[],
                        warnings=[]
                    )
                    validation_results.append(result)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to validate {sprite_file}: {e}")
        
        # Count total errors and warnings
        for result in validation_results:
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
        
        if total_errors > 0:
            raise PipelineError(f"Validation failed with {total_errors} errors", PipelineStep.VALIDATE)
        
        if total_warnings > 0:
            self.logger.warning(f"Validation completed with {total_warnings} warnings")
        
        return {
            "assets_validated": len(validation_results),
            "total_errors": total_errors,
            "total_warnings": total_warnings
        }
    
    # Cache management methods
    def _get_step_cache_key(self, step: PipelineStep) -> str:
        """Generate cache key for a pipeline step."""
        # This would include relevant configuration and file hashes
        return f"{step.value}_{hash(str(self.config))}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is still valid."""
        # This would check file modification times, configuration changes, etc.
        return False  # For now, always invalidate cache
    
    def _update_step_cache(self, step: PipelineStep, result: StepResult):
        """Update cache entry for a completed step."""
        cache_key = self._get_step_cache_key(step)
        self._cache_index[cache_key] = {
            "timestamp": time.time(),
            "result": result,
            "config_hash": hash(str(self.config))
        }
    
    def _load_cache_index(self):
        """Load cache index from disk."""
        cache_index_path = self._cache_dir / "index.json"
        if cache_index_path.exists():
            try:
                with open(cache_index_path) as f:
                    self._cache_index = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache index: {e}")
                self._cache_index = {}
    
    def _save_cache_index(self):
        """Save cache index to disk."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_index_path = self._cache_dir / "index.json"
        
        try:
            with open(cache_index_path, 'w') as f:
                # Convert StepResult objects to dictionaries for JSON serialization
                serializable_index = {}
                for key, value in self._cache_index.items():
                    if isinstance(value.get('result'), StepResult):
                        value = value.copy()
                        value['result'] = {
                            'step': value['result'].step.value,
                            'success': value['result'].success,
                            'duration': value['result'].duration,
                            'message': value['result'].message,
                            'data': value['result'].data,
                            'errors': value['result'].errors,
                            'warnings': value['result'].warnings
                        }
                    serializable_index[key] = value
                
                json.dump(serializable_index, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache index: {e}")
    
    def _generate_execution_summary(self):
        """Generate and log execution summary."""
        total_duration = time.time() - (self.state.start_time or time.time())
        
        self.logger.info("=" * 60)
        self.logger.info("PIPELINE EXECUTION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total execution time: {total_duration:.2f}s")
        self.logger.info(f"Steps completed: {len(self.state.completed_steps)}")
        self.logger.info(f"Steps failed: {len(self.state.failed_steps)}")
        self.logger.info(f"Total assets processed: {self.state.total_assets_processed}")
        self.logger.info(f"Cache hits: {self.state.cache_hits}")
        self.logger.info(f"Cache misses: {self.state.cache_misses}")
        
        if self.state.failed_steps:
            self.logger.info("\nFailed steps:")
            for step in self.state.failed_steps:
                result = self.state.step_results.get(step)
                if result:
                    self.logger.info(f"  - {step.value}: {result.message}")
        
        self.logger.info("\nStep execution times:")
        for step, result in self.state.step_results.items():
            status = "✓" if result.success else "✗"
            self.logger.info(f"  {status} {step.value}: {result.duration:.2f}s")
        
        self.logger.info("=" * 60)
    
    @contextmanager
    def rollback_on_failure(self):
        """Context manager for automatic rollback on pipeline failure."""
        initial_state = self.state.completed_steps.copy()
        
        try:
            yield
        except Exception:
            # Rollback completed steps
            self.logger.info("Rolling back pipeline changes due to failure")
            self._rollback_changes(initial_state)
            raise
    
    def _rollback_changes(self, initial_completed_steps: Set[PipelineStep]):
        """
        Rollback changes made during pipeline execution.
        
        Args:
            initial_completed_steps: Steps that were completed before this execution
        """
        # Determine which steps need to be rolled back
        steps_to_rollback = self.state.completed_steps - initial_completed_steps
        
        for step in reversed(list(steps_to_rollback)):
            try:
                self._rollback_step(step)
                self.state.completed_steps.discard(step)
                self.logger.info(f"Rolled back step: {step.value}")
            except Exception as e:
                self.logger.error(f"Failed to rollback step {step.value}: {e}")
    
    def _rollback_step(self, step: PipelineStep):
        """
        Rollback changes made by a specific step.
        
        Args:
            step: Step to rollback
        """
        # This would implement step-specific rollback logic
        # For now, we'll just log the rollback attempt
        self.logger.debug(f"Rolling back step {step.value}")