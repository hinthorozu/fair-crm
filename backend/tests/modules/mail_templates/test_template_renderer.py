import pytest

from app.modules.mail_templates.domain.exceptions import MailTemplateRenderError
from app.modules.mail_templates.infrastructure.template_renderer import JinjaMailTemplateRenderer


def test_jinja_renderer_replaces_variables():
    renderer = JinjaMailTemplateRenderer()
    result = renderer.render("Hello {{ name }}", {"name": "Ada"})
    assert result == "Hello Ada"


def test_jinja_renderer_missing_variable_raises():
    renderer = JinjaMailTemplateRenderer()
    with pytest.raises(MailTemplateRenderError):
        renderer.render("Hello {{ name }}", {})


def test_jinja_renderer_preserves_mailersend_unsubscribe():
    renderer = JinjaMailTemplateRenderer()
    result = renderer.render(
        "Hello {{ name }} <a href=\"{{unsubscribe}}\">Unsubscribe</a>",
        {"name": "Ada"},
    )
    assert result == 'Hello Ada <a href="{{unsubscribe}}">Unsubscribe</a>'
