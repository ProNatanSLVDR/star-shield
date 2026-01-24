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
        if not kwargs.title:
            raise ValueError("Card component requires a non-empty 'title'.")

        # Build card classes - always include base classes
        base_card_classes = "card shadow-sm border rounded-4"
        card_classes = f"{base_card_classes} {kwargs.card_classes}".strip()

        # Build body classes - always include base classes
        base_body_classes = "card-body px-4 py-4"
        body_classes = f"{base_body_classes} {kwargs.body_classes}".strip()

        # Build header classes - always include base classes
        base_header_classes = "card-header bg-primary border-bottom px-4 py-3"
        header_classes = f"{base_header_classes} {kwargs.header_classes}".strip()

        return {
            "title": kwargs.title,
            "icon": kwargs.icon,
            "card_classes": card_classes,
            "body_classes": body_classes,
            "header_classes": header_classes,
            "card_id": kwargs.card_id,
        }
