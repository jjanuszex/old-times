"""
Integration tests for the complete asset pipeline.
Tests end-to-end pipeline execution, caching, error handling, and rollback.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from ..pipeline import AssetPipeline, PipelineStep, PipelineError, PipelineState
from ..config import PipelineConfig, ErrorConfig


class TestPipelineIntegration:
    """Integration tests for the complete asset pipeline."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig(
            assets_dir=f"{self.temp_dir}/assets",
            sprites_dir=f"{self.temp_dir}/assets/sprites",
            atlases_dir=f"{self.temp_dir}/assets/atlases",
            data_dir=f"{self.temp_dir}/assets/data",
            preview_dir=f"{self.temp_dir}/assets/preview",
            mods_dir=f"{self.temp_dir}/mods"
        )
        
        # Create directory structure
        for dir_path in [
            self.config.assets_dir,
            self.config.sprites_dir,
            self.config.atlases_dir,
            self.config.data_dir,
            self.config.preview_dir,
            self.config.mods_dir
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Create some test assets
        self._create_test_assets()
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_assets(self):
        """Create test assets for pipeline testing."""
        # Create test sprite files
        sprites_dir = Path(self.config.sprites_dir)
        
        # Create dummy PNG files (just empty files for testing)
        test_sprites = ["grass.png", "stone.png", "worker.png", "lumberjack.png"]
        for sprite in test_sprites:
            (sprites_dir / sprite).touch()
        
        # Create test configuration files
        config_dir = Path(self.config.data_dir)
        
        # Create a basic sprites.toml
        sprites_toml = config_dir / "sprites.toml"
        sprites_toml.write_text("""
[tiles.grass]
kind = "tile"
size = [64, 32]
source = "sprites/grass.png"

[buildings.lumberjack]
kind = "building"
size = [64, 96]
source = "sprites/lumberjack.png"

[units.worker]
kind = "unit"
source = "sprites/worker.png"
frame_size = [64, 64]
""")
    
    def test_full_pipeline_execution(self):
        """Test complete pipeline execution with all steps."""
        pipeline = AssetPipeline(self.config)
        
        # Mock the step handlers to avoid actual processing
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 5}), \
             patch.object(pipeline, '_execute_ai_sources_step', return_value={"assets_generated": 3}), \
             patch.object(pipeline, '_execute_normalize_step', return_value={"assets_normalized": 8}), \
             patch.object(pipeline, '_execute_atlas_step', return_value={"atlases_created": 2}), \
             patch.object(pipeline, '_execute_metadata_step', return_value={"metadata_generated": True}), \
             patch.object(pipeline, '_execute_preview_step', return_value={"previews_generated": 1}), \
             patch.object(pipeline, '_execute_validate_step', return_value={"assets_validated": 8}):
            
            final_state = pipeline.run_full_pipeline()
            
            # Verify all steps completed successfully
            assert len(final_state.completed_steps) == len(PipelineStep)
            assert len(final_state.failed_steps) == 0
            
            # Verify step results
            for step in PipelineStep:
                assert step in final_state.step_results
                assert final_state.step_results[step].success
                assert final_state.step_results[step].duration > 0
    
    def test_pipeline_with_specific_steps(self):
        """Test pipeline execution with specific steps only."""
        pipeline = AssetPipeline(self.config)
        
        # Test running only symlink and validation steps
        requested_steps = [PipelineStep.SYMLINK, PipelineStep.VALIDATE]
        
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_validate_step', return_value={"assets_validated": 8}):
            
            final_state = pipeline.run_full_pipeline(requested_steps)
            
            # Should include dependencies (none for symlink, metadata for validate)
            expected_steps = {PipelineStep.SYMLINK, PipelineStep.VALIDATE}
            # Validate depends on metadata, which depends on atlas, etc.
            # So we should see all dependencies included
            assert PipelineStep.SYMLINK in final_state.completed_steps
            assert len(final_state.failed_steps) == 0
    
    def test_pipeline_step_dependencies(self):
        """Test that pipeline respects step dependencies."""
        pipeline = AssetPipeline(self.config)
        
        # Mock all step handlers
        execution_order = []
        
        def track_execution(step_name):
            def handler():
                execution_order.append(step_name)
                return {"executed": True}
            return handler
        
        with patch.object(pipeline, '_execute_symlink_step', track_execution("symlink")), \
             patch.object(pipeline, '_execute_kenney_sources_step', track_execution("kenney")), \
             patch.object(pipeline, '_execute_ai_sources_step', track_execution("ai")), \
             patch.object(pipeline, '_execute_normalize_step', track_execution("normalize")), \
             patch.object(pipeline, '_execute_atlas_step', track_execution("atlas")), \
             patch.object(pipeline, '_execute_metadata_step', track_execution("metadata")), \
             patch.object(pipeline, '_execute_preview_step', track_execution("preview")), \
             patch.object(pipeline, '_execute_validate_step', track_execution("validate")):
            
            pipeline.run_full_pipeline()
            
            # Verify execution order respects dependencies
            symlink_idx = execution_order.index("symlink")
            kenney_idx = execution_order.index("kenney")
            ai_idx = execution_order.index("ai")
            normalize_idx = execution_order.index("normalize")
            atlas_idx = execution_order.index("atlas")
            metadata_idx = execution_order.index("metadata")
            
            # Symlink should come before kenney and ai
            assert symlink_idx < kenney_idx
            assert symlink_idx < ai_idx
            
            # Normalize should come after kenney and ai
            assert normalize_idx > kenney_idx
            assert normalize_idx > ai_idx
            
            # Atlas should come after normalize
            assert atlas_idx > normalize_idx
            
            # Metadata should come after atlas
            assert metadata_idx > atlas_idx
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling and recovery."""
        error_config = ErrorConfig(ignore_categories=["preview"])
        pipeline = AssetPipeline(self.config, error_config)
        
        # Mock step handlers with one failure
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 5}), \
             patch.object(pipeline, '_execute_ai_sources_step', return_value={"assets_generated": 3}), \
             patch.object(pipeline, '_execute_normalize_step', return_value={"assets_normalized": 8}), \
             patch.object(pipeline, '_execute_atlas_step', return_value={"atlases_created": 2}), \
             patch.object(pipeline, '_execute_metadata_step', return_value={"metadata_generated": True}), \
             patch.object(pipeline, '_execute_preview_step', side_effect=Exception("Preview failed")), \
             patch.object(pipeline, '_execute_validate_step', return_value={"assets_validated": 8}):
            
            final_state = pipeline.run_full_pipeline()
            
            # Preview should have failed but pipeline should continue
            assert PipelineStep.PREVIEW in final_state.failed_steps
            assert PipelineStep.VALIDATE in final_state.completed_steps
            
            # Other steps should have completed successfully
            expected_completed = {
                PipelineStep.SYMLINK,
                PipelineStep.KENNEY_SOURCES,
                PipelineStep.AI_SOURCES,
                PipelineStep.NORMALIZE,
                PipelineStep.ATLAS,
                PipelineStep.METADATA,
                PipelineStep.VALIDATE
            }
            assert expected_completed.issubset(final_state.completed_steps)
    
    def test_pipeline_critical_failure(self):
        """Test pipeline behavior with critical step failure."""
        pipeline = AssetPipeline(self.config)
        
        # Mock step handlers with critical failure
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 5}), \
             patch.object(pipeline, '_execute_ai_sources_step', return_value={"assets_generated": 3}), \
             patch.object(pipeline, '_execute_normalize_step', side_effect=Exception("Critical normalization failure")):
            
            with pytest.raises(PipelineError):
                pipeline.run_full_pipeline()
    
    def test_pipeline_caching(self):
        """Test pipeline caching functionality."""
        pipeline = AssetPipeline(self.config)
        
        # Mock cache validation to return True for some steps
        with patch.object(pipeline, '_is_cache_valid', return_value=True), \
             patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}) as mock_symlink:
            
            # Set up cache index with cached symlink step
            cache_key = pipeline._get_step_cache_key(PipelineStep.SYMLINK)
            pipeline._cache_index[cache_key] = {
                "timestamp": 1234567890,
                "result": {"executed": True},
                "config_hash": hash(str(pipeline.config))
            }
            
            final_state = pipeline.run_full_pipeline([PipelineStep.SYMLINK])
            
            # Symlink step should have been skipped due to cache
            assert final_state.cache_hits > 0
            mock_symlink.assert_not_called()
    
    def test_pipeline_rollback(self):
        """Test pipeline rollback functionality."""
        pipeline = AssetPipeline(self.config)
        
        # Create some test files that would be "created" by pipeline steps
        test_file = Path(self.config.sprites_dir) / "test_generated.png"
        
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 5}), \
             patch.object(pipeline, '_execute_normalize_step', side_effect=Exception("Normalization failed")), \
             patch.object(pipeline, '_rollback_step') as mock_rollback:
            
            with pipeline.rollback_on_failure():
                try:
                    pipeline.run_full_pipeline()
                except PipelineError:
                    pass  # Expected
            
            # Rollback should have been called for completed steps
            assert mock_rollback.call_count > 0
    
    def test_pipeline_state_management(self):
        """Test pipeline state tracking and management."""
        pipeline = AssetPipeline(self.config)
        
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 5}):
            
            final_state = pipeline.run_full_pipeline([PipelineStep.SYMLINK, PipelineStep.KENNEY_SOURCES])
            
            # Verify state tracking
            assert final_state.start_time is not None
            assert len(final_state.step_results) == 2
            assert final_state.total_assets_processed >= 0
            
            # Verify step results contain required information
            for step, result in final_state.step_results.items():
                assert result.step == step
                assert result.duration > 0
                assert result.message is not None
                assert isinstance(result.data, dict)
    
    def test_pipeline_incremental_updates(self):
        """Test pipeline incremental update functionality."""
        pipeline = AssetPipeline(self.config)
        
        # First run - all steps should execute
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}) as mock_symlink, \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 5}) as mock_kenney:
            
            first_state = pipeline.run_full_pipeline([PipelineStep.SYMLINK, PipelineStep.KENNEY_SOURCES])
            
            assert mock_symlink.call_count == 1
            assert mock_kenney.call_count == 1
            assert first_state.cache_misses == 2
        
        # Second run with same pipeline - should use cache
        pipeline2 = AssetPipeline(self.config)
        pipeline2._cache_index = pipeline._cache_index.copy()
        
        with patch.object(pipeline2, '_is_cache_valid', return_value=True), \
             patch.object(pipeline2, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}) as mock_symlink2, \
             patch.object(pipeline2, '_execute_kenney_sources_step', return_value={"assets_processed": 5}) as mock_kenney2:
            
            second_state = pipeline2.run_full_pipeline([PipelineStep.SYMLINK, PipelineStep.KENNEY_SOURCES])
            
            # Steps should be skipped due to cache
            assert mock_symlink2.call_count == 0
            assert mock_kenney2.call_count == 0
            assert second_state.cache_hits == 2
    
    def test_pipeline_statistics_reporting(self):
        """Test pipeline statistics and reporting functionality."""
        pipeline = AssetPipeline(self.config)
        
        with patch.object(pipeline, '_execute_symlink_step', return_value={"symlink_target": "../../assets"}), \
             patch.object(pipeline, '_execute_kenney_sources_step', return_value={"assets_processed": 10}), \
             patch.object(pipeline, '_execute_normalize_step', return_value={"assets_normalized": 15}):
            
            final_state = pipeline.run_full_pipeline([
                PipelineStep.SYMLINK, 
                PipelineStep.KENNEY_SOURCES, 
                PipelineStep.NORMALIZE
            ])
            
            # Verify statistics are tracked
            assert final_state.total_assets_processed >= 15  # From normalize step
            assert len(final_state.step_results) == 3
            
            # Verify timing information
            total_duration = sum(result.duration for result in final_state.step_results.values())
            assert total_duration > 0
            
            # Verify step-specific data is preserved
            kenney_result = final_state.step_results[PipelineStep.KENNEY_SOURCES]
            assert kenney_result.data.get("assets_processed") == 10
            
            normalize_result = final_state.step_results[PipelineStep.NORMALIZE]
            assert normalize_result.data.get("assets_normalized") == 15


class TestPipelineConfiguration:
    """Test pipeline configuration and initialization."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization with different configurations."""
        config = PipelineConfig()
        error_config = ErrorConfig(max_retries=5)
        
        pipeline = AssetPipeline(config, error_config)
        
        assert pipeline.config == config
        assert pipeline.error_config == error_config
        assert isinstance(pipeline.state, PipelineState)
        assert pipeline.logger is not None
    
    def test_pipeline_component_initialization(self):
        """Test that pipeline components are properly initialized."""
        config = PipelineConfig()
        pipeline = AssetPipeline(config)
        
        # Initialize components
        pipeline._initialize_components()
        
        # Verify providers are initialized
        assert "kenney" in pipeline._providers
        assert "ai" in pipeline._providers
        
        # Verify processors are initialized
        assert pipeline._normalizer is not None
        assert pipeline._atlas_generator is not None
        assert pipeline._metadata_generator is not None
        assert pipeline._validator is not None
        assert pipeline._preview_processor is not None
    
    def test_execution_order_calculation(self):
        """Test calculation of step execution order."""
        config = PipelineConfig()
        pipeline = AssetPipeline(config)
        
        # Test with all steps
        all_steps = list(PipelineStep)
        execution_order = pipeline._calculate_execution_order(all_steps)
        
        # Verify symlink comes first (no dependencies)
        assert execution_order[0] == PipelineStep.SYMLINK
        
        # Verify dependencies are respected
        symlink_idx = execution_order.index(PipelineStep.SYMLINK)
        kenney_idx = execution_order.index(PipelineStep.KENNEY_SOURCES)
        normalize_idx = execution_order.index(PipelineStep.NORMALIZE)
        atlas_idx = execution_order.index(PipelineStep.ATLAS)
        metadata_idx = execution_order.index(PipelineStep.METADATA)
        
        assert symlink_idx < kenney_idx
        assert kenney_idx < normalize_idx
        assert normalize_idx < atlas_idx
        assert atlas_idx < metadata_idx
    
    def test_execution_order_with_subset(self):
        """Test execution order calculation with subset of steps."""
        config = PipelineConfig()
        pipeline = AssetPipeline(config)
        
        # Request only metadata step - should include all dependencies
        requested_steps = [PipelineStep.METADATA]
        execution_order = pipeline._calculate_execution_order(requested_steps)
        
        # Should include all dependencies
        expected_steps = {
            PipelineStep.SYMLINK,
            PipelineStep.KENNEY_SOURCES,
            PipelineStep.AI_SOURCES,
            PipelineStep.NORMALIZE,
            PipelineStep.ATLAS,
            PipelineStep.METADATA
        }
        
        assert set(execution_order) == expected_steps
        
        # Verify order is still correct
        assert execution_order.index(PipelineStep.SYMLINK) < execution_order.index(PipelineStep.KENNEY_SOURCES)
        assert execution_order.index(PipelineStep.NORMALIZE) < execution_order.index(PipelineStep.ATLAS)
        assert execution_order.index(PipelineStep.ATLAS) < execution_order.index(PipelineStep.METADATA)


