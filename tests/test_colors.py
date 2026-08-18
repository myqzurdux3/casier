"""Teintes des casiers : table de référence partagée avec le client mobile.

`mobile/tests/categoryColor.test.js` vérifie exactement la même table côté
TypeScript. Rien n'exécute les deux langages dans un même processus — pytest
d'un côté, `node --test` de l'autre — donc c'est cette table qui tient lieu de
contrat : si l'une des deux implémentations dérive, son test tombe.

Les clés couvrent les vingt catégories réelles de `config.py`, les tranches
d'années et une référence, plus une clé accentuée pour couvrir l'encodage
UTF-8 — c'est le seul endroit où les deux implémentations pourraient diverger,
le TypeScript encodant les octets à la main.
"""

import pytest

from spotify_sort import config
from spotify_sort.colors import CATEGORY_COLORS, category_color

ATTENDU = {
    "chill": "#8E9BFF",
    "vibe": "#E8A33D",
    "fete": "#F276B8",
    "melancolie": "#7CD98A",
    "energie": "#F2795E",
    "romance": "#7CD98A",
    "rap-us": "#4FC9B0",
    "rap-uk": "#4FC9B0",
    "rap-fr": "#F276B8",
    "pop": "#F2795E",
    "rock": "#5CB4F2",
    "metal": "#5CB4F2",
    "electro": "#F276B8",
    "rnb-soul": "#F276B8",
    "jazz-blues": "#F2795E",
    "reggae-afro": "#F276B8",
    "latino": "#7CD98A",
    "country-folk": "#7CD98A",
    "classique-instrumental": "#C68CF5",
    "chanson-francaise": "#F2795E",
    "2010s": "#F276B8",
    "2020s": "#7CD98A",
    "white-girl-music": "#8E9BFF",
    "accentué-é": "#E8A33D",
}


@pytest.mark.parametrize(("cle", "teinte"), sorted(ATTENDU.items()))
def test_teinte_conforme_a_la_table(cle, teinte):
    assert category_color(cle) == teinte


def test_toutes_les_categories_reelles_sont_couvertes():
    """La table doit suivre config.py : une catégorie ajoutée doit y entrer."""
    reelles = set(config.MOODS) | set(config.GENRES)
    assert reelles <= set(ATTENDU), f"absentes de la table : {sorted(reelles - set(ATTENDU))}"


def test_teinte_stable_entre_deux_appels():
    """Pas de cache, pas d'aléa : la fonction est purement dérivée de la clé."""
    assert category_color("rap-uk") == category_color("rap-uk")


def test_teinte_toujours_dans_la_palette():
    for cle in ATTENDU:
        assert category_color(cle) in CATEGORY_COLORS


def test_l_accent_d_action_n_est_pas_une_teinte_de_casier():
    """#D7E63B veut dire « on peut appuyer » ; aucun casier ne doit le porter."""
    assert "#D7E63B" not in CATEGORY_COLORS
