from django import template

register = template.Library()


@register.filter
def after_original(value):
    """
    Filter that extracts text after "(Original)" string.
    If "(Original)" is found, returns everything after it.
    Otherwise, returns the original value.
    """
    if not value:
        return value

    if "(Original)" in value:
        parts = value.split("(Original)", 1)
        if len(parts) > 1:
            return parts[1].strip()

    return value