class TestPipelineCacheManagement:
    """Test pipeline cache management functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = PipelineConfig()
        self.pipeline = AssetPipeline(self.config)
        self.pipeline._cache_dir = Path(self.temp_dir) / "cache"
    
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cache_key_generation(self):
        """Test cache key generation for steps."""
        step = PipelineStep.SYMLINK
        cache_key = self.pipeline._get_step_cache_key(step)
        
        assert isinstance(cache_key, str)
        assert step.value in cache_key
        
        # Different configs should generate different keys
        config2 = PipelineConfig(tile_size=(32, 16))
        pipeline2 = AssetPipeline(config2)
        cache_key2 = pipeline2._get_step_cache_key(step)
        
        assert cache_key != cache_key2
    
    def test_cache_index_persistence(self):
        """Test cache index saving and loading."""
        # Create some cache entries
        self.pipeline._cache_index = {
            "test_key": {
                "timestamp": 1234567890,
                "result": {"test": "data"},
                "config_hash": 12345
            }
        }
        
        # Save cache index
        self.pipeline._save_cache_index()
        
        # Create new pipeline and load cache
        pipeline2 = AssetPipeline(self.config)
        pipeline2._cache_dir = self.pipeline._cache_dir
        pipeline2._load_cache_index()
        
        assert "test_key" in pipeline2._cache_index
        assert pipeline2._cache_index["test_key"]["timestamp"] == 1234567890
    
    def test_cache_validation(self):
        """Test cache entry validation."""
        # For now, cache validation always returns False
        # This test verifies the current behavior
        cache_entry = {
            "timestamp": 1234567890,
            "result": {"test": "data"},
            "config_hash": 12345
        }
        
        is_valid = self.pipeline._is_cache_valid(cache_entry)
        assert is_valid is False  # Current implementation always invalidates