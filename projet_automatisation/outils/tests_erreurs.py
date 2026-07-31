"""Vérification des cas d'erreur obligatoires du projet.

Chaque test provoque volontairement une erreur et vérifie que la chaîne
d'automatisation la détecte, la traite et affiche un message clair.

Utilisation :
    python outils/tests_erreurs.py
"""

import smtplib
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from pypdf.errors import DependencyError

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

import email_tools
import image_tools
import pdf_tools
import scraping

PDF_SOURCE = RACINE / "pdf" / "rapport_produits.pdf"
PDF_VIDE = RACINE / "pdf" / "document_vide.pdf"
PDF_PROTEGE = RACINE / "pdf" / "document_protege.pdf"
IMAGE_CORROMPUE = RACINE / "images" / "image_corrompue.png"
FICHIER_NON_IMAGE = RACINE / "images" / "fichier_non_image.txt"

resultats = []


def verifier(intitule, exception_attendue, action):
    """Exécute une action censée échouer et contrôle l'erreur obtenue."""
    try:
        action()
    except exception_attendue as erreur:
        print(f"  OK   {intitule}\n       -> {erreur}")
        resultats.append(True)
        return
    except Exception as erreur:  # erreur d'un type inattendu : le test échoue
        print(f"  ÉCHEC {intitule}\n       -> exception inattendue : {type(erreur).__name__} : {erreur}")
        resultats.append(False)
        return
    print(f"  ÉCHEC {intitule}\n       -> aucune erreur levée alors qu'une erreur était attendue")
    resultats.append(False)


class ServeurErreurHTTP(BaseHTTPRequestHandler):
    """Petit serveur local qui répond systématiquement par un code 404."""

    def do_GET(self):
        self.send_error(404, "Not Found")

    def log_message(self, *arguments):
        pass


def demarrer_serveur_local():
    serveur = HTTPServer(("127.0.0.1", 0), ServeurErreurHTTP)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur


def port_libre():
    """Retourne un numéro de port sur lequel aucun service n'écoute."""
    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        return prise.getsockname()[1]


class SmtpQuiRefuseAuthentification:
    """Faux serveur SMTP utilisé pour reproduire une erreur d'authentification."""

    def __init__(self, *arguments, **parametres):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False

    def starttls(self, **parametres):
        return 220, b"ready"

    def login(self, utilisateur, mot_de_passe):
        raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    def send_message(self, message):
        raise AssertionError("L'envoi ne doit pas avoir lieu après un échec d'authentification.")


def tester_scraping():
    print("\n[1] Collecte Web")
    verifier(
        "URL inaccessible (nom de domaine inexistant)",
        scraping.ErreurScraping,
        lambda: scraping.telecharger_page("https://domaine-qui-nexiste-pas-1234.invalid/", delai=5),
    )

    serveur = demarrer_serveur_local()
    adresse = f"http://127.0.0.1:{serveur.server_port}/catalogue"
    verifier(
        "Réponse HTTP incorrecte (404)",
        scraping.ErreurScraping,
        lambda: scraping.telecharger_page(adresse, delai=5),
    )
    serveur.shutdown()

    verifier(
        "Page HTML sans produit (structure inattendue)",
        scraping.ErreurScraping,
        lambda: scraping.extraire_produits("<html><body><p>Rien ici</p></body></html>"),
    )
    verifier(
        "Page locale absente",
        scraping.ErreurScraping,
        lambda: scraping.lire_page_locale(RACINE / "data" / "fichier_inexistant.html"),
    )


def tester_pdf():
    print("\n[2] Documents PDF")
    verifier(
        "PDF absent",
        pdf_tools.ErreurPdf,
        lambda: pdf_tools.ouvrir_pdf(RACINE / "pdf" / "document_inexistant.pdf"),
    )
    verifier(
        "PDF sans texte extractible",
        pdf_tools.ErreurPdf,
        lambda: pdf_tools.rechercher_mot_cle(PDF_VIDE, "produit"),
    )
    verifier(
        "PDF protégé sans mot de passe",
        pdf_tools.ErreurPdf,
        lambda: pdf_tools.ouvrir_pdf(PDF_PROTEGE),
    )
    verifier(
        "PDF protégé avec un mot de passe erroné",
        pdf_tools.ErreurPdf,
        lambda: pdf_tools.ouvrir_pdf(PDF_PROTEGE, mot_de_passe="mauvais_mot_de_passe"),
    )
    verifier(
        "Numéro de page trop grand",
        ValueError,
        lambda: pdf_tools.extraire_plage_pages(PDF_SOURCE, 1, 99, RACINE / "exports" / "test.pdf"),
    )
    verifier(
        "Numéro de page nul ou négatif",
        ValueError,
        lambda: pdf_tools.extraire_plage_pages(PDF_SOURCE, 0, 2, RACINE / "exports" / "test.pdf"),
    )
    verifier(
        "Plage inversée (début après la fin)",
        ValueError,
        lambda: pdf_tools.extraire_plage_pages(PDF_SOURCE, 3, 2, RACINE / "exports" / "test.pdf"),
    )
    verifier(
        "Mot-clé vide",
        ValueError,
        lambda: pdf_tools.rechercher_mot_cle(PDF_SOURCE, "   "),
    )
    verifier(
        "Chiffrement sans mot de passe",
        ValueError,
        lambda: pdf_tools.chiffrer_pdf(PDF_SOURCE, RACINE / "exports" / "test.pdf", ""),
    )
    tester_dependance_chiffrement_absente()


