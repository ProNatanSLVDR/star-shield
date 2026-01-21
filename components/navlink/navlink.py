from typing import NamedTuple, Optional

from django_components import Component, register


@register("navlink")
class Navlink(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        link: str
        icon: str
        text: str
        page_name: Optional[str] = None
        current_page: Optional[str] = None

    class Defaults:
        page_name: Optional[str] = None
        current_page: Optional[str] = None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        if not kwargs.link:
            raise ValueError("Navlink component requires a non-empty 'link' value.")

        # Get current_page from kwargs if provided, otherwise from context
        current_page = kwargs.current_page
        if current_page is None and context:
            current_page = context.get("current_page")

        return {
            "link": kwargs.link,
            "icon": kwargs.icon,
            "text": kwargs.text,
            "page_name": kwargs.page_name,
            "current_page": current_page,
        }
