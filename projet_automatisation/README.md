# Chaîne d'automatisation avec Python

Projet de synthèse du cours *Scripting Python pour l'automatisation*.

L'application collecte des produits sur un site Web de démonstration, enregistre
les résultats dans un fichier CSV, traite un document PDF (recherche d'un
mot-clé, extraction de pages, découpage, filigrane « CONFIDENTIEL »,
chiffrement), redimensionne une image sans la déformer, puis envoie l'ensemble
des résultats par e-mail.

---

## 1. Arborescence

```
projet_automatisation/
├── data/                 # pages HTML collectées et page de démonstration hors ligne
├── images/               # images d'entrée et fichiers de test
├── pdf/                  # documents PDF d'entrée et fichiers de test
├── exports/              # TOUS les résultats produits par la chaîne
├── outils/               # scripts annexes (génération des fichiers de test, tests d'erreur)
├── src/
│   ├── scraping.py       # collecte Web : titre, prix, disponibilité
│   ├── fichiers.py       # chemins pathlib, création des dossiers, lecture/écriture CSV
│   ├── pdf_tools.py      # recherche, découpage, filigrane, chiffrement
│   ├── image_tools.py    # redimensionnement sans déformation
│   ├── email_tools.py    # construction et envoi des e-mails avec pièces jointes
│   └── main.py           # fonction main() et enchaînement des étapes
├── requirements.txt
└── README.md
```

## 2. Installation

Python 3.9 ou plus récent est nécessaire.

```bash
cd projet_automatisation

python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

pip install -r requirements.txt
```

## 3. Exécution

Le programme se lance depuis le terminal, à la racine du dossier
`projet_automatisation/` :

```bash
python src/main.py
```

Exécution complète en mode démonstration, sans réseau ni compte SMTP :

```bash
python src/main.py --hors-ligne --mot-cle disponibilite --plage 1-3 \
                   --simuler-email --destinataire nom@exemple.fr
```

Le mot-clé recherché et le mot de passe du PDF sont demandés dans le terminal
lorsqu'ils ne sont pas fournis en option.

### Options disponibles

| Option | Rôle | Valeur par défaut |
| --- | --- | --- |
| `--url` | URL du catalogue à analyser | `https://books.toscrape.com/catalogue/page-1.html` |
| `--pages` | nombre de pages à parcourir | `1` |
| `--hors-ligne` | utiliser la page HTML locale de `data/` | désactivé |
| `--source-html` | chemin d'une autre page HTML locale | – |
| `--pdf` | PDF source à traiter | `pdf/rapport_produits.pdf` |
| `--mot-cle` | mot-clé recherché dans le PDF | demandé dans le terminal |
| `--plage` | plage de pages à extraire (`debut-fin`) | `1-2` |
| `--pages-par-fichier` | pages par fichier lors du découpage | `1` |
| `--filigrane` | texte du filigrane | `CONFIDENTIEL` |
| `--image` | image source | `images/photo_produit.jpg` |
| `--largeur-max`, `--hauteur-max` | cadre maximal de redimensionnement | `800` × `800` |
| `--destinataire` | adresse e-mail destinataire | demandée dans le terminal |
| `--simuler-email` | préparer le message en `.eml` sans connexion SMTP | désactivé |
| `--sans-email` | ignorer l'étape d'envoi | désactivé |

`python src/main.py --help` affiche l'aide complète.

## 4. Configuration de l'envoi d'e-mail

**Aucun identifiant n'est écrit dans le code.** Les paramètres sont lus dans les
variables d'environnement, et le mot de passe est saisi dans le terminal s'il
n'est pas défini.

| Variable | Rôle | Obligatoire |
| --- | --- | --- |
| `SMTP_SERVEUR` | adresse du serveur SMTP (ex. `smtp.gmail.com`) | oui |
| `SMTP_PORT` | port du serveur (`587` STARTTLS, `465` SSL) | non (`587`) |
| `SMTP_UTILISATEUR` | identifiant de connexion | oui |
| `SMTP_MOT_DE_PASSE` | mot de passe ou mot de passe d'application | non (demandé au clavier) |
| `SMTP_EXPEDITEUR` | adresse affichée en expéditeur | non (= identifiant) |

