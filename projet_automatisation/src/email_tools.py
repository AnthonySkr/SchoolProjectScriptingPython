"""Envoi des résultats par e-mail avec pièces jointes.

Aucun identifiant n'est écrit dans le code : les paramètres du serveur SMTP sont
lus dans les variables d'environnement et le mot de passe est saisi dans le
terminal s'il n'est pas déjà défini.
"""

import mimetypes
import os
import smtplib
import socket
import ssl
from email.message import EmailMessage
from getpass import getpass
from pathlib import Path

from fichiers import chemin, chemin_relatif, preparer_dossier

VARIABLES_ATTENDUES = {
    "serveur": "SMTP_SERVEUR",
    "port": "SMTP_PORT",
    "utilisateur": "SMTP_UTILISATEUR",
    "mot_de_passe": "SMTP_MOT_DE_PASSE",
    "expediteur": "SMTP_EXPEDITEUR",
}
PORT_PAR_DEFAUT = 587
DELAI_CONNEXION = 20


class ErreurEmail(Exception):
    """Erreur levée lorsqu'un e-mail ne peut pas être préparé ou envoyé."""


def charger_configuration(demander_mot_de_passe=True):
    """Lit la configuration SMTP dans l'environnement et complète ce qui manque."""
    serveur = os.environ.get(VARIABLES_ATTENDUES["serveur"], "").strip()
    utilisateur = os.environ.get(VARIABLES_ATTENDUES["utilisateur"], "").strip()
    expediteur = os.environ.get(VARIABLES_ATTENDUES["expediteur"], "").strip() or utilisateur

    if not serveur or not utilisateur:
        raise ErreurEmail(
            "Configuration SMTP incomplète : définissez au minimum "
            f"{VARIABLES_ATTENDUES['serveur']} et {VARIABLES_ATTENDUES['utilisateur']} "
            "dans vos variables d'environnement."
        )

    try:
        port = int(os.environ.get(VARIABLES_ATTENDUES["port"], PORT_PAR_DEFAUT))
    except ValueError as erreur:
        raise ErreurEmail(
            f"{VARIABLES_ATTENDUES['port']} doit être un nombre entier."
        ) from erreur

    mot_de_passe = os.environ.get(VARIABLES_ATTENDUES["mot_de_passe"], "")
    if not mot_de_passe and demander_mot_de_passe:
        mot_de_passe = getpass(f"Mot de passe SMTP pour {utilisateur} : ")
    if not mot_de_passe:
        raise ErreurEmail("Mot de passe SMTP absent : envoi impossible.")

    return {
        "serveur": serveur,
        "port": port,
        "utilisateur": utilisateur,
        "mot_de_passe": mot_de_passe,
        "expediteur": expediteur,
    }


def _joindre_fichier(message, fichier):
    fichier = Path(fichier)
    if not fichier.is_file():
        raise ErreurEmail(f"Pièce jointe introuvable : {fichier}")

    type_mime, _ = mimetypes.guess_type(fichier.name)
    type_principal, sous_type = (type_mime or "application/octet-stream").split("/", 1)

    try:
        contenu = fichier.read_bytes()
    except OSError as erreur:
        raise ErreurEmail(f"Lecture impossible de la pièce jointe {fichier.name} : {erreur}") from erreur

    message.add_attachment(
        contenu, maintype=type_principal, subtype=sous_type, filename=fichier.name
    )


def construire_message(expediteur, destinataire, sujet, corps, pieces_jointes=None):
    """Construit un e-mail complet avec ses pièces jointes."""
    if not destinataire:
        raise ErreurEmail("Aucun destinataire indiqué.")

    message = EmailMessage()
    message["From"] = expediteur
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(corps)

    for fichier in pieces_jointes or []:
        _joindre_fichier(message, fichier)
        print(f"[email] Pièce jointe ajoutée : {chemin_relatif(fichier)}")

    return message


def enregistrer_message(message, destination=None):
    """Enregistre l'e-mail au format .eml (mode simulation, sans connexion SMTP)."""
    destination = preparer_dossier(destination or chemin("exports", "email_simule.eml"))
    try:
        destination.write_bytes(bytes(message))
    except OSError as erreur:
        raise ErreurEmail(f"Enregistrement de l'e-mail impossible : {erreur}") from erreur

    print(f"[email] Mode simulation : message enregistré dans {chemin_relatif(destination)}")
    return destination


def envoyer_email(destinataire, sujet, corps, pieces_jointes=None, configuration=None):
    """Envoie un e-mail avec pièces jointes via un serveur SMTP authentifié."""
    configuration = configuration or charger_configuration()
    message = construire_message(
        configuration["expediteur"], destinataire, sujet, corps, pieces_jointes
    )

    contexte = ssl.create_default_context()
    try:
        if configuration["port"] == 465:
            serveur_smtp = smtplib.SMTP_SSL(
                configuration["serveur"], configuration["port"],
                timeout=DELAI_CONNEXION, context=contexte,
            )
        else:
            serveur_smtp = smtplib.SMTP(
                configuration["serveur"], configuration["port"], timeout=DELAI_CONNEXION
            )

        with serveur_smtp:
            if configuration["port"] != 465:
                serveur_smtp.starttls(context=contexte)
            serveur_smtp.login(configuration["utilisateur"], configuration["mot_de_passe"])
            serveur_smtp.send_message(message)

    except smtplib.SMTPAuthenticationError as erreur:
        raise ErreurEmail(
            f"Erreur d'authentification SMTP pour {configuration['utilisateur']} "
            f"(code {erreur.smtp_code}). Vérifiez l'identifiant ou le mot de passe d'application."
        ) from erreur
    except smtplib.SMTPRecipientsRefused as erreur:
        raise ErreurEmail(f"Destinataire refusé par le serveur : {destinataire}") from erreur
    except smtplib.SMTPException as erreur:
        raise ErreurEmail(f"Envoi impossible : {erreur}") from erreur
    except (socket.gaierror, socket.timeout, TimeoutError, ConnectionError, ssl.SSLError) as erreur:
        raise ErreurEmail(
            f"Connexion impossible à {configuration['serveur']}:{configuration['port']} ({erreur})"
        ) from erreur

    print(f"[email] Message envoyé à {destinataire}.")
    return message