def tester_dependance_chiffrement_absente():
    """Vérifie qu'une bibliothèque de chiffrement manquante donne un message clair.

    Le chiffrement AES-256 de pypdf s'appuie sur la bibliothèque « cryptography ».
    Si elle n'est pas installée, l'utilisateur doit obtenir une consigne
    d'installation, et non une trace d'erreur Python.
    """
    encrypt_original = pdf_tools.PdfWriter.encrypt

    def encrypt_sans_dependance(self, *arguments, **parametres):
        raise DependencyError("cryptography>=3.1 is required for AES algorithm")

    pdf_tools.PdfWriter.encrypt = encrypt_sans_dependance
    try:
        verifier(
            "Bibliothèque de chiffrement absente",
            pdf_tools.ErreurPdf,
            lambda: pdf_tools.chiffrer_pdf(
                PDF_SOURCE, RACINE / "exports" / "test.pdf", "mot_de_passe_de_test"
            ),
        )
    finally:
        pdf_tools.PdfWriter.encrypt = encrypt_original


def tester_images():
    print("\n[3] Images")
    verifier(
        "Image absente",
        image_tools.ErreurImage,
        lambda: image_tools.ouvrir_image(RACINE / "images" / "image_inexistante.jpg"),
    )
    verifier(
        "Format non pris en charge",
        image_tools.ErreurImage,
        lambda: image_tools.ouvrir_image(FICHIER_NON_IMAGE),
    )
    verifier(
        "Image corrompue",
        image_tools.ErreurImage,
        lambda: image_tools.redimensionner_image(
            IMAGE_CORROMPUE, RACINE / "exports" / "test.jpg"
        ),
    )


def tester_email():
    print("\n[4] Envoi d'e-mail")
    configuration_valide = {
        "serveur": "127.0.0.1",
        "port": port_libre(),
        "utilisateur": "compte@exemple.fr",
        "mot_de_passe": "mot_de_passe_de_test",
        "expediteur": "compte@exemple.fr",
    }

    verifier(
        "Serveur SMTP injoignable",
        email_tools.ErreurEmail,
        lambda: email_tools.envoyer_email(
            "destinataire@exemple.fr", "Test", "Corps", [], configuration_valide
        ),
    )

    verifier(
        "Pièce jointe introuvable",
        email_tools.ErreurEmail,
        lambda: email_tools.construire_message(
            "a@exemple.fr", "b@exemple.fr", "Test", "Corps",
            [RACINE / "exports" / "fichier_inexistant.csv"],
        ),
    )

    verifier(
        "Destinataire manquant",
        email_tools.ErreurEmail,
        lambda: email_tools.construire_message("a@exemple.fr", "", "Test", "Corps"),
    )

    smtp_original = smtplib.SMTP
    smtplib.SMTP = SmtpQuiRefuseAuthentification
    try:
        verifier(
            "Erreur d'authentification SMTP (identifiants refusés)",
            email_tools.ErreurEmail,
            lambda: email_tools.envoyer_email(
                "destinataire@exemple.fr", "Test", "Corps", [], configuration_valide
            ),
        )
    finally:
        smtplib.SMTP = smtp_original


def main():
    """Exécute l'ensemble des tests d'erreur et retourne le code de sortie."""
    print("=== Tests des cas d'erreur obligatoires ===")
    tester_scraping()
    tester_pdf()
    tester_images()
    tester_email()

    reussis = sum(resultats)
    total = len(resultats)
    print(f"\n=== {reussis}/{total} test(s) réussi(s) ===")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    sys.exit(main())
