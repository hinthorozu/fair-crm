from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[3]
ROUTES_PATH = BACKEND_ROOT / "app/modules/system_admin/api/data_operation_routes.py"
SERVICE_PATH = BACKEND_ROOT / "app/modules/system_admin/application/data_operation_service.py"


def _function_source(path: Path, function_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"Function not found: {function_name}")


def _class_source(path: Path, class_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            return segment
    raise AssertionError(f"Class not found: {class_name}")


def test_download_route_uses_execute_permission_only() -> None:
    source = _function_source(ROUTES_PATH, "download_data_operation_file")
    assert "Depends(require_data_operations_run_permission)" in source
    assert "Depends(require_data_operations_read_permission)" not in source


def test_download_use_case_uses_same_execute_permission() -> None:
    source = _class_source(SERVICE_PATH, "DownloadDataOperationFileUseCase")
    assert "permission_code=PERMISSION_RUN" in source
    assert "permission_code=PERMISSION_READ" not in source
