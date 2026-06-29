"""Context construction layer: ContextPackage (Node 7C output) + prompt building (Node 8)."""

from .answer_generator import generate_answer
from .context_package import (
    ContextChunk,
    ContextPackage,
    build_context_package,
    build_context_string,
    build_prompt,
)

__all__ = [
    "ContextChunk",
    "ContextPackage",
    "build_context_package",
    "build_context_string",
    "build_prompt",
    "generate_answer",
]
