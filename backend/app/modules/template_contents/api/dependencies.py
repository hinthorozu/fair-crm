from app.modules.quote_templates.api.dependencies import _require

PERMISSION_READ = "fair_crm.template_contents.read"
PERMISSION_CREATE = "fair_crm.template_contents.create"
PERMISSION_UPDATE = "fair_crm.template_contents.update"
PERMISSION_DELETE = "fair_crm.template_contents.delete"

require_read_permission = _require(PERMISSION_READ)
require_create_permission = _require(PERMISSION_CREATE)
require_update_permission = _require(PERMISSION_UPDATE)
require_delete_permission = _require(PERMISSION_DELETE)
