from django_components import Component, register
from typing import NamedTuple

@register("button")
class Button(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        classes: str
        icon: str
        text: str
        href: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "classes": kwargs.classes,
            "icon": kwargs.icon,
            "text": kwargs.text,
            "href": kwargs.href,
        }