```bash
export SMTP_SERVEUR="smtp.gmail.com"
export SMTP_PORT=587
export SMTP_UTILISATEUR="mon.adresse@gmail.com"
python src/main.py --destinataire collegue@exemple.fr
```

Sous Windows (PowerShell) : `$env:SMTP_SERVEUR = "smtp.gmail.com"`.

Le mot de passe du PDF est demandé au clavier (`getpass`, saisie masquée et
confirmée). Pour une exécution automatisée sans terminal interactif, il peut
être fourni par la variable d'environnement `PDF_MOT_DE_PASSE`.

## 5. Résultats produits

Tous les fichiers sont écrits dans `exports/` :

| Fichier | Contenu |
| --- | --- |
| `produits.csv` | titre, prix, devise, disponibilité et source de chaque produit |
| `extrait_pages.pdf` | plage de pages extraite du PDF source |
| `decoupage/` | PDF source découpé en plusieurs fichiers |
| `document_filigrane.pdf` | document portant le filigrane « CONFIDENTIEL » |
| `document_final_protege.pdf` | document final chiffré par mot de passe |
| `<image>_redimensionnee.jpg` | image réduite, proportions conservées |
| `email_simule.eml` | message et pièces jointes en mode `--simuler-email` |
| `journal_execution.txt` | compte rendu de l'exécution |

## 6. Fichiers de test fournis

| Fichier | Cas testé |
| --- | --- |
| `data/catalogue_demo.html` | collecte hors ligne |
| `pdf/rapport_produits.pdf` | document source (4 pages de texte) |
| `pdf/document_vide.pdf` | PDF sans texte extractible |
| `pdf/document_protege.pdf` | PDF protégé (mot de passe de test : `demo2024`) |
| `images/photo_produit.jpg` | image source 1600 × 900 |
| `images/image_corrompue.png` | fichier `.png` invalide |
| `images/fichier_non_image.txt` | format non pris en charge |

Ces fichiers peuvent être régénérés :

```bash
python outils/generer_fichiers_test.py
```

## 7. Tests des cas d'erreur

Les vingt cas d'erreur attendus (URL inaccessible, réponse HTTP incorrecte, PDF
absent, vide ou protégé, numéro de page incorrect, image non prise en charge ou
corrompue, erreur d'authentification ou d'envoi d'e-mail) sont vérifiés
automatiquement :

```bash
python outils/tests_erreurs.py
```

Le script affiche le message d'erreur produit pour chaque cas et retourne un
code de sortie non nul si l'un d'eux n'est pas correctement traité.

## 8. Choix techniques

- **`requests` + `BeautifulSoup`** pour la collecte : bibliothèques standard du
  scraping, lisibles et suffisantes pour une page statique.
- **`pypdf`** pour le PDF (lecture, découpage, chiffrement AES-256) et
  **`reportlab`** pour dessiner le calque de filigrane, fusionné ensuite sur
  chaque page.
- **`Pillow`** et sa méthode `thumbnail()`, qui réduit une image dans un cadre
  donné en conservant le rapport largeur/hauteur : aucune déformation possible.
- **`pathlib`** pour tous les chemins, construits à partir de la racine du
  projet : aucun chemin absolu propre à une machine.
- **Dossiers créés automatiquement** au démarrage (`fichiers.creer_dossiers()`).
- **Exceptions dédiées** par module (`ErreurScraping`, `ErreurPdf`,
  `ErreurImage`, `ErreurEmail`) : `main()` les intercepte, affiche un message
  clair et poursuit les étapes suivantes plutôt que d'interrompre la chaîne.
- **Mode hors ligne et mode simulation d'e-mail** pour démontrer la chaîne
  complète sans accès réseau ni compte SMTP.

## 9. Sécurité

- Aucun identifiant, mot de passe ni adresse réelle dans le code ou le dépôt.
- Le mot de passe SMTP et celui du PDF ne sont jamais écrits sur le disque.
- Le mot de passe `demo2024` du PDF de test sert uniquement aux tests d'erreur
  et ne protège aucune donnée réelle.
