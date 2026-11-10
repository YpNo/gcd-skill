"""Load the hyphen-named scripts in scripts/ as importable modules for tests."""

import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def load_script(name: str) -> ModuleType:
    """Import scripts/<name>.py under a module name with hyphens replaced."""
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS_DIR / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
