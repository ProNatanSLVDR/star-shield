from django_components import Component, register


@register("etablissement_selector")
class EtablissementSelector(Component):
    template_file = "template.html"

    def get_template_data(self, args, kwargs, slots, context):
        return {}
