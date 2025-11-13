from django.urls import reverse
from auths.models import Etablissement
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
from .models import ReviewAnalytics


def calcul_objectif(noteactu: float, nb_notes: int, objectif: float) -> float:
    """
    trouve le nombre de notes pour atteindre l'objetif
    """

    def moyenne(liste_notes: list[int]) -> float:
        return sum(liste_notes) / len(liste_notes)

    NOTES_POSSIBLES = [1, 2, 3, 4, 5]

    notes_potential_list = []

    # on determine les notes qui peuvent faire monter la moyenne
    for note in NOTES_POSSIBLES:
        if note > objectif:
            notes_potential_list.append(note)

    print(f"notes potential list: {notes_potential_list}")

    results = {
        "1_stars_needed": None,
        "2_stars_needed": None,
        "3_stars_needed": None,
        "4_stars_needed": None,
        "5_stars_needed": None,
    }

    # on determine le nombre de notes pour atteindre l'objetif
    for note in notes_potential_list:
        # on met a 0 les vars pour ce test
        test_array = [noteactu] * nb_notes
        nb_notes_to_add = 0

        # tant qu'on passe pas les
        while moyenne(test_array) < objectif:
            test_array.append(note)
            nb_notes_to_add += 1

        results[f"{note}_stars_needed"] = nb_notes_to_add

    print(results)

    return results


# calcul_objectif(noteactu=3.2, nb_notes=12, objectif=4.7)


def google_stars_to_number(stars: str) -> int:
    """
    convertit les étoiles Google en nombre
    """

    if stars == "ONE":
        return 1
    elif stars == "TWO":
        return 2
    elif stars == "THREE":
        return 3
    elif stars == "FOUR":
        return 4
    elif stars == "FIVE":
        return 5
    else:
        return 0


def get_etablissement_by_identifier(identifier: str) -> Etablissement | None:
    if not identifier:
        raise Http404()
    try:
        etablissement = Etablissement.objects.get(slug=identifier)
    except Etablissement.DoesNotExist:
        try:
            etablissement = Etablissement.objects.get(uuid=identifier)
        except (Etablissement.DoesNotExist, ValueError):
            raise Http404()
    return etablissement


def build_feedback_context(etablissement, identifier, mode="main", form=None, prefilled_rating=None) -> dict:
    """
    Build the context dictionary for the feedback page template.

    Args:
        etablissement: The Etablissement instance
        identifier: The identifier (UUID or slug) for building URLs

    Returns:
        dict: Context dictionary with etablissement, rating_array, and URLs
    """
    # Build rating array (same logic as feedback_view)
    rating_array = []
    for i in range(1, 6):
        if i >= etablissement.review_threshold:
            rating_array.append(True)
        else:
            rating_array.append(False)

    context = {
        "etablissement": etablissement,
        "rating_array": rating_array,
        "internal_feedback_url": reverse("reviews:internal_feedback", args=[identifier]),
        "external_feedback_url": reverse("reviews:external_feedback", args=[identifier]),
        "form": form,
        "prefilled_rating": prefilled_rating,
        "mode": mode,
        "review_show_etablissement_pill": etablissement.review_show_etablissement_pill,
        "review_accent_color": etablissement.review_accent_color or "#0b5ed7",
    }

    return context


def get_valid_session_key(request, key: str, valid_minutes: int = 5) -> str | None:
    key_time = request.session.get(f"{key}_save_time")
    key_value = request.session.get(key)

    save_time = parse_datetime(key_time) if key_time else None

    is_valid = save_time and save_time > timezone.now() - timedelta(minutes=valid_minutes)
    if is_valid:
        return key_value

    return None


def set_valid_session_key(request, key: str, value: str) -> None:
    request.session[f"{key}_save_time"] = str(timezone.now())
    request.session[key] = value
    request.session.modified = True
