"""Traitement des documents PDF : lecture, recherche, découpage, filigrane, chiffrement."""

import io
import unicodedata
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import DependencyError, PyPdfError
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from fichiers import preparer_dossier

TEXTE_FILIGRANE = "CONFIDENTIEL"
LONGUEUR_EXTRAIT = 90
ALGORITHME_CHIFFREMENT = "AES-256"
MESSAGE_DEPENDANCE_MANQUANTE = (
    "la bibliothèque « cryptography » est nécessaire au chiffrement AES des PDF. "
    "Installez-la avec : pip install -r requirements.txt"
)


class ErreurPdf(Exception):
    """Erreur levée lorsqu'un document PDF ne peut pas être lu ou traité."""


def ouvrir_pdf(source, mot_de_passe=None):
    """Ouvre un PDF en vérifiant qu'il existe, qu'il est lisible et non vide."""
    source = Path(source)
    if not source.is_file():
        raise ErreurPdf(f"PDF absent : {source}")
    if source.stat().st_size == 0:
        raise ErreurPdf(f"PDF vide (fichier de 0 octet) : {source.name}")

    try:
        lecteur = PdfReader(str(source))
    except (PyPdfError, OSError, ValueError) as erreur:
        raise ErreurPdf(f"PDF illisible ou corrompu ({source.name}) : {erreur}") from erreur

    if lecteur.is_encrypted:
        if not mot_de_passe:
            raise ErreurPdf(
                f"PDF protégé par mot de passe : {source.name}. "
                "Fournissez le mot de passe pour l'ouvrir."
            )
        try:
            if not lecteur.decrypt(mot_de_passe):
                raise ErreurPdf(f"Mot de passe incorrect pour : {source.name}")
        except DependencyError as erreur:
            raise ErreurPdf(
                f"Déchiffrement impossible ({source.name}) : {MESSAGE_DEPENDANCE_MANQUANTE}"
            ) from erreur
        except (PyPdfError, NotImplementedError) as erreur:
            raise ErreurPdf(f"Déchiffrement impossible ({source.name}) : {erreur}") from erreur

    if len(lecteur.pages) == 0:
        raise ErreurPdf(f"PDF vide (aucune page) : {source.name}")

    return lecteur


def nombre_de_pages(source, mot_de_passe=None):
    """Retourne le nombre de pages d'un document PDF."""
    return len(ouvrir_pdf(source, mot_de_passe).pages)


