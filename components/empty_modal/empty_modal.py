from typing import NamedTuple

from django_components import Component, register


@register("empty_modal")
class EmptyModal(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        modal_id: str
        size: str | None = None
        no_close_button: bool = False

    class Defaults:
        size = "xl"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if not kwargs.modal_id:
            msg = "EmptyModal component requires a non-empty 'modal_id'."
            raise ValueError(msg)

        allowed_sizes = {None, "sm", "lg", "xl", "md"}
        if kwargs.size not in allowed_sizes:
            msg = "EmptyModal size must be one of: 'sm', 'lg', 'xl', 'md'."
            raise ValueError(msg)

        size = kwargs.size or "xl"
        return {
            "modal_id": kwargs.modal_id,
            "size": size,
            "no_close_button": kwargs.no_close_button,
        }
