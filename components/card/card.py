from typing import NamedTuple

from django_components import Component, Default, register


@register("card")
class Card(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        title: str
        icon: str | None = None
        card_classes: str = Default("")
        body_classes: str = Default("")
        header_classes: str = Default("")
        card_id: str | None = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "title": kwargs.title,
            "icon": kwargs.icon,
            "card_classes": kwargs.card_classes,
            "body_classes": kwargs.body_classes,
            "header_classes": kwargs.header_classes,
            "card_id": kwargs.card_id,
        }
