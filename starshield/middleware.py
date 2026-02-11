import json

from django.contrib.messages import get_messages
from django.utils.deprecation import MiddlewareMixin

from apps.private.auths.models import Etablissement


class CustomMessageMiddleware(MiddlewareMixin):
    """
    Middleware that adds messages to X-Messages header for all requests
    """

    def parse_messages(self, request):
        storage = get_messages(request)
        messages = []
        for message in storage:
            messages.append({"message": str(message.message), "tags": str(message.tags)})
        return messages

    def __call__(self, request):
        messages = self.parse_messages(request)
        request._custom_messages = messages
        response = self.get_response(request)

        if 300 <= response.status_code < 400:
            return response

        if messages:
            response.headers["X-Messages"] = json.dumps(messages)

        return response


class EtablissementMiddleware(MiddlewareMixin):
    """
    Middleware that adds the selected etablissement to the request
    """

    def __call__(self, request):
        etablissement_id = request.session.get("selected_etablissement")
        if etablissement_id and hasattr(request, "user") and request.user.is_authenticated:
            etablissement = Etablissement.objects.filter(
                id=etablissement_id,
                google_credential__user=request.user,
            ).first()
            if etablissement:
                request.etablissement = etablissement
            else:
                del request.session["selected_etablissement"]

        return self.get_response(request)
