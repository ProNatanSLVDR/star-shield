from datetime import timedelta

from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.private.auths.models import Etablissement


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
    if stars == "TWO":
        return 2
    if stars == "THREE":
        return 3
    if stars == "FOUR":
        return 4
    if stars == "FIVE":
        return 5
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
            raise Http404() from None
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
        "review_accent_color": etablissement.review_accent_color or "#0066ff",
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


distribution_notes = {
    5: {
        5: 1,
    },
    4: {
        5: 3 / 4,
        4: 1 / 4,
    },
    3: {
        5: 3 / 4,
        4: 2 / 12,
        3: 1 / 12,
    },
}


def estimations(note_actuelle: float, nb_notes: int, objectif: float, notes_par_semaine) -> dict:
    def moyenne(liste_notes: list[int]) -> float:
        return sum(liste_notes) / len(liste_notes)

    def generate_weekly_notes(threshold: int, notes_par_semaine: int) -> list[int]:
        items = list(distribution_notes[threshold].items())
        calculated_weekly_notes = []
        remaining = notes_par_semaine

        for i, (note, percentage) in enumerate(items):
            if i == len(items) - 1:
                count = remaining
            else:
                count = round(percentage * notes_par_semaine)
                remaining -= count
            calculated_weekly_notes.extend([note] * count)
        return calculated_weekly_notes

    test_array = [note_actuelle] * nb_notes

    results = {
        "at_threshold_3": None,
        "at_threshold_4": None,
        "at_threshold_5": None,
    }

    # on teste chaque seuil
    for threshold in distribution_notes:
        weekly_notes = generate_weekly_notes(threshold, notes_par_semaine)

        # on copie le tableau de notes
        new_test_array = test_array.copy()

        # on fait 270 tours de boucle pour simuler 5 ans max
        for i in range(270):
            new_test_array.extend(weekly_notes)

            if moyenne(new_test_array) >= objectif:
                print(f"{i} semaines pour atteindre l'objectif, threshold: {threshold}")
                results[f"at_threshold_{threshold}"] = i
                break

    return results
