"""Standalone utilities for model path resolution."""

import json
import os


def get_model_path(model_base_path: str, name: str, version: str | None = None) -> str:
    """Get path to model directory."""
    if version:
        return os.path.join(model_base_path, name, version)
    return os.path.join(model_base_path, name, "active")


def get_active_version(model_base_path: str, name: str) -> str:
    """Read active version from symlink or metadata."""
    active_path = os.path.join(model_base_path, name, "active")

    if os.path.islink(active_path):
        target = os.readlink(active_path)
        return os.path.basename(target)
    elif os.path.isdir(active_path):
        with open(os.path.join(active_path, "metadata.json")) as f:
            meta = json.load(f)
            return meta.get("version", "v1")
    return "v1"
