"""Traitement des images : vérification, redimensionnement sans déformation."""

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from fichiers import preparer_dossier

TAILLE_MAXIMALE = (800, 800)
FORMATS_ACCEPTES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}


class ErreurImage(Exception):
    """Erreur levée lorsqu'une image est absente, corrompue ou non prise en charge."""


def ouvrir_image(source):
    """Ouvre une image en vérifiant son existence, son format et son intégrité."""
    source = Path(source)
    if not source.is_file():
        raise ErreurImage(f"Image absente : {source}")
    if source.suffix.lower() not in FORMATS_ACCEPTES:
        raise ErreurImage(
            f"Format non pris en charge : {source.suffix or 'sans extension'} "
            f"(formats acceptés : {', '.join(sorted(FORMATS_ACCEPTES))})"
        )

    try:
        image = Image.open(source)
        image.load()
    except UnidentifiedImageError as erreur:
        raise ErreurImage(f"Image corrompue ou format non reconnu : {source.name}") from erreur
    except (OSError, ValueError) as erreur:
        raise ErreurImage(f"Lecture impossible de {source.name} : {erreur}") from erreur

    return image


def informations_image(source):
    """Retourne les caractéristiques principales d'une image."""
    image = ouvrir_image(source)
    return {
        "nom": Path(source).name,
        "format": image.format,
        "mode": image.mode,
        "largeur": image.width,
        "hauteur": image.height,
    }


def redimensionner_image(source, destination, taille_maximale=TAILLE_MAXIMALE, qualite=85):
    """Redimensionne une image en conservant ses proportions (aucune déformation).

    L'image est réduite pour tenir dans le cadre ``taille_maximale`` ; le rapport
    largeur/hauteur d'origine est préservé.
    """
    image = ouvrir_image(source)
    largeur_origine, hauteur_origine = image.size

    destination = preparer_dossier(destination)
    if destination.suffix.lower() in {".jpg", ".jpeg"} and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    copie = image.copy()
    copie.thumbnail(taille_maximale, Image.LANCZOS)

    try:
        if destination.suffix.lower() in {".jpg", ".jpeg"}:
            copie.save(destination, quality=qualite, optimize=True)
        else:
            copie.save(destination)
    except (OSError, ValueError, KeyError) as erreur:
        raise ErreurImage(f"Enregistrement impossible ({destination.name}) : {erreur}") from erreur

    print(
        f"[image] {Path(source).name} : {largeur_origine}x{hauteur_origine} px "
        f"-> {copie.width}x{copie.height} px (proportions conservées)."
    )
    return destination
