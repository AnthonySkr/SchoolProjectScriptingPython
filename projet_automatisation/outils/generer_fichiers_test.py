"""Génère les fichiers de test du projet (PDF, images et page HTML locale).

Ce script ne fait pas partie de la chaîne d'automatisation : il sert uniquement à
recréer les fichiers d'entrée présents dans data/, pdf/ et images/.

Utilisation :
    python outils/generer_fichiers_test.py
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

RACINE = Path(__file__).resolve().parent.parent
MOT_DE_PASSE_FIXTURE = "demo2024"

LIVRES = [
    ("A Light in the Attic", "51.77", "In stock"),
    ("Tipping the Velvet", "53.74", "In stock"),
    ("Soumission", "50.10", "In stock"),
    ("Sharp Objects", "47.82", "In stock"),
    ("Sapiens: A Brief History of Humankind", "54.23", "In stock"),
    ("The Requiem Red", "22.65", "In stock"),
    ("The Dirty Little Secrets of Getting Your Dream Job", "33.34", "Out of stock"),
    ("The Coming Woman: A Novel Based on the Life of the Infamous", "17.93", "In stock"),
    ("The Boys in the Boat", "22.60", "In stock"),
    ("The Black Maria", "52.15", "Out of stock"),
]

CONTENU_PDF = [
    (
        "Catalogue de produits — rapport interne",
        [
            "Ce document de démonstration accompagne le projet de synthèse de "
            "Scripting Python. Il décrit le catalogue de produits collecté "
            "automatiquement sur le site de démonstration.",
            "Chaque produit du catalogue est décrit par un titre, un prix et une "
            "disponibilité. Ces trois informations sont enregistrées dans un fichier "
            "CSV exploitable par le service commercial.",
        ],
    ),
    (
        "Analyse des prix",
        [
            "Le prix moyen constaté sur la première page du catalogue est de 38,60 "
            "livres sterling. Le produit le plus cher est vendu 57,25 livres.",
            "Une variation de prix supérieure à 10 % entre deux collectes doit être "
            "signalée au responsable des achats.",
        ],
    ),
    (
        "Disponibilité des produits",
        [
            "La disponibilité de chaque produit est relevée à chaque exécution de la "
            "chaîne d'automatisation. Un produit indisponible reste présent dans le "
            "fichier CSV avec la mention correspondante.",
            "Le suivi de disponibilité permet d'anticiper les ruptures de stock.",
        ],
    ),
    (
        "Diffusion et confidentialité",
        [
            "Le document final porte un filigrane CONFIDENTIEL et il est protégé par "
            "un mot de passe saisi dans le terminal au moment de l'exécution.",
            "Le mot de passe n'est jamais enregistré dans le dépôt du projet ni dans "
            "le code source.",
        ],
    ),
]


def generer_page_html(destination):
    """Crée une page HTML locale reproduisant la structure du catalogue de démonstration."""
    articles = []
    for titre, prix, disponibilite in LIVRES:
        articles.append(
            f"""      <li>
        <article class="product_pod">
          <h3><a href="catalogue/{titre.lower().replace(' ', '-')[:30]}/index.html"
                 title="{titre}">{titre[:30]}</a></h3>
          <div class="product_price">
            <p class="price_color">&pound;{prix}</p>
            <p class="instock availability">{disponibilite}</p>
          </div>
        </article>
      </li>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Catalogue de démonstration</title>
</head>
<body>
  <section>
    <ol class="row">
{chr(10).join(articles)}
    </ol>
    <ul class="pager">
      <li class="next"><a href="page-2.html">next</a></li>
    </ul>
  </section>
