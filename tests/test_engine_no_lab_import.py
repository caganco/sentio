"""Strangler-purity invariant: no ``src/engine`` module may import the untracked lab.

``.importlinter`` cannot enforce this -- its ``root_package = src`` graph cannot
see ``lab-demo-clone1`` (untracked, not a package on the path), so an accidental
``src.engine -> lab`` edge would slip past it silently. This AST scan closes that
gap: it walks every module under ``src/engine/`` and fails if any ``import`` /
``from ... import`` names a forbidden root module. Keeps the Catal-3 resolution
(engine lives in ``src`` BECAUSE it imports committed primitives only) executable
through Faz-2/3, when the cost (clib) and sector temptations actually arrive.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

import src.engine as engine_pkg

# Root module components that must never appear in an engine import.
_FORBIDDEN_ROOTS = {"lab", "lab_demo_clone1", "clib", "c9", "c12"}

_ENGINE_DIR = Path(engine_pkg.__file__).resolve().parent
_ENGINE_MODULES = sorted(_ENGINE_DIR.glob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    """Root module component of every import in ``tree`` (absolute imports only).

    ``import a.b.c`` / ``from a.b import c`` both contribute root ``a``. Relative
    imports (``from . import x``, level > 0) are intra-package and carry no root.
    """
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def test_engine_modules_discovered():
    # Guard against a silently-empty scan (e.g. glob path drift).
    assert _ENGINE_MODULES, f"no engine modules found under {_ENGINE_DIR}"


@pytest.mark.parametrize("module_path", _ENGINE_MODULES, ids=lambda p: p.name)
def test_no_lab_import(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    leaked = _imported_roots(tree) & _FORBIDDEN_ROOTS
    assert not leaked, (
        f"{module_path.name} imports forbidden lab root(s) {sorted(leaked)}: "
        "src/engine must depend on committed src/* primitives only (no src->lab)."
    )
