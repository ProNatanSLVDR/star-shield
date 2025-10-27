def calcul_objectif(noteactu: float, nb_notes: int, objectif: float) -> float:
    """
    trouve le nombre de notes pour atteindre l'objetif
    """
    def moyenne(liste_notes: list[int]) -> float:
        return sum(liste_notes) / len(liste_notes)

    NOTES_POSSIBLES = [1, 2, 3, 4, 5]

    notes_potential_list = []

    # on determine les notes qui peuvent faire monter la moyenne
    for note in NOTES_POSSIBLES :
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

#calcul_objectif(noteactu=3.2, nb_notes=12, objectif=4.7)


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