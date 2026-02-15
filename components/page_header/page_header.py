from typing import NamedTuple

from django_components import Component, register


@register("page_header")
class PageHeader(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        title: str
        subtitle: str
        icon: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "title": kwargs.title,
            "subtitle": kwargs.subtitle,
            "icon": kwargs.icon,
        }