def lire_pages_texte(source, mot_de_passe=None):
    """Retourne la liste du texte extrait de chaque page."""
    lecteur = ouvrir_pdf(source, mot_de_passe)
    pages = []
    for numero, page in enumerate(lecteur.pages, start=1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as erreur:  # une page endommagée ne doit pas tout interrompre
            print(f"[pdf] Page {numero} illisible, ignorée ({erreur}).")
            pages.append("")
    return pages


def _normaliser(texte):
    """Met le texte en minuscules et retire les accents, sans changer sa longueur.

    Conserver la longueur permet de retrouver la position exacte du mot-clé dans
    le texte d'origine afin d'en afficher un extrait lisible.
    """
    caracteres = []
    for caractere in texte.lower():
        decompose = unicodedata.normalize("NFD", caractere)
        sans_accent = "".join(c for c in decompose if not unicodedata.combining(c))
        caracteres.append(sans_accent[0] if sans_accent else caractere)
    return "".join(caracteres)


def rechercher_mot_cle(source, mot_cle, mot_de_passe=None):
    """Recherche un mot-clé dans un PDF et retourne les pages contenant ce mot.

    La recherche ignore la casse et les accents.
    """
    if not mot_cle or not mot_cle.strip():
        raise ValueError("Le mot-clé recherché ne peut pas être vide.")

    mot_cle = mot_cle.strip()
    resultats = []
    pages = lire_pages_texte(source, mot_de_passe)

    if not any(pages):
        raise ErreurPdf(
            f"Aucun texte extractible dans {Path(source).name} "
            "(document vide ou constitué d'images)."
        )

    mot_normalise = _normaliser(mot_cle)
    for numero, texte in enumerate(pages, start=1):
        texte_normalise = _normaliser(texte)
        occurrences = texte_normalise.count(mot_normalise)
        if occurrences:
            position = texte_normalise.find(mot_normalise)
            debut = max(0, position - LONGUEUR_EXTRAIT // 2)
            extrait = " ".join(texte[debut : debut + LONGUEUR_EXTRAIT].split())
            resultats.append({"page": numero, "occurrences": occurrences, "extrait": extrait})

    return resultats


def _valider_plage(debut, fin, total):
    try:
        debut, fin = int(debut), int(fin)
    except (TypeError, ValueError) as erreur:
        raise ValueError("Les numéros de page doivent être des entiers.") from erreur

    if debut < 1 or fin < 1:
        raise ValueError(f"Numéro de page incorrect : la numérotation commence à 1 (reçu {debut}-{fin}).")
    if debut > fin:
        raise ValueError(f"Plage incorrecte : la page de début ({debut}) dépasse celle de fin ({fin}).")
    if fin > total:
        raise ValueError(f"Numéro de page incorrect : le document ne contient que {total} page(s).")
    return debut, fin


def extraire_plage_pages(source, debut, fin, destination, mot_de_passe=None):
    """Extrait une plage de pages (numérotation humaine, de 1 à N) vers un nouveau PDF."""
    lecteur = ouvrir_pdf(source, mot_de_passe)
    debut, fin = _valider_plage(debut, fin, len(lecteur.pages))

    redacteur = PdfWriter()
    for index in range(debut - 1, fin):
        redacteur.add_page(lecteur.pages[index])

    destination = preparer_dossier(destination)
    try:
        with destination.open("wb") as fichier:
            redacteur.write(fichier)
    except (OSError, PyPdfError) as erreur:
        raise ErreurPdf(f"Écriture du PDF impossible ({destination}) : {erreur}") from erreur

    print(f"[pdf] Pages {debut} à {fin} extraites vers {destination.name}.")
    return destination


def diviser_pdf(source, dossier_sortie, pages_par_fichier=1, mot_de_passe=None):
    """Découpe un PDF en plusieurs fichiers et retourne la liste des fichiers créés."""
    if pages_par_fichier < 1:
        raise ValueError("Le nombre de pages par fichier doit être supérieur ou égal à 1.")

    lecteur = ouvrir_pdf(source, mot_de_passe)
    dossier_sortie = Path(dossier_sortie)
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    base = Path(source).stem

    fichiers = []
    total = len(lecteur.pages)
    for debut in range(0, total, pages_par_fichier):
        fin = min(debut + pages_par_fichier, total)
        redacteur = PdfWriter()
        for index in range(debut, fin):
            redacteur.add_page(lecteur.pages[index])

        destination = dossier_sortie / f"{base}_pages_{debut + 1}-{fin}.pdf"
        try:
            with destination.open("wb") as fichier:
                redacteur.write(fichier)
        except (OSError, PyPdfError) as erreur:
            raise ErreurPdf(f"Écriture du PDF impossible ({destination}) : {erreur}") from erreur
        fichiers.append(destination)

    print(f"[pdf] Document découpé en {len(fichiers)} fichier(s) dans {dossier_sortie.name}/.")
    return fichiers


def _page_filigrane(largeur, hauteur, texte):
    """Construit en mémoire une page PDF ne contenant que le filigrane."""
    tampon = io.BytesIO()
    dessin = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
    dessin.saveState()
    dessin.setFont("Helvetica-Bold", max(28, int(min(largeur, hauteur) / 10)))
    dessin.setFillColor(Color(0.6, 0.1, 0.1, alpha=0.25))
    dessin.translate(largeur / 2, hauteur / 2)
    dessin.rotate(45)
    dessin.drawCentredString(0, 0, texte)
    dessin.restoreState()
    dessin.save()
    tampon.seek(0)
    return PdfReader(tampon).pages[0]


def ajouter_filigrane(source, destination, texte=TEXTE_FILIGRANE, mot_de_passe=None):
    """Ajoute un filigrane sur toutes les pages d'un PDF."""
    lecteur = ouvrir_pdf(source, mot_de_passe)
    redacteur = PdfWriter()

    for page in lecteur.pages:
        largeur = float(page.mediabox.width)
        hauteur = float(page.mediabox.height)
        try:
            page.merge_page(_page_filigrane(largeur, hauteur, texte))
        except Exception as erreur:
            raise ErreurPdf(f"Ajout du filigrane impossible : {erreur}") from erreur
        redacteur.add_page(page)

    destination = preparer_dossier(destination)
    try:
        with destination.open("wb") as fichier:
            redacteur.write(fichier)
    except (OSError, PyPdfError) as erreur:
        raise ErreurPdf(f"Écriture du PDF impossible ({destination}) : {erreur}") from erreur

    print(f"[pdf] Filigrane « {texte} » appliqué sur {len(lecteur.pages)} page(s).")
    return destination


def chiffrer_pdf(source, destination, mot_de_passe, mot_de_passe_source=None):
    """Protège un PDF par un mot de passe saisi par l'utilisateur."""
    if not mot_de_passe:
        raise ValueError("Le mot de passe de chiffrement ne peut pas être vide.")

    lecteur = ouvrir_pdf(source, mot_de_passe_source)
    redacteur = PdfWriter()
    for page in lecteur.pages:
        redacteur.add_page(page)

    try:
        redacteur.encrypt(mot_de_passe, algorithm=ALGORITHME_CHIFFREMENT)
    except DependencyError as erreur:
        raise ErreurPdf(f"Chiffrement impossible : {MESSAGE_DEPENDANCE_MANQUANTE}") from erreur
    except (PyPdfError, NotImplementedError, ValueError) as erreur:
        raise ErreurPdf(f"Chiffrement impossible : {erreur}") from erreur

    destination = preparer_dossier(destination)
    try:
        with destination.open("wb") as fichier:
            redacteur.write(fichier)
    except (OSError, PyPdfError) as erreur:
        raise ErreurPdf(f"Écriture du PDF impossible ({destination}) : {erreur}") from erreur

    print(f"[pdf] Document chiffré : {destination.name}")
    return destination
