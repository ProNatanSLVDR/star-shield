from typing_extensions import Dict, Any
from django_components import Component, Default, register
from typing import NamedTuple

@register("button")
class Button(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        classes: str
        icon: str
        text: str
        href: str
        extra_kwargs: Dict[str, Any]

    class Defaults:
        href: str = None
        extra_kwargs = Default(dict)


    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        extra_kwargs = kwargs.extra_kwargs.copy()

        # pop the extra_kwargs keys that are not needed
        default_hx_modal = extra_kwargs.pop("default_hx_modal", None)
        modal_close = extra_kwargs.pop("modal_close", None)
        disabled = extra_kwargs.pop("disabled", None)

        return {
            "classes": kwargs.classes,
            "icon": kwargs.icon,
            "text": kwargs.text,
            "href": kwargs.href,
            "extra_kwargs": extra_kwargs,
            # custom kwargs
            "default_hx_modal": default_hx_modal,
            "modal_close": modal_close,
            "disabled": disabled,
        }