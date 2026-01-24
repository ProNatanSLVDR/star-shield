from typing import NamedTuple

from django_components import Component, Default, register
from typing_extensions import Any


@register("button")
class Button(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        classes: str
        icon: str
        text: str
        href: str
        extra_kwargs: dict[str, Any]

    class Defaults:
        href: str = None
        extra_kwargs = Default(dict)

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        extra_kwargs = kwargs.extra_kwargs.copy()

        # pop the extra_kwargs keys that are not needed
        hx_modal_toggle = extra_kwargs.pop("hx_modal_toggle", None)
        hx_modal_target = extra_kwargs.pop("hx_modal_target", None)
        modal_close = extra_kwargs.pop("modal_close", None)

        disabled = extra_kwargs.pop("disabled", None)

        return {
            "classes": kwargs.classes,
            "icon": kwargs.icon,
            "text": kwargs.text,
            "extra_kwargs": extra_kwargs,
            "disabled": disabled,
            # Modals
            "hx_modal_toggle": hx_modal_toggle,
            "hx_modal_target": hx_modal_target,
            "modal_close": modal_close,
        }
