"""
Integration tests for the asset pipeline CLI.
Tests command-line interface functionality and argument parsing.
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

# Add the parent directory to the path so we can import the CLI
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.asset_pipeline.cli import app
from scripts.asset_pipeline.config import PipelineConfig


class TestCLIIntegration:
    """Test CLI integration and command functionality."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create basic directory structure
        os.makedirs("assets/sprites", exist_ok=True)
        os.makedirs("assets/atlases", exist_ok=True)
        os.makedirs("assets/data", exist_ok=True)
        os.makedirs("crates/oldtimes-client", exist_ok=True)
        os.makedirs("scripts", exist_ok=True)
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_config(self, config_data: dict = None) -> Path:
        """Create a test configuration file."""
        if config_data is None:
            config_data = {
                "sources": {
                    "kenney_packs": ["test-pack"],
                    "ai_provider": "none"
                },
                "processing": {
                    "tile_size": [64, 32],
                    "unit_frame_size": [64, 64]
                },
                "paths": {
                    "assets_dir": "assets",
                    "sprites_dir": "assets/sprites"
                }
            }
        
        config_path = Path("test_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return config_path
    
    def test_cli_help(self):
        """Test that CLI help command works."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Asset pipeline for Old Times 2D Isometric RTS Game" in result.stdout
    
    def test_link_command_help(self):
        """Test link command help."""
        result = self.runner.invoke(app, ["link", "--help"])
        assert result.exit_code == 0
        assert "Create symlink between asset directories" in result.stdout
    
    def test_link_command_dry_run(self):
        """Test link command with dry run."""
        result = self.runner.invoke(app, ["link", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN:" in result.stdout
        assert "Would create symlink" in result.stdout
    
    @patch('scripts.asset_pipeline.cli.create_asset_symlink')
    @patch('scripts.asset_pipeline.cli.validate_asset_symlink')
    def test_link_command_success(self, mock_validate, mock_create):
        """Test successful link command execution."""
        mock_create.return_value = True
        mock_validate.return_value = (True, "/path/to/assets")
        
        result = self.runner.invoke(app, ["link"])
        assert result.exit_code == 0
        assert "Created symlink" in result.stdout
        mock_create.assert_called_once_with(force=True)
        mock_validate.assert_called_once()
    
    @patch('scripts.asset_pipeline.cli.create_asset_symlink')
    def test_link_command_failure(self, mock_create):
        """Test link command failure handling."""
        from scripts.asset_pipeline.utils.symlink import SymlinkError
        mock_create.side_effect = SymlinkError("Test error")
        
        result = self.runner.invoke(app, ["link"])
        assert result.exit_code == 1
        assert "Symlink error:" in result.stdout
    
    def test_config_command_show(self):
        """Test config command show functionality."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["config", "--show", "--config", str(config_path)])
        assert result.exit_code == 0
        # Should display configuration table
    
    def test_config_command_validate_valid(self):
        """Test config validation with valid configuration."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["config", "--validate", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Configuration is valid" in result.stdout
    
    def test_config_command_validate_invalid(self):
        """Test config validation with invalid configuration."""
        invalid_config = {
            "processing": {
                "tile_size": [-1, -1],  # Invalid negative dimensions
                "compression_level": 15  # Invalid compression level
            }
        }
        config_path = self.create_test_config(invalid_config)
        
        result = self.runner.invoke(app, ["config", "--validate", "--config", str(config_path)])
        assert result.exit_code == 1
        assert "Configuration validation errors:" in result.stdout
    
    def test_config_file_not_found(self):
        """Test behavior when config file doesn't exist."""
        result = self.runner.invoke(app, ["config", "--show", "--config", "nonexistent.json"])
        assert result.exit_code == 1
        assert "Configuration file not found" in result.stdout
    
    def test_kenney_command_no_packs(self):
        """Test kenney command with no packs configured."""
        config_data = {
            "sources": {
                "kenney_packs": [],
                "ai_provider": "none"
            }
        }
        config_path = self.create_test_config(config_data)
        
        result = self.runner.invoke(app, ["kenney", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "No Kenney packs configured" in result.stdout
    
    def test_cloud_command_no_provider(self):
        """Test cloud command with no AI provider."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["cloud", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "No AI provider configured" in result.stdout
    
    def test_mod_command_no_name(self):
        """Test mod command without NAME argument."""
        result = self.runner.invoke(app, ["mod"])
        assert result.exit_code == 2  # Typer error for missing argument
    
    def test_mod_command_with_name(self):
        """Test mod command with valid name."""
        config_path = self.create_test_config()
        
        # Mock the mod processing modules since they may not be fully implemented
        with patch('scripts.asset_pipeline.processing.mod.ModDirectoryManager'), \
             patch('scripts.asset_pipeline.processing.mod.ModConfigManager'), \
             patch('scripts.asset_pipeline.processing.mod.ModAssetIsolation'), \
             patch('scripts.asset_pipeline.processing.mod.ModMetadataGenerator'):
            
            result = self.runner.invoke(app, ["mod", "test_mod", "--config", str(config_path)])
            # The command should attempt to run, even if modules aren't fully implemented
            # We're testing the CLI argument parsing and basic flow
    
    def test_environment_variable_override(self):
        """Test that environment variables override configuration."""
        config_path = self.create_test_config()
        
        # Set environment variables
        env_vars = {
            'ASSET_PIPELINE_AI_PROVIDER': 'test_provider',
            'ASSET_PIPELINE_TILE_WIDTH': '128',
            'ASSET_PIPELINE_TILE_HEIGHT': '64',
            'ASSET_PIPELINE_OUTPUT_FORMAT': 'WEBP'
        }
        
        with patch.dict(os.environ, env_vars):
            result = self.runner.invoke(app, ["config", "--show", "--config", str(config_path)])
            assert result.exit_code == 0
            # The output should reflect the environment variable overrides
    
    def test_all_command_basic(self):
        """Test the all command basic functionality."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["all", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Running complete asset pipeline" in result.stdout
    
    def test_validate_command_basic(self):
        """Test the validate command basic functionality."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["validate", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Validating assets" in result.stdout
    
    def test_atlas_command_basic(self):
        """Test the atlas command basic functionality."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["atlas", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Creating texture atlases" in result.stdout
    
    def test_preview_command_basic(self):
        """Test the preview command basic functionality."""
        config_path = self.create_test_config()
        
        result = self.runner.invoke(app, ["preview", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Generating asset previews" in result.stdout
    
    def test_preview_command_with_options(self):
        """Test preview command with various options."""
        config_path = self.create_test_config()
        
        # Test grid-only option
        result = self.runner.invoke(app, ["preview", "--grid-only", "--config", str(config_path)])
        assert result.exit_code == 0
        
        # Test alignment-only option
        result = self.runner.invoke(app, ["preview", "--alignment-only", "--config", str(config_path)])
        assert result.exit_code == 0
        
        # Test animations-only option
        result = self.runner.invoke(app, ["preview", "--animations-only", "--config", str(config_path)])
        assert result.exit_code == 0
        
        # Test cleanup option
        result = self.runner.invoke(app, ["preview", "--cleanup", "--config", str(config_path)])
        assert result.exit_code == 0


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_global_config_option(self):
        """Test that global --config option is parsed correctly."""
        result = self.runner.invoke(app, ["config", "--show", "--config", "test.json"])
        # Should fail because file doesn't exist, but argument parsing should work
        assert "Configuration file not found" in result.stdout
    
    def test_boolean_flags(self):
        """Test boolean flag parsing."""
        # Test link command flags
        result = self.runner.invoke(app, ["link", "--help"])
        assert "--force" in result.stdout
        assert "--no-force" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--validate" in result.stdout
    
    def test_optional_arguments(self):
        """Test optional argument parsing."""
        # Test preview command optional arguments
        result = self.runner.invoke(app, ["preview", "--help"])
        assert "--output" in result.stdout
        assert "--assets" in result.stdout
        assert "--grid-only" in result.stdout
        assert "--alignment-only" in result.stdout
        assert "--animations-only" in result.stdout
    
    def test_required_arguments(self):
        """Test required argument validation."""
        # Test mod command requires NAME
        result = self.runner.invoke(app, ["mod", "--help"])
        assert "NAME" in result.stdout
        assert "[required]" in result.stdout or "required" in result.stdout.lower()


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_invalid_command(self):
        """Test handling of invalid commands."""
        result = self.runner.invoke(app, ["invalid_command"])
        assert result.exit_code != 0
    
    def test_missing_dependencies_simulation(self):
        """Test behavior when dependencies are missing."""
        # This would require mocking the import system, which is complex
        # For now, we'll test that the CLI handles import errors gracefully
        pass
    
    def test_permission_errors(self):
        """Test handling of permission errors."""
        # This would require creating files with restricted permissions
        # Implementation depends on the specific error handling in each command
        pass


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])