"""Extraction du titre, du prix et de la disponibilité de produits depuis un site Web.

Le site de démonstration utilisé est https://books.toscrape.com, prévu pour
l'apprentissage du scraping. Une source locale (page HTML enregistrée dans
``data/``) peut remplacer le réseau lorsque celui-ci n'est pas disponible.
"""

from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from fichiers import chemin, enregistrer_texte

URL_PAR_DEFAUT = "https://books.toscrape.com/catalogue/page-1.html"
DELAI_REPONSE = 10
ENTETES_HTTP = {"User-Agent": "Projet-automatisation-scolaire/1.0"}
COLONNES_CSV = ["titre", "prix", "devise", "disponibilite", "source"]


class ErreurScraping(Exception):
    """Erreur levée lorsqu'une page ne peut pas être récupérée ou analysée."""


def telecharger_page(url, delai=DELAI_REPONSE):
    """Télécharge une page Web et retourne son code HTML.

    Une URL inaccessible ou un code HTTP différent de 200 lève une ErreurScraping.
    """
    try:
        reponse = requests.get(url, headers=ENTETES_HTTP, timeout=delai)
        reponse.raise_for_status()
    except requests.exceptions.Timeout as erreur:
        raise ErreurScraping(f"Délai dépassé ({delai} s) pour l'URL : {url}") from erreur
    except requests.exceptions.HTTPError as erreur:
        code = erreur.response.status_code if erreur.response is not None else "inconnu"
        raise ErreurScraping(f"Réponse HTTP incorrecte ({code}) pour l'URL : {url}") from erreur
    except requests.exceptions.ConnectionError as erreur:
        raise ErreurScraping(f"URL inaccessible (connexion impossible) : {url}") from erreur
    except requests.exceptions.RequestException as erreur:
        raise ErreurScraping(f"Requête impossible vers {url} : {erreur}") from erreur

    reponse.encoding = reponse.apparent_encoding or "utf-8"
    return reponse.text


def lire_page_locale(source):
    """Lit une page HTML enregistrée sur le disque (mode hors ligne)."""
    source = Path(source)
    if not source.is_file():
        raise ErreurScraping(f"Page HTML locale introuvable : {source}")

    try:
        return source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as erreur:
        raise ErreurScraping(f"Lecture impossible de {source} : {erreur}") from erreur


def _texte_nettoye(element):
    return element.get_text(strip=True) if element else ""


def _separer_prix(prix_brut):
    """Sépare « £51.77 » en une valeur numérique et une devise."""
    montant = "".join(caractere for caractere in prix_brut if caractere.isdigit() or caractere == ".")
    devise = "".join(caractere for caractere in prix_brut if not caractere.isdigit() and caractere not in ".,")
    try:
        return float(montant), devise.strip()
    except ValueError:
        return None, devise.strip()


def extraire_produits(html, source="inconnue"):
    """Analyse le HTML d'une page catalogue et retourne la liste des produits."""
    try:
        soupe = BeautifulSoup(html, "html.parser")
    except Exception as erreur:  # protection contre un HTML totalement illisible
        raise ErreurScraping(f"Analyse HTML impossible : {erreur}") from erreur

    produits = []
    for article in soupe.select("article.product_pod"):
        lien_titre = article.select_one("h3 a")
        titre = lien_titre.get("title") if lien_titre and lien_titre.get("title") else _texte_nettoye(lien_titre)
        prix_brut = _texte_nettoye(article.select_one("p.price_color"))
        disponibilite = _texte_nettoye(article.select_one("p.availability")) or "Non précisée"
        prix, devise = _separer_prix(prix_brut)

        if not titre:
            continue

        produits.append(
            {
                "titre": titre,
                "prix": prix if prix is not None else prix_brut,
                "devise": devise,
                "disponibilite": disponibilite,
                "source": source,
            }
        )

    if not produits:
        raise ErreurScraping(
            "Aucun produit trouvé : la page ne correspond pas à la structure attendue "
            "(balises <article class=\"product_pod\">)."
        )
    return produits


def _url_page_suivante(html, url_courante):
    soupe = BeautifulSoup(html, "html.parser")
    lien = soupe.select_one("li.next a")
    return urljoin(url_courante, lien["href"]) if lien and lien.get("href") else None


def collecter_produits(url=URL_PAR_DEFAUT, nombre_pages=1, archiver=True):
    """Parcourt une ou plusieurs pages du catalogue et retourne tous les produits."""
    produits = []
    url_courante = url

    for numero in range(1, max(1, nombre_pages) + 1):
        if url_courante is None:
            print(f"[scraping] Plus de page suivante après la page {numero - 1}.")
            break

        print(f"[scraping] Page {numero} : {url_courante}")
        html = telecharger_page(url_courante)

        if archiver:
            archive = chemin("data", f"page_catalogue_{numero}.html")
            enregistrer_texte(html, archive)

        produits.extend(extraire_produits(html, source=url_courante))
        url_courante = _url_page_suivante(html, url_courante)

    print(f"[scraping] {len(produits)} produit(s) extrait(s).")
    return produits


def collecter_produits_hors_ligne(source=None):
    """Extrait les produits depuis une page HTML locale, sans accès réseau."""
    source = Path(source) if source else chemin("data", "catalogue_demo.html")
    print(f"[scraping] Source locale : {source.name}")
    html = lire_page_locale(source)
    produits = extraire_produits(html, source=f"fichier local : {source.name}")
    print(f"[scraping] {len(produits)} produit(s) extrait(s).")
    return produits
