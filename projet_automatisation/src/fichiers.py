"""Gestion des chemins, des dossiers et des fichiers CSV du projet."""

import csv
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parent.parent

DOSSIERS = {
    "data": RACINE_PROJET / "data",
    "images": RACINE_PROJET / "images",
    "pdf": RACINE_PROJET / "pdf",
    "exports": RACINE_PROJET / "exports",
}

ENCODAGE_CSV = "utf-8-sig"


def chemin(nom_dossier, nom_fichier=None):
    """Retourne le chemin d'un dossier du projet, ou d'un fichier qu'il contient."""
    if nom_dossier not in DOSSIERS:
        raise ValueError(
            f"Dossier inconnu : {nom_dossier!r}. "
            f"Valeurs attendues : {', '.join(sorted(DOSSIERS))}"
        )
    dossier = DOSSIERS[nom_dossier]
    return dossier if nom_fichier is None else dossier / nom_fichier


def creer_dossiers():
    """Crée les dossiers de travail du projet s'ils n'existent pas encore."""
    crees = []
    for nom, dossier in DOSSIERS.items():
        try:
            if not dossier.exists():
                crees.append(nom)
            dossier.mkdir(parents=True, exist_ok=True)
        except OSError as erreur:
            raise OSError(f"Impossible de créer le dossier {dossier} : {erreur}") from erreur
    return crees


def preparer_dossier(destination):
    """Crée le dossier parent d'un fichier de sortie et retourne le chemin."""
    destination = Path(destination)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as erreur:
        raise OSError(
            f"Impossible de préparer le dossier {destination.parent} : {erreur}"
        ) from erreur
    return destination


def ecrire_csv(lignes, destination, entetes=None):
    """Écrit une liste de dictionnaires dans un fichier CSV et retourne son chemin."""
    if not lignes:
        raise ValueError("Aucune donnée à écrire : la liste de lignes est vide.")

    destination = preparer_dossier(destination)
    if entetes is None:
        entetes = list(lignes[0].keys())

    try:
        with destination.open("w", encoding=ENCODAGE_CSV, newline="") as fichier:
            redacteur = csv.DictWriter(fichier, fieldnames=entetes, delimiter=";")
            redacteur.writeheader()
            redacteur.writerows(lignes)
    except (OSError, csv.Error) as erreur:
        raise OSError(f"Écriture du CSV impossible ({destination}) : {erreur}") from erreur

    return destination


def lire_csv(source):
    """Lit un fichier CSV produit par le projet et retourne une liste de dictionnaires."""
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"Fichier CSV introuvable : {source}")

    try:
        with source.open("r", encoding=ENCODAGE_CSV, newline="") as fichier:
            return list(csv.DictReader(fichier, delimiter=";"))
    except (OSError, UnicodeDecodeError, csv.Error) as erreur:
        raise OSError(f"Lecture du CSV impossible ({source}) : {erreur}") from erreur


def enregistrer_texte(contenu, destination):
    """Enregistre un contenu texte (HTML brut, journal, rapport) sur le disque."""
    destination = preparer_dossier(destination)
    try:
        destination.write_text(contenu, encoding="utf-8")
    except OSError as erreur:
        raise OSError(f"Écriture impossible ({destination}) : {erreur}") from erreur
    return destination


def chemin_relatif(cible):
    """Affiche un chemin relatif à la racine du projet pour des messages lisibles."""
    cible = Path(cible)
    try:
        return str(cible.relative_to(RACINE_PROJET))
    except ValueError:
        return str(cible)


def taille_lisible(cible):
    """Retourne la taille d'un fichier dans une unité lisible (Ko, Mo...)."""
    cible = Path(cible)
    if not cible.is_file():
        return "0 o"

    taille = float(cible.stat().st_size)
    for unite in ("o", "Ko", "Mo", "Go"):
        if taille < 1024 or unite == "Go":
            return f"{taille:.1f} {unite}" if unite != "o" else f"{int(taille)} o"
        taille /= 1024
    return f"{taille:.1f} Go"
