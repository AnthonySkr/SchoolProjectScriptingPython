"""Chaîne d'automatisation : scraping, CSV, traitement PDF, image et envoi d'e-mail.

Exemple d'utilisation :
    python src/main.py --hors-ligne --mot-cle disponibilite --simuler-email
"""

import argparse
import os
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import email_tools
import fichiers
import image_tools
import pdf_tools
import scraping

PDF_SOURCE_PAR_DEFAUT = "rapport_produits.pdf"
IMAGE_SOURCE_PAR_DEFAUT = "photo_produit.jpg"
VARIABLE_MOT_DE_PASSE_PDF = "PDF_MOT_DE_PASSE"


def analyser_arguments(arguments=None):
    """Définit et lit les options de la ligne de commande."""
    analyseur = argparse.ArgumentParser(
        description="Chaîne d'automatisation Python : scraping, CSV, PDF, image et e-mail.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    groupe_web = analyseur.add_argument_group("collecte Web")
    groupe_web.add_argument("--url", default=scraping.URL_PAR_DEFAUT, help="URL du catalogue à analyser")
    groupe_web.add_argument("--pages", type=int, default=1, help="nombre de pages à parcourir")
    groupe_web.add_argument(
        "--hors-ligne", action="store_true",
        help="utiliser la page HTML locale de data/ au lieu du réseau",
    )
    groupe_web.add_argument("--source-html", help="chemin d'une page HTML locale à analyser")

    groupe_pdf = analyseur.add_argument_group("traitement PDF")
    groupe_pdf.add_argument("--pdf", help=f"PDF source (par défaut pdf/{PDF_SOURCE_PAR_DEFAUT})")
    groupe_pdf.add_argument("--mot-cle", help="mot-clé à rechercher dans le PDF")
    groupe_pdf.add_argument("--plage", default="1-2", help="plage de pages à extraire, format debut-fin")
    groupe_pdf.add_argument(
        "--pages-par-fichier", type=int, default=1,
        help="nombre de pages par fichier lors du découpage",
    )
    groupe_pdf.add_argument("--filigrane", default=pdf_tools.TEXTE_FILIGRANE, help="texte du filigrane")

    groupe_image = analyseur.add_argument_group("traitement image")
    groupe_image.add_argument("--image", help=f"image source (par défaut images/{IMAGE_SOURCE_PAR_DEFAUT})")
    groupe_image.add_argument("--largeur-max", type=int, default=800, help="largeur maximale en pixels")
    groupe_image.add_argument("--hauteur-max", type=int, default=800, help="hauteur maximale en pixels")

    groupe_email = analyseur.add_argument_group("envoi des résultats")
    groupe_email.add_argument("--destinataire", help="adresse e-mail qui recevra les résultats")
    groupe_email.add_argument(
        "--simuler-email", action="store_true",
        help="préparer le message et l'enregistrer en .eml sans connexion SMTP",
    )
    groupe_email.add_argument("--sans-email", action="store_true", help="ignorer complètement l'étape e-mail")

    return analyseur.parse_args(arguments)


def demander_mot_cle(mot_cle_argument):
    """Récupère le mot-clé auprès de l'utilisateur si l'option n'a pas été fournie."""
    if mot_cle_argument:
        return mot_cle_argument
    if not sys.stdin.isatty():
        return "produit"
    saisie = input("Mot-clé à rechercher dans le PDF [produit] : ").strip()
    return saisie or "produit"


def demander_mot_de_passe_pdf():
    """Demande dans le terminal le mot de passe qui protégera le PDF final."""
    depuis_environnement = os.environ.get(VARIABLE_MOT_DE_PASSE_PDF, "")
    if depuis_environnement:
        print(f"[pdf] Mot de passe lu dans la variable {VARIABLE_MOT_DE_PASSE_PDF}.")
        return depuis_environnement

    if not sys.stdin.isatty():
        raise ValueError(
            "Aucun terminal interactif : définissez la variable "
            f"{VARIABLE_MOT_DE_PASSE_PDF} pour chiffrer le document."
        )

    for _ in range(3):
        mot_de_passe = getpass("Mot de passe du PDF final : ")
        confirmation = getpass("Confirmez le mot de passe : ")
        if mot_de_passe and mot_de_passe == confirmation:
            return mot_de_passe
        print("[pdf] Les mots de passe sont vides ou différents, nouvelle tentative.")

    raise ValueError("Mot de passe non confirmé après trois tentatives.")


def analyser_plage(plage):
    """Convertit une plage « debut-fin » en deux entiers."""
    morceaux = str(plage).split("-")
    if len(morceaux) != 2:
        raise ValueError(f"Plage de pages invalide : {plage!r} (format attendu : 1-3).")
    return int(morceaux[0]), int(morceaux[1])


def etape_collecte(options, journal):
    """Étape 1 : collecte des produits et écriture du CSV dans exports/."""
    print("\n=== Étape 1 : collecte des produits ===")
    if options.hors_ligne or options.source_html:
        produits = scraping.collecter_produits_hors_ligne(options.source_html)
    else:
        produits = scraping.collecter_produits(options.url, options.pages)

    destination = fichiers.chemin("exports", "produits.csv")
    csv_produits = fichiers.ecrire_csv(produits, destination, entetes=scraping.COLONNES_CSV)
    print(f"[csv] {len(produits)} ligne(s) écrite(s) dans {fichiers.chemin_relatif(csv_produits)}.")
    journal.append(f"CSV produit : {fichiers.chemin_relatif(csv_produits)} ({len(produits)} produits)")
    return csv_produits


def etape_pdf(options, journal):
    """Étape 2 : recherche, découpage, filigrane et chiffrement du PDF."""
    print("\n=== Étape 2 : traitement du document PDF ===")
    source = Path(options.pdf) if options.pdf else fichiers.chemin("pdf", PDF_SOURCE_PAR_DEFAUT)
    total_pages = pdf_tools.nombre_de_pages(source)
    print(f"[pdf] Document source : {fichiers.chemin_relatif(source)} ({total_pages} pages)")

    mot_cle = demander_mot_cle(options.mot_cle)
    resultats = pdf_tools.rechercher_mot_cle(source, mot_cle)
    if resultats:
        print(f"[pdf] Mot-clé « {mot_cle} » trouvé sur {len(resultats)} page(s) :")
        for resultat in resultats:
            print(f"       page {resultat['page']} ({resultat['occurrences']}x) : {resultat['extrait']}")
    else:
        print(f"[pdf] Mot-clé « {mot_cle} » absent du document.")
    journal.append(f"Recherche « {mot_cle} » : {len(resultats)} page(s) correspondante(s)")

    debut, fin = analyser_plage(options.plage)
    extrait = pdf_tools.extraire_plage_pages(
        source, debut, fin, fichiers.chemin("exports", "extrait_pages.pdf")
    )

    parties = pdf_tools.diviser_pdf(
        source, fichiers.chemin("exports", "decoupage"), options.pages_par_fichier
    )
    journal.append(f"Découpage : {len(parties)} fichier(s) dans exports/decoupage/")

    filigrane = pdf_tools.ajouter_filigrane(
        extrait, fichiers.chemin("exports", "document_filigrane.pdf"), options.filigrane
    )

    mot_de_passe = demander_mot_de_passe_pdf()
    final = pdf_tools.chiffrer_pdf(
        filigrane, fichiers.chemin("exports", "document_final_protege.pdf"), mot_de_passe
    )
    journal.append(f"PDF final chiffré : {fichiers.chemin_relatif(final)}")
    return final


def etape_image(options, journal):
    """Étape 3 : redimensionnement de l'image sans déformation."""
    print("\n=== Étape 3 : traitement de l'image ===")
    source = Path(options.image) if options.image else fichiers.chemin("images", IMAGE_SOURCE_PAR_DEFAUT)
    infos = image_tools.informations_image(source)
    print(f"[image] Source : {infos['nom']} ({infos['format']}, {infos['largeur']}x{infos['hauteur']} px)")

    destination = fichiers.chemin("exports", f"{Path(source).stem}_redimensionnee.jpg")
    resultat = image_tools.redimensionner_image(
        source, destination, (options.largeur_max, options.hauteur_max)
    )
    journal.append(f"Image redimensionnée : {fichiers.chemin_relatif(resultat)}")
    return resultat


def etape_email(options, pieces_jointes, journal):
    """Étape 4 : envoi (ou simulation d'envoi) des résultats par e-mail."""
    print("\n=== Étape 4 : envoi des résultats par e-mail ===")
    pieces_jointes = [piece for piece in pieces_jointes if piece]
    if not pieces_jointes:
        raise email_tools.ErreurEmail("Aucun résultat à envoyer : les étapes précédentes ont échoué.")

    destinataire = options.destinataire
    if not destinataire:
        destinataire = input("Adresse du destinataire : ").strip() if sys.stdin.isatty() else ""
    if not destinataire and options.simuler_email:
        destinataire = "destinataire.demo@exemple.fr"

    horodatage = datetime.now().strftime("%d/%m/%Y à %H:%M")
    sujet = "Résultats de la chaîne d'automatisation Python"
    corps = (
        "Bonjour,\n\n"
        f"Vous trouverez en pièces jointes les résultats produits le {horodatage} :\n"
        + "\n".join(f"  - {Path(piece).name}" for piece in pieces_jointes)
        + "\n\nLe document PDF est protégé par mot de passe, communiqué séparément.\n\n"
        "Message envoyé automatiquement par le projet de synthèse Scripting Python.\n"
    )

    if options.simuler_email:
        message = email_tools.construire_message(
            "expediteur.demo@exemple.fr", destinataire, sujet, corps, pieces_jointes
        )
        resultat = email_tools.enregistrer_message(message, fichiers.chemin("exports", "email_simule.eml"))
        journal.append(f"E-mail simulé : {fichiers.chemin_relatif(resultat)}")
        return resultat

    email_tools.envoyer_email(destinataire, sujet, corps, pieces_jointes)
    journal.append(f"E-mail envoyé à {destinataire}")
    return destinataire


def ecrire_journal(journal):
    """Enregistre le compte rendu de l'exécution dans exports/."""
    contenu = (
        "Journal d'exécution de la chaîne d'automatisation\n"
        f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        + "\n".join(f"- {ligne}" for ligne in journal)
        + "\n"
    )
    return fichiers.enregistrer_texte(contenu, fichiers.chemin("exports", "journal_execution.txt"))


def main(arguments=None):
    """Point d'entrée du programme : enchaîne les quatre étapes de la chaîne."""
    options = analyser_arguments(arguments)
    journal = []
    erreurs = 0

    print("=== Chaîne d'automatisation Python ===")
    try:
        crees = fichiers.creer_dossiers()
        print(f"[dossiers] Dossiers de travail prêts ({', '.join(fichiers.DOSSIERS)}).")
        if crees:
            print(f"[dossiers] Dossiers créés automatiquement : {', '.join(crees)}.")
    except OSError as erreur:
        print(f"[erreur] {erreur}")
        return 1

    csv_produits = None
    try:
        csv_produits = etape_collecte(options, journal)
    except (scraping.ErreurScraping, OSError, ValueError) as erreur:
        erreurs += 1
        print(f"[erreur] Collecte impossible : {erreur}")
        journal.append(f"ÉCHEC collecte : {erreur}")

    pdf_final = None
    try:
        pdf_final = etape_pdf(options, journal)
    except (pdf_tools.ErreurPdf, OSError, ValueError) as erreur:
        erreurs += 1
        print(f"[erreur] Traitement PDF impossible : {erreur}")
        journal.append(f"ÉCHEC PDF : {erreur}")

    image_finale = None
    try:
        image_finale = etape_image(options, journal)
    except (image_tools.ErreurImage, OSError, ValueError) as erreur:
        erreurs += 1
        print(f"[erreur] Traitement de l'image impossible : {erreur}")
        journal.append(f"ÉCHEC image : {erreur}")

    if options.sans_email:
        print("\n=== Étape 4 : envoi ignoré (--sans-email) ===")
        journal.append("E-mail ignoré à la demande de l'utilisateur")
    else:
        try:
            etape_email(options, [csv_produits, pdf_final, image_finale], journal)
        except (email_tools.ErreurEmail, OSError, ValueError) as erreur:
            erreurs += 1
            print(f"[erreur] Envoi de l'e-mail impossible : {erreur}")
            journal.append(f"ÉCHEC e-mail : {erreur}")

    try:
        rapport = ecrire_journal(journal)
        print(f"\n[journal] Compte rendu enregistré dans {fichiers.chemin_relatif(rapport)}")
    except OSError as erreur:
        print(f"[erreur] Journal non enregistré : {erreur}")

    if erreurs:
        print(f"\n=== Terminé avec {erreurs} étape(s) en échec ===")
        return 1

    print("\n=== Chaîne exécutée avec succès ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
