"""Une teinte stable par casier, côté serveur.

Jumeau de `mobile/lib/categoryColor.ts` : le panel web et l'app doivent afficher
exactement les mêmes couleurs. La teinte vient de la *clé* de catégorie, qui ne
bouge pas, et non du nom affiché, qui peut être renommé à volonté.

`tests/test_colors.py` fige la table des clés réelles ; son jumeau
`mobile/tests/categoryColor.test.js` vérifie la même table côté TypeScript.
"""

# Huit teintes à luminosité constante. Le jaune-vert manque volontairement : il
# appartient à l'accent d'action, qui veut dire « on peut appuyer ».
CATEGORY_COLORS = [
    "#F2795E", "#E8A33D", "#7CD98A", "#4FC9B0",
    "#5CB4F2", "#8E9BFF", "#C68CF5", "#F276B8",
]


def category_color(key: str) -> str:
    """Teinte d'un casier, dérivée de sa clé par un FNV-1a 32 bits."""
    h = 0x811C9DC5
    for b in key.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return CATEGORY_COLORS[h % len(CATEGORY_COLORS)]
