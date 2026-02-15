from typing import NamedTuple

from django_components import Component, register


@register("feature_toggle")
class FeatureToggle(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        feature_name: str
        icon: str
        feature_field: str
        feature_enabled: bool

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "feature_name": kwargs.feature_name,
            "icon": kwargs.icon,
            "feature_field": kwargs.feature_field,
            "feature_enabled": kwargs.feature_enabled,
        }
