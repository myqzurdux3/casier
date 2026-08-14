#!/usr/bin/env python3
"""Génère les icônes de l'app.

Motif : trois barres de longueurs croissantes — le tri — surmontées d'une note.
Volontairement distinct du logo Spotify, qui est une marque déposée et que les
Developer Terms interdisent d'employer comme icône d'application.

    python3 tools/make-icons.py

Produit assets/icon.png, assets/adaptive-icon.png et assets/splash-icon.png.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "assets"

FOND = (18, 18, 18, 255)
VERT = (29, 185, 84, 255)
TAILLE = 1024


def dessiner(draw: ImageDraw.ImageDraw, echelle: float, decalage: int) -> None:
    """Dessine le motif centré, mis à l'échelle.

    `echelle` < 1 laisse la marge que l'icône adaptative Android rogne : le
    système découpe un cercle dans le carré, et tout ce qui déborde disparaît.
    """
    def E(v: float) -> float:
        return v * echelle + decalage

    # Trois barres alignées à gauche, de la plus longue à la plus courte : une
    # liste triée. Les centrer individuellement donnerait une pyramide, qui ne
    # raconte rien.
    hauteur, ecart, gauche = 92, 54, 232
    haut = 500
    for index, largeur in enumerate((560, 430, 300)):
        y = haut + index * (hauteur + ecart)
        draw.rounded_rectangle(
            [E(gauche), E(y), E(gauche + largeur), E(y + hauteur)],
            radius=E(hauteur / 2),
            fill=VERT,
        )

    # Note de musique au-dessus, centrée sur le bloc de barres.
    draw.ellipse([E(392), E(286), E(568), E(418)], fill=VERT)      # tête
    draw.rounded_rectangle([E(524), E(150), E(572), E(360)], radius=E(24), fill=VERT)  # hampe
    draw.rounded_rectangle([E(524), E(150), E(668), E(198)], radius=E(24), fill=VERT)  # crochet


def carre(fond: tuple, echelle: float) -> Image.Image:
    image = Image.new("RGBA", (TAILLE, TAILLE), fond)
    marge = int(TAILLE * (1 - echelle) / 2)
    dessiner(ImageDraw.Draw(image), echelle, marge)
    return image


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    # Icône classique : le motif occupe presque tout le carré.
    carre(FOND, 0.86).save(ASSETS / "icon.png")

    # Icône adaptative : Android rogne jusqu'à un cercle inscrit, d'où une
    # échelle plus faible pour que rien d'utile ne soit coupé.
    carre(FOND, 0.62).save(ASSETS / "adaptive-icon.png")

    # Écran de démarrage : motif seul sur fond transparent, Expo pose la couleur.
    carre((0, 0, 0, 0), 0.62).save(ASSETS / "splash-icon.png")

    for nom in ("icon.png", "adaptive-icon.png", "splash-icon.png"):
        chemin = ASSETS / nom
        print(f"  {nom:<20} {Image.open(chemin).size}  {chemin.stat().st_size // 1024} Kio")


if __name__ == "__main__":
    main()
