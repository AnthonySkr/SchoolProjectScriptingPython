# Rapport de projet — Chaîne d'automatisation avec Python

Cours : *Scripting Python pour l'automatisation* — Projet de synthèse.

---

## 1. Objectif

Automatiser une chaîne complète de traitement documentaire : collecter des
données produit sur le Web, les enregistrer dans un CSV, traiter un document PDF
(recherche, découpage, filigrane, chiffrement), redimensionner une image, puis
diffuser les résultats par e-mail — le tout depuis un unique lancement en
terminal.

## 2. Architecture

Le code est réparti en cinq modules métier, sans logique dans le point d'entrée
autre que l'enchaînement des étapes.

| Module | Responsabilité | Fonctions principales |
| --- | --- | --- |
| `fichiers.py` | chemins `pathlib`, création des dossiers, CSV | `chemin`, `creer_dossiers`, `preparer_dossier`, `ecrire_csv`, `lire_csv` |
| `scraping.py` | collecte HTTP et analyse HTML | `telecharger_page`, `extraire_produits`, `collecter_produits`, `collecter_produits_hors_ligne` |
| `pdf_tools.py` | traitement des documents PDF | `ouvrir_pdf`, `rechercher_mot_cle`, `extraire_plage_pages`, `diviser_pdf`, `ajouter_filigrane`, `chiffrer_pdf` |
| `image_tools.py` | traitement des images | `ouvrir_image`, `informations_image`, `redimensionner_image` |
| `email_tools.py` | e-mail et pièces jointes | `charger_configuration`, `construire_message`, `envoyer_email`, `enregistrer_message` |
| `main.py` | orchestration, options de ligne de commande | `analyser_arguments`, `etape_collecte`, `etape_pdf`, `etape_image`, `etape_email`, `main` |

Tous les chemins sont dérivés de `RACINE_PROJET = Path(__file__).resolve().parent.parent`
dans `fichiers.py` : le projet fonctionne quel que soit le dossier depuis lequel
il est copié, sans aucun chemin absolu propre à une machine.

`fichiers.creer_dossiers()` crée `data/`, `images/`, `pdf/` et `exports/` au
démarrage ; `fichiers.preparer_dossier()` crée en plus le dossier parent de
chaque fichier écrit.

## 3. Fonctionnalités réalisées

| Attendu | Réalisation |
| --- | --- |
| Extraire titre, prix et disponibilité | `scraping.extraire_produits()` analyse les balises `article.product_pod` de books.toscrape.com ; le prix est séparé en valeur numérique et devise |
| Enregistrer les résultats en CSV | `fichiers.ecrire_csv()` écrit `exports/produits.csv` (séparateur `;`, encodage `utf-8-sig` lisible par Excel) |
| Rechercher un mot-clé dans un PDF | `pdf_tools.rechercher_mot_cle()` retourne pour chaque page le nombre d'occurrences et un extrait ; la recherche ignore la casse **et les accents** |
| Diviser le PDF / extraire une plage | `diviser_pdf()` (fichiers de *N* pages dans `exports/decoupage/`) et `extraire_plage_pages()` (`--plage 1-3`) |
| Filigrane « CONFIDENTIEL » | `ajouter_filigrane()` construit un calque `reportlab` en mémoire, à la taille exacte de chaque page, incliné à 45° et semi-transparent, puis le fusionne sur chaque page |
| Chiffrer le PDF | `chiffrer_pdf()` applique un chiffrement **AES-256** avec un mot de passe saisi au clavier (`getpass`, masqué et confirmé) |
| Redimensionner sans déformer | `redimensionner_image()` s'appuie sur `Image.thumbnail()` : l'image est inscrite dans un cadre maximal, le rapport largeur/hauteur est conservé par construction |
| Envoyer les résultats par e-mail | `envoyer_email()` joint le CSV, le PDF final et l'image, via SMTP authentifié en STARTTLS (port 587) ou SSL (port 465) |

## 4. Contraintes techniques respectées

- **Code organisé en fonctions et réparti dans plusieurs modules** : 6 modules,
  aucune fonction ne dépasse une trentaine de lignes.
- **Fonction `main()`** présente dans `src/main.py`, appelée via
  `if __name__ == "__main__": sys.exit(main())` et retournant un code de sortie
  (`0` succès, `1` si une étape a échoué).
- **`pathlib`** pour l'ensemble des chemins et des dossiers.
- **`try` / `except`** : chaque opération d'entrée-sortie est protégée, avec des
  exceptions dédiées par module et des messages en français.
