from pathlib import Path


ROUTES = Path("app/modules/system_admin/api/data_operation_routes.py")


def test_analyze_export_route_uses_execute_permission_only():
    source = ROUTES.read_text(encoding="utf-8")
    marker = '"/runs/{run_id}/dataset/customers/export"'
    start = source.index(marker)
    end = source.index('\n\n@router.get(', start + len(marker))
    route = source[start:end]

    assert "Depends(require_data_operations_run_permission)" in route
    assert "Depends(require_data_operations_read_permission)" not in route
