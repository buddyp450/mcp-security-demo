from __future__ import annotations

import ast
import difflib
from functools import lru_cache
from pathlib import Path
from typing import List

from .catalog import CLIENT_CATALOG
from .models import CodeAnnotation, CodeDiffResponse

REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        parts = path.parts
        if parts and parts[0] == REPO_ROOT.name:
            path = Path(*parts[1:]) if len(parts) > 1 else Path()
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()

    if not str(path).startswith(str(REPO_ROOT)):
        raise FileNotFoundError("Path escapes repository")
    if not path.exists():
        raise FileNotFoundError(path_str)
    return path


def _read_file(relative_path: str) -> str:
    target = _resolve_repo_path(relative_path)
    return target.read_text(encoding="utf-8")


def _collect_annotations(source: str) -> List[CodeAnnotation]:
    annotations: List[CodeAnnotation] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", start)
            symbol = node.name if isinstance(node, ast.ClassDef) else f"{node.name}"
            summary = ast.get_docstring(node) or ""
            annotations.append(
                CodeAnnotation(
                    symbol=symbol,
                    summary=summary[:160],
                    start_line=start,
                    end_line=end,
                )
            )
    annotations.sort(key=lambda ann: ann.start_line)
    return annotations


@lru_cache(maxsize=128)
def compute_code_diff(file_path: str, baseline: str, variant: str) -> CodeDiffResponse:
    if file_path.startswith("clients/"):
        relative = f"mcp-security-demo/backend/{file_path}"
    elif file_path.startswith("backend/"):
        relative = f"mcp-security-demo/{file_path}"
    else:
        relative = file_path

    baseline_profile = CLIENT_CATALOG.get(baseline)
    variant_profile = CLIENT_CATALOG.get(variant)
    if not baseline_profile or not variant_profile:
        raise FileNotFoundError("Unknown client reference")

    base_source = _read_file(baseline_profile.source_path)
    variant_source = _read_file(variant_profile.source_path)

    diff = "\n".join(
        difflib.unified_diff(
            base_source.splitlines(),
            variant_source.splitlines(),
            fromfile=baseline_profile.source_path,
            tofile=variant_profile.source_path,
            lineterm="",
        )
    )

    annotations = _collect_annotations(variant_source)
    return CodeDiffResponse(
        file=relative,
        baseline=baseline_profile.id,
        variant=variant_profile.id,
        diff=diff,
        annotations=annotations,
    )

