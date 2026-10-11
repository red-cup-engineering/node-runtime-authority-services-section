"""Intake Stack - validates and normalizes recognitions before persistence.

The intake stack implements the schema registry, discipline filters, and 
normalization pipeline from the intake-stack simulation specification.
"""

from app.intake.registry import SchemaRegistry
from app.intake.pipeline import IntakePipeline
from app.intake.normalizer import RecognitionNormalizer

__all__ = [
    "SchemaRegistry",
    "IntakePipeline", 
    "RecognitionNormalizer",
]