- **Aucun identifiant ni mot de passe dans le code** : variables
  d'environnement `SMTP_*` et saisie clavier via `getpass`.
- **Création automatique des dossiers de sortie**.
- **Messages d'exécution clairs** : chaque ligne est préfixée par l'étape
  concernée (`[scraping]`, `[csv]`, `[pdf]`, `[image]`, `[email]`, `[erreur]`).
- **Nommage** : fonctions, variables et fichiers en français, explicites, sans
  abréviation.

## 5. Démonstration

Commande exécutée (mode hors ligne et simulation d'e-mail, pour une
démonstration reproductible sans réseau ni compte SMTP) :

```bash
PDF_MOT_DE_PASSE="MotDePasseDemo!" \
python src/main.py --hors-ligne --mot-cle disponibilite --plage 1-3 \
                   --simuler-email --destinataire nom@exemple.fr
```

Le mot de passe du PDF est ici fourni par une variable d'environnement afin que
la démonstration soit reproductible sans saisie. En usage normal
(`python src/main.py`), il est demandé au clavier de façon masquée et confirmé.

Sortie du terminal :

```
=== Chaîne d'automatisation Python ===
[dossiers] Dossiers de travail prêts (data, images, pdf, exports).

=== Étape 1 : collecte des produits ===
[scraping] Source locale : catalogue_demo.html
[scraping] 10 produit(s) extrait(s).
[csv] 10 ligne(s) écrite(s) dans exports/produits.csv.

=== Étape 2 : traitement du document PDF ===
[pdf] Document source : pdf/rapport_produits.pdf (4 pages)
[pdf] Mot-clé « disponibilite » trouvé sur 2 page(s) :
       page 1 (1x) : ogue est décrit par un titre, un prix et une disponibilité. Ces trois informations sont en
       page 3 (3x) : Disponibilité des produits La disponibilité de chaque produit est relevée à chaque exécuti
[pdf] Pages 1 à 3 extraites vers extrait_pages.pdf.
[pdf] Document découpé en 4 fichier(s) dans decoupage/.
[pdf] Filigrane « CONFIDENTIEL » appliqué sur 3 page(s).
[pdf] Mot de passe lu dans la variable PDF_MOT_DE_PASSE.
[pdf] Document chiffré : document_final_protege.pdf

=== Étape 3 : traitement de l'image ===
[image] Source : photo_produit.jpg (JPEG, 1600x900 px)
[image] photo_produit.jpg : 1600x900 px -> 800x450 px (proportions conservées).

=== Étape 4 : envoi des résultats par e-mail ===
[email] Pièce jointe ajoutée : exports/produits.csv
[email] Pièce jointe ajoutée : exports/document_final_protege.pdf
[email] Pièce jointe ajoutée : exports/photo_produit_redimensionnee.jpg
[email] Mode simulation : message enregistré dans exports/email_simule.eml

[journal] Compte rendu enregistré dans exports/journal_execution.txt

=== Chaîne exécutée avec succès ===
```

### Résultats produits dans `exports/`

| Fichier | Vérification |
| --- | --- |
| `produits.csv` | 10 lignes, colonnes `titre;prix;devise;disponibilite;source` |
| `extrait_pages.pdf` | 3 pages extraites du document de 4 pages |
| `decoupage/` | 4 fichiers d'une page (`rapport_produits_pages_1-1.pdf` … `_4-4.pdf`) |
| `document_filigrane.pdf` | mention `CONFIDENTIEL` présente dans le texte extrait de chaque page |
| `document_final_protege.pdf` | lecture refusée sans mot de passe (`FileNotDecryptedError`), 3 pages lisibles avec le mot de passe |
| `photo_produit_redimensionnee.jpg` | 800 × 450 px, rapport 1,7778 identique à l'original (1600 × 900) |
| `email_simule.eml` | message avec les 3 pièces jointes |
| `journal_execution.txt` | compte rendu horodaté des étapes |

### Comportement en cas d'échec d'une étape

La chaîne n'est pas interrompue par l'échec d'une étape : l'erreur est affichée,
inscrite au journal, et les étapes suivantes s'exécutent. Exemple réel obtenu
lorsque le réseau est indisponible :

```
=== Étape 1 : collecte des produits ===
[scraping] Page 1 : https://books.toscrape.com/catalogue/page-1.html
[erreur] Collecte impossible : URL inaccessible (connexion impossible) : https://books.toscrape.com/catalogue/page-1.html

=== Étape 2 : traitement du document PDF ===
[pdf] Document source : pdf/rapport_produits.pdf (4 pages)
[pdf] Mot-clé « prix » trouvé sur 2 page(s) :
...
```

