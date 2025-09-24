"""
Asset Pipeline for Old Times 2D Isometric RTS Game

A comprehensive Python-based toolchain for asset generation, processing, and management.
Supports multiple asset sources (CC0 packs, AI generation), creates texture atlases,
and generates metadata files for the Rust/Bevy game engine.
"""

__version__ = "0.1.0"
__author__ = "Old Times Development Team"

from .config import PipelineConfig
from .providers.base import AssetProvider, AssetSpec
from .processing.normalizer import AssetNormalizer
from .processing.atlas import AtlasGenerator
from .processing.metadata import MetadataGenerator
from .processing.validator import QualityValidator

__all__ = [
    "PipelineConfig",
    "AssetProvider",
    "AssetSpec",
    "AssetNormalizer",
    "AtlasGenerator",
    "MetadataGenerator",
    "QualityValidator",
]