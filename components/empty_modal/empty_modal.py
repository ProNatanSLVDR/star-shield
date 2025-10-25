from typing import NamedTuple, Optional

from django_components import Component, register


@register("empty_modal")
class EmptyModal(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        modal_id: str
        size: Optional[str] = None

    class Defaults:
        size = "xl"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if not kwargs.modal_id:
            raise ValueError("EmptyModal component requires a non-empty 'modal_id'.")

        allowed_sizes = {None, "sm", "lg", "xl"}
        if kwargs.size not in allowed_sizes:
            raise ValueError("EmptyModal size must be one of: 'sm', 'lg', 'xl'.")

        size = kwargs.size or "xl"
        return {
            "modal_id": kwargs.modal_id,
            "size": size,
        }

