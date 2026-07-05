from typing import Any

from jinja2 import StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

from app.modules.mail_templates.domain.exceptions import MailTemplateRenderError


class JinjaMailTemplateRenderer:
    def __init__(self) -> None:
        self._environment = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)

    def render(self, template: str, variables: dict[str, Any]) -> str:
        try:
            compiled = self._environment.from_string(template)
            return compiled.render(**variables)
        except (TemplateSyntaxError, UndefinedError, TypeError, ValueError) as exc:
            raise MailTemplateRenderError(f"Template render failed: {exc}") from exc
