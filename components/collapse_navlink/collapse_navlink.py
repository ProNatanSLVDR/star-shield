import uuid
from typing import NamedTuple, Optional

from django_components import Component, register


@register("collapse_navlink")
class CollapseNavlink(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        icon: str
        text: str
        collapse_id: Optional[str] = None

    class Defaults:
        collapse_id: Optional[str] = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if not kwargs.icon:
            raise ValueError("CollapseNavlink component requires a non-empty 'icon' value.")
        if not kwargs.text:
            raise ValueError("CollapseNavlink component requires a non-empty 'text' value.")

        collapse_id = kwargs.collapse_id
        if not collapse_id:
            collapse_id = f"collapse_{uuid.uuid4().hex[:8]}"

        return {
            "icon": kwargs.icon,
            "text": kwargs.text,
            "collapse_id": collapse_id,
        }
