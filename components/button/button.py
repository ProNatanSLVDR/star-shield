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
        disabled: bool
        default_hx_modal: bool
        modal_close: bool
        extra_kwargs: Dict[str, Any]

    class Defaults:
        default_hx_modal: bool = False
        modal_close: bool = False
        href: str = None
        disabled: bool = False
        extra_kwargs = Default(dict)


    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "classes": kwargs.classes,
            "icon": kwargs.icon,
            "text": kwargs.text,
            "href": kwargs.href,
            "extra_kwargs": kwargs.extra_kwargs,
            "default_hx_modal": kwargs.default_hx_modal,
            "modal_close": kwargs.modal_close,
        }