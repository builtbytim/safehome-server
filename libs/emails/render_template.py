from jinja2 import Environment, PackageLoader, select_autoescape
from libs.config.settings import get_settings

settings = get_settings()


env = Environment(
    loader=PackageLoader("libs.emails", "templates"),
    autoescape=select_autoescape()
)


def render_to_string(template_name: str, **kwargs):
    template = env.get_template(template_name)
    return template.render(**kwargs, settings=settings)
