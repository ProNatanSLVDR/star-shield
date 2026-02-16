from django_components import Component, register


@register("etablissement_selector")
class EtablissementSelector(Component):
    template_file = "template.html"

    def get_template_data(self, args, kwargs, slots, context):
        request = context.get("request")
        count = 0
        if request and hasattr(request.user, "google_credential") and request.user.google_credential:
            count = request.user.google_credential.etablissements.count()
        return {"etablissement_count": count}