</body>
</html>
"""
    destination.write_text(html, encoding="utf-8")
    print(f"HTML local  : {destination.relative_to(RACINE)}")


def generer_pdf_source(destination):
    """Crée un PDF de quatre pages contenant du texte recherchable."""
    document = SimpleDocTemplate(str(destination), pagesize=A4, title="Rapport produits")
    styles = getSampleStyleSheet()
    contenu = []

    for index, (titre, paragraphes) in enumerate(CONTENU_PDF):
        contenu.append(Paragraph(titre, styles["Title"] if index == 0 else styles["Heading1"]))
        contenu.append(Spacer(1, 18))
        for paragraphe in paragraphes:
            contenu.append(Paragraph(paragraphe, styles["BodyText"]))
            contenu.append(Spacer(1, 12))
        if index < len(CONTENU_PDF) - 1:
            contenu.append(PageBreak())

    document.build(contenu)
    print(f"PDF source  : {destination.relative_to(RACINE)}")


def generer_pdf_vide(destination):
    """Crée un PDF d'une page sans aucun texte extractible."""
    redacteur = PdfWriter()
    redacteur.add_blank_page(width=595, height=842)
    with destination.open("wb") as fichier:
        redacteur.write(fichier)
    print(f"PDF vide    : {destination.relative_to(RACINE)}")


def generer_pdf_protege(source, destination):
    """Crée une copie chiffrée du PDF source pour tester la gestion des documents protégés."""
    lecteur = PdfReader(str(source))
    redacteur = PdfWriter()
    for page in lecteur.pages:
        redacteur.add_page(page)
    redacteur.encrypt(MOT_DE_PASSE_FIXTURE, algorithm="AES-256")
    with destination.open("wb") as fichier:
        redacteur.write(fichier)
    print(f"PDF protégé : {destination.relative_to(RACINE)} (mot de passe : {MOT_DE_PASSE_FIXTURE})")


def generer_image(destination, largeur=1600, hauteur=900):
    """Crée une image de démonstration au format paysage."""
    image = Image.new("RGB", (largeur, hauteur), (18, 32, 58))
    dessin = ImageDraw.Draw(image)

    for position in range(0, hauteur, 4):
        teinte = int(40 + 120 * position / hauteur)
        dessin.line([(0, position), (largeur, position)], fill=(teinte // 3, teinte // 2, teinte))

    dessin.ellipse([200, 150, 700, 650], fill=(232, 178, 62))
    dessin.rectangle([850, 250, 1400, 700], fill=(214, 74, 74))
    dessin.polygon([(500, 800), (900, 500), (1300, 800)], fill=(70, 168, 132))
    dessin.text((60, 60), "Produit de demonstration", fill=(255, 255, 255))

    image.save(destination, quality=92)
    print(f"Image       : {destination.relative_to(RACINE)} ({largeur}x{hauteur})")


def generer_image_corrompue(destination):
    """Crée un fichier .png invalide pour tester la détection des images corrompues."""
    aleatoire = random.Random(2024)
    octets = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + bytes(aleatoire.randrange(256) for _ in range(512))
    destination.write_bytes(octets)
    print(f"Image KO    : {destination.relative_to(RACINE)}")


def generer_fichier_non_image(destination):
    """Crée un fichier texte placé dans images/ pour tester les formats non pris en charge."""
    destination.write_text(
        "Ce fichier n'est pas une image : il sert à tester le refus des formats "
        "non pris en charge par le module image_tools.\n",
        encoding="utf-8",
    )
    print(f"Format KO   : {destination.relative_to(RACINE)}")


def main():
    """Génère l'ensemble des fichiers de test dans data/, pdf/ et images/."""
    for nom in ("data", "pdf", "images", "exports"):
        (RACINE / nom).mkdir(parents=True, exist_ok=True)

    generer_page_html(RACINE / "data" / "catalogue_demo.html")
    pdf_source = RACINE / "pdf" / "rapport_produits.pdf"
    generer_pdf_source(pdf_source)
    generer_pdf_vide(RACINE / "pdf" / "document_vide.pdf")
    generer_pdf_protege(pdf_source, RACINE / "pdf" / "document_protege.pdf")
    generer_image(RACINE / "images" / "photo_produit.jpg")
    generer_image_corrompue(RACINE / "images" / "image_corrompue.png")
    generer_fichier_non_image(RACINE / "images" / "fichier_non_image.txt")
    print("\nFichiers de test générés.")


if __name__ == "__main__":
    main()
