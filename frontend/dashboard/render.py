import json
from typing import Any

from django.shortcuts import render


def starshield_render(request, template_name, context={}, page_name="", hx_triggers=None):
    """
    Render basique de django, avec un contexte par defaut (page_name, et autres)
    """
    base_context: dict[str, Any] = {
        "current_page": str(page_name),
    }

    # On render la page
    context.update(base_context)
    response = render(request, template_name, context)

    # Si des triggers sont passés en paramètre, on les ajoute au response
    if hx_triggers:
        # On filtre les triggers qui sont à False
        filtered_triggers = {key: value for key, value in hx_triggers.items() if value is True}
        if not filtered_triggers:
            return response

        response["HX-Trigger"] = json.dumps(filtered_triggers)

    return response
