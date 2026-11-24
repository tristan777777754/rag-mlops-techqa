"""Check that the repository's declared runtime dependencies import offline."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    ("datasets", "huggingface_hub", "pandas", "pyarrow", "yaml"),
)
def test_runtime_dependency_imports(module_name: str) -> None:
    importlib.import_module(module_name)
