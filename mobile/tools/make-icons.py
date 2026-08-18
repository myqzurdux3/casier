#!/usr/bin/env python3
"""Génère les icônes de l'app.

Le mark : un carré arrondi sombre contenant une grille 2×2 — quatre casiers,
dont un seul est rempli. Le carré est la forme qu'on retrouve partout dans
l'app, devant chaque nom de casier, et le jaune est celui de l'accent.

Volontairement sans rapport avec le logo Spotify, qui est une marque déposée
que les Developer Terms interdisent d'employer comme icône d'application.

    python3 tools/make-icons.py

Produit assets/icon.png, assets/adaptive-icon.png et assets/splash-icon.png.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"

FOND = (27, 29, 32, 255)        # --bg
PLAQUE = (35, 38, 42, 255)      # --surface
CONTOUR = (110, 117, 124, 255)  # --faint
ACCENT = (215, 230, 59, 255)    # --accent

TAILLE = 1024

# Le motif est décrit sur une grille de 64, puis mis à l'échelle. C'est l'unité
# dans laquelle les proportions se lisent : rayon 14/64 ≈ 22 % du côté.
UNITE = 64
RAYON = 14
GOUTTIERE = 4
# Retrait de la grille dans la plaque. Ce qui reste, moins la gouttière, se
# partage en deux cellules carrées : (64 - 2×14 - 4) / 2 = 16.
RETRAIT = 14
CELLULE = (UNITE - 2 * RETRAIT - GOUTTIERE) / 2
TRAIT = 2


def dessiner(draw: ImageDraw.ImageDraw, cote: float, decalage: float) -> None:
    """Dessine le mark, mis à l'échelle sur `cote` et décalé de `decalage`."""

    def E(v: float) -> float:
        return v * cote / UNITE + decalage

    draw.rounded_rectangle(
        [E(0), E(0), E(UNITE), E(UNITE)], radius=E(RAYON) - decalage, fill=PLAQUE
    )

    # Trois casiers vides, un rempli. Le rempli est en bas à gauche : c'est là
    # que l'œil se pose en dernier, et il doit rester le point d'arrivée.
    for ligne in (0, 1):
        for colonne in (0, 1):
            x = RETRAIT + colonne * (CELLULE + GOUTTIERE)
            y = RETRAIT + ligne * (CELLULE + GOUTTIERE)
            boite = [E(x), E(y), E(x + CELLULE), E(y + CELLULE)]
            if (ligne, colonne) == (1, 0):
                draw.rectangle(boite, fill=ACCENT)
            else:
                draw.rectangle(boite, outline=CONTOUR, width=max(1, round(E(TRAIT) - decalage)))


def carre(fond: tuple, echelle: float) -> Image.Image:
    image = Image.new("RGBA", (TAILLE, TAILLE), fond)
    cote = TAILLE * echelle
    dessiner(ImageDraw.Draw(image), cote, (TAILLE - cote) / 2)
    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    # Icône classique : le mark occupe presque tout le carré.
    carre(FOND, 0.86).save(ASSETS / "icon.png")

    # Icône adaptative : Android rogne le premier plan jusqu'à un cercle, et ne
    # garantit que les deux tiers centraux (72 dp visibles sur 108). Le fond est
    # posé par `android.adaptiveIcon.backgroundColor`, d'où le calque transparent.
    carre((0, 0, 0, 0), 0.66).save(ASSETS / "adaptive-icon.png")

    # Écran de démarrage : mark seul, Expo pose la couleur derrière.
    carre((0, 0, 0, 0), 0.62).save(ASSETS / "splash-icon.png")

    for nom in ("icon.png", "adaptive-icon.png", "splash-icon.png"):
        chemin = ASSETS / nom
        print(f"  {nom:<20} {Image.open(chemin).size}  {chemin.stat().st_size // 1024} Kio")


if __name__ == "__main__":
    main()