Le programme retourne alors le code de sortie `1`.

## 6. Tests des cas d'erreur obligatoires

`python outils/tests_erreurs.py` — **20 tests, 20 réussis**.

| Cas exigé | Test | Message obtenu |
| --- | --- | --- |
| URL inaccessible | domaine inexistant | `URL inaccessible (connexion impossible) : https://domaine-qui-nexiste-pas-1234.invalid/` |
| Réponse HTTP incorrecte | serveur local renvoyant 404 | `Réponse HTTP incorrecte (404) pour l'URL : http://127.0.0.1:38705/catalogue` |
| — | page HTML de structure inattendue | `Aucun produit trouvé : la page ne correspond pas à la structure attendue` |
| — | page HTML locale absente | `Page HTML locale introuvable : .../data/fichier_inexistant.html` |
| PDF absent | fichier inexistant | `PDF absent : .../pdf/document_inexistant.pdf` |
| PDF vide | `document_vide.pdf` | `Aucun texte extractible dans document_vide.pdf (document vide ou constitué d'images).` |
| PDF protégé | `document_protege.pdf` sans mot de passe | `PDF protégé par mot de passe : document_protege.pdf. Fournissez le mot de passe pour l'ouvrir.` |
| PDF protégé | mot de passe erroné | `Mot de passe incorrect pour : document_protege.pdf` |
| Numéro de page incorrect | page 99 d'un document de 4 pages | `Numéro de page incorrect : le document ne contient que 4 page(s).` |
| Numéro de page incorrect | page 0 | `Numéro de page incorrect : la numérotation commence à 1 (reçu 0-2).` |
| Numéro de page incorrect | plage inversée 3-2 | `Plage incorrecte : la page de début (3) dépasse celle de fin (2).` |
| — | mot-clé vide | `Le mot-clé recherché ne peut pas être vide.` |
| — | chiffrement sans mot de passe | `Le mot de passe de chiffrement ne peut pas être vide.` |
| Image non prise en charge | fichier `.txt` | `Format non pris en charge : .txt (formats acceptés : ...)` |
| Image corrompue | `.png` aux octets invalides | `Image corrompue ou format non reconnu : image_corrompue.png` |
| — | image absente | `Image absente : .../images/image_inexistante.jpg` |
| Erreur d'envoi d'e-mail | serveur SMTP injoignable | `Connexion impossible à 127.0.0.1:41055 ([Errno 111] Connection refused)` |
| Erreur d'authentification | identifiants refusés (code 535) | `Erreur d'authentification SMTP pour compte@exemple.fr (code 535). Vérifiez l'identifiant ou le mot de passe d'application.` |
| — | pièce jointe introuvable | `Pièce jointe introuvable : .../exports/fichier_inexistant.csv` |
| — | destinataire manquant | `Aucun destinataire indiqué.` |

## 7. Difficultés rencontrées et solutions

- **Filigrane sur des pages de tailles différentes.** Un calque de taille fixe
  se serait décalé sur des pages non A4. Le calque est donc généré à la volée
  aux dimensions exactes de chaque `mediabox` avant fusion.
- **Recherche de mot-clé et accents.** Une recherche naïve sur `disponibilite`
  ne trouvait pas « disponibilité ». Le texte et le mot-clé sont normalisés
  (minuscules, accents retirés) par une fonction qui **conserve la longueur du
  texte**, ce qui permet de retrouver la position exacte du mot et d'en afficher
  un extrait lisible.
- **Démonstration sans accès réseau ni compte SMTP.** L'environnement de
  développement n'autorisait pas la sortie vers le site de démonstration. Deux
  modes ont été ajoutés : `--hors-ligne` (analyse d'une page HTML enregistrée
  dans `data/`, exactement le même analyseur HTML) et `--simuler-email` (le
  message et ses pièces jointes sont réellement construits puis enregistrés au
  format `.eml`, sans connexion SMTP). Le code réseau et le code SMTP restent
  ceux qui sont utilisés en fonctionnement normal.
- **Secrets et dépôt Git.** Aucun identifiant ne figure dans le code : la
  configuration SMTP passe par des variables d'environnement et les mots de
  passe par `getpass`. Le fichier `.gitignore` exclut `.env` et les
  environnements virtuels.

## 8. Améliorations possibles

- Journalisation via le module `logging` avec plusieurs niveaux de détail.
- Tests unitaires avec `pytest` en complément du script de tests d'erreur.
- Planification automatique de la chaîne (cron ou tâche planifiée).
- Export supplémentaire au format Excel et suivi de l'évolution des prix entre
  deux exécutions.
