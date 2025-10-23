from django.shortcuts import render

def overview_view(request):
    """
    Simple overview page for the etablissement.
    """
    return render(request, "etablissement/overview.html")
