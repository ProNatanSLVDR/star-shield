from audioop import avg
from django.shortcuts import redirect
from django.db.models import Avg, Q
from django.utils import timezone
from datetime import timedelta
from auths.models import Etablissement
from apps.reviews.models import Review
from apps.dashboard.render import starshield_render
from starshield.decorators import google_gmb_connected_required, selected_etablissement_required


@google_gmb_connected_required
@selected_etablissement_required
def overview_view(request):


    request.etablissement.update_reviews()
    

    context = {
        "etablissement": request.etablissement,
    }
    
    return starshield_render(request, "etablissement/overview.html", context=context, page_name="etablissement")





