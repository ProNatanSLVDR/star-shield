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

    kept_text = value

    if "(Original)" in value:
        parts = value.split("(Original)", 1)
        if len(parts) > 1:
            kept_text = parts[1].strip()

    if "(Translated by Google)" in value:
        kept_text = kept_text.split("(Translated by Google)", 1)[0].strip()

    return kept_text
