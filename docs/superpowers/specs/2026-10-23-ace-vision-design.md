# ace-vision — Document de conception

Date : 2026-10-23 · Statut : validé par l’utilisateur (2026-10-23)

## 1. Intention

Un joueur amateur filme ses matchs de tennis avec son iPhone. Il veut savoir **comment améliorer son jeu** — pas seulement des chiffres. Déclencheur : un match où ses coups droits « ne passaient pas » sans qu'il sache pourquoi ni quoi changer.

ace-vision analyse la vidéo d'un match sur son Mac et produit un **bilan** : statistiques des échanges et des coups (coup droit, revers, service), où se produisent les fautes, et 2-3 conseils concrets appuyés par des chiffres et des extraits vidéo.

**Critère de succès (utilisateur) :** « l'app aura servi si mon tennis est bon ». Traduction pour le builder : les conseils doivent être **justes, précis et actionnables** sur le court. Un conseil vague ou faux = échec, même si les stats sont parfaites.

## 2. Utilisateur et contexte

- Un seul utilisateur : le joueur lui-même. Usage personnel.
- Il filme **souvent** ses matchs avec un **iPhone fixe**, aujourd'hui **posé à côté du filet, tourné vers lui** (il est au fond du court). Il a aussi cité « derrière moi » comme position possible, mais **n'a aucune vidéo filmée de derrière** à ce jour.
- **Matchs en simple uniquement.** Il **ne change pas de côté** pendant les matchs filmés : il reste toujours dans la même moitié du court.
- Vidéo d'exemple : `videos/IMG_2665.mov` — 30 s, HEVC, **portrait** 1116×1986, **30 i/s**, caméra près du filet ; on le voit en entier, de face, au fond du court ; on ne voit ni le filet ni le reste du court.
- Il accepte d'**annoter** des images (position de balle, coups) pour réentraîner/valider les modèles.
- Machine d'analyse : **Mac Apple M4 Pro, 24 Go de RAM**.
- Il connaît Python (projets `my-agent`, `whisper`), Next.js/TypeScript (`tennis-score`), Swift.

## 3. Objectifs (V1)

Deux types de vidéo à gérer (détecté ou choisi à l'import) :
- **« Vue filet »** (ce qu'il a aujourd'hui) : joueur de face, court peu visible → technique, coups, conseils ; **pas** d'issue des balles ni de carte des fautes.
- **« Vue arrière »** (paysage, 60 i/s, iPhone derrière lui en hauteur, tout le court visible) → bilan B complet.
Le bilan **masque les blocs non calculables** au lieu d'inventer des chiffres.


1. **Importer** une vidéo de match dans l'**appli web locale** (bouton « Ajouter une vidéo », fichier .mov/.mp4 transféré depuis l'iPhone) en précisant la **vue** (filet/arrière) et un **titre libre facultatif**. **Un match = une vidéo** (si plusieurs fichiers, l'utilisateur les colle avant avec une commande fournie). L'app garde une **copie** de la vidéo dans `data/matchs/<date>-<nom>/` (hors git) ; ré-analyser remplace l'analyse précédente. **Pas de suppression** dans l'app en V1 (l'utilisateur nettoie le dossier lui-même).
2. **Analyser** automatiquement, sans saisie manuelle pendant le match :
   - suivre la balle (TrackNet) ;
   - repérer **le joueur** (toujours dans la même moitié du court : la plus proche de la caméra en vue arrière, celle face à la caméra en vue filet) et sa pose corporelle image par image ;
   - découper le match en **échanges** ; pour chacun : nombre de frappes, comment il se termine (filet, dehors, balle non renvoyée), quel coup le termine ;
   - classer **les coups du joueur** : coup droit, revers, service, sinon **« autre »** (volée, smash, lob… comptés, sans analyse technique). Un coup bras au-dessus de la tête précédé d'**au moins 3 s sans frappe** = service, sinon « autre » ;
   - détecter **4 défauts** par coup (mesurables en 2D, vue filet comme arrière) : **préparation tardive** (rotation des épaules finie < 0,4 s avant l'impact), **rotation des épaules insuffisante**, **jambes trop tendues**, **appuis trop serrés**. Seuils de départ = repères d'entraîneur, ajustés sur ses vidéos.
3. **Conseiller** : relier technique et résultat (ex. « 11 de tes 14 coups droits dans le filet sont frappés épaule non tournée ») ; **sans IA générative en V1** (décision utilisateur) : des **règles** détectent les défauts mesurés (ex. préparation tardive, impact derrière la hanche) et choisissent dans une **bibliothèque de conseils rédigés à l'avance en français** (texte + exercice). Un défaut devient un **constat** s'il touche **≥ 40 % des coups de ce type et ≥ 5 coups** ; le bilan affiche les **3 constats** les plus fréquents, chacun avec son chiffre, son conseil + exercice et ses extraits vidéo.
4. **Afficher le bilan** (maquette validée : version « B — les chiffres d'abord ») dans le navigateur du Mac, de haut en bas :
   1. *Vue d'ensemble* : nb d'échanges, longueur moyenne et max ; par coup : nb frappés et % de fautes ; service : % de 1res balles, doubles fautes.
   2. *Où ça casse* : carte du court des fautes (filet/long/large), fautes selon la longueur de l'échange (1-3 / 4-6 / 7+ coups), coup qui termine les points perdus.
   3. *Conseils* : 2-3 conseils avec extraits vidéo cliquables.
5. **Historique** : page d'accueil = liste des matchs (date lue dans la vidéo, durée, vue, titre, 2-3 chiffres clés, statut) ; un clic ouvre le bilan. Une **liste suffit en V1**.
6. **Appli web locale** : démarrée par une **icône à double-cliquer** (« ACE Vision », glissable dans le Dock) qui lance le serveur et ouvre **Safari** (lecture HEVC native, pas de conversion). **Une analyse à la fois** avec barre de progression ; si l'app est fermée ou plante en cours, le match passe **« échoué »** avec un bouton **« Relancer »**. Page **Réglages** (une fois pour toutes) : droitier/gaucher, revers à 1 ou 2 mains.
7. **Vérification de la détection** : dans la page d'un match, bouton **« Noter mes coups »** : la vidéo défile, l'utilisateur appuie sur **D** (coup droit), **R** (revers), **S** (service), **A** (autre) ; l'app compare ses détections à ces notes et affiche son score. Objectif V1 : **≥ 90 % des coups trouvés, ≥ 85 % bien classés** (sur `IMG_2665.mov` puis un vrai match).

## 4. Non-objectifs (V1)

- Pas d'app iPhone : l'iPhone ne sert qu'à filmer.
- Pas d'analyse **en direct** pendant le match : l'analyse se fait après.
- Pas de graphiques d'évolution / comparaison entre matchs (peut venir plus tard).
- Pas d'intégration avec `tennis-score` (possible plus tard ; il a déjà Match/Set/Point).
- Pas d'analyse détaillée de l'adversaire : ses frappes sont détectées pour compter les échanges, mais son type de coup peut rester « inconnu ».
- Pas de mise en ligne, pas de comptes utilisateurs, pas de multi-utilisateurs.
- Pas de calcul du score du match.
- Pas de suppression de match dans l'app, pas de file d'attente d'analyses, pas de détection automatique de la vue.
- Pas de conseils rédigés par une IA générative (Claude ou autre) — envisageable en V2.
- Pas de double, pas de suivi du joueur s'il change de côté.
- Pas de caméra mobile ni tenue à la main.

## 5. Anti-objectifs (ce qui ferait échouer le projet même si « ça marche »)

- Des **conseils génériques** (« fléchis les genoux ») non reliés à ce que la vidéo montre.
- Des **conseils affirmés sur des données fausses** : si la détection n'est pas fiable pour un coup ou un indicateur, le bilan doit le dire ou se taire, pas inventer.
- Un bilan qui ne permet pas de **revoir les coups** concernés en vidéo (l'utilisateur doit pouvoir vérifier).

## 6. Contraintes

- Tout tourne **en local sur le Mac**, **sans aucun service en ligne** : rien ne quitte le Mac, pas de clé API.
- Temps d'analyse : plusieurs minutes pour un match d'1 h est acceptable (hypothèse).
- Caméra **fixe** pendant toute la vidéo (confirmé).
- Vidéo iPhone : portrait ou paysage, 30 ou 60 i/s, HEVC (.mov).

## 7. Décisions prises (« comment »)

| Sujet | Décision | Origine |
|---|---|---|
| Où tourne l'analyse | Sur le Mac | Utilisateur |
| Capture | iPhone, côté du court ou derrière le joueur | Utilisateur |
| Langage d'analyse | **Python** | Proposé par Claude, accepté |
| Suivi de balle | **TrackNet** (famille V2/V3/V4), réentraîné sur les vidéos de l'utilisateur si besoin | Utilisateur, après comparaison avec Vision d'Apple |
| Rédaction des conseils | **Pas d'IA générative en V1** : règles sur les mesures + conseils pré-rédigés. Pas de clé API Claude | Utilisateur |
| Présentation | **Appli web locale en Python seul** (serveur FastAPI qui génère le HTML, un peu de JavaScript), ouverte dans Safari ; mise en page « B » | Utilisateur |
| Outillage | `uv` + **Python 3.12** ; code en anglais, tout le texte visible en français | Utilisateur |
| Vocabulaire | Voir `GLOSSARY.md` (frappe, coup, échange, point, défaut, constat, conseil, faute, match, vue) | Utilisateur |
| Historique | Liste simple des matchs analysés | Utilisateur |
| Main forte / type de revers | Réglage utilisateur (droitier/gaucher, revers 1 ou 2 mains) | Choix de Claude |
| Juge des conseils | L'utilisateur, en revoyant les extraits liés à chaque conseil | Choix de Claude |
| Données publiques | Jeux de données de **recherche** (TrackNet, RacketVision…) pour la vue arrière, licence vérifiée avant usage ; **pas** de matchs officiels téléchargés (droits, CGU YouTube) | Utilisateur d'accord avec la proposition |

**Ordre des travaux (accepté par l'utilisateur) :**
1. **Vues filet de l'utilisateur** : détection des frappes, classification coup droit/revers/service, mesures techniques, conseils, bilan + historique (blocs « issue/carte » masqués).
2. **Jeux de données publics (vue arrière)** : suivi de balle TrackNet, détection du court, découpage des échanges, issue (filet/long/large), carte des fautes.
3. **Première vidéo arrière de l'utilisateur** : réentraînement/validation sur ses images, assemblage du bilan B complet.

Contexte recherche (vérifié le 2026-10-23) : TrackNet (arXiv 1907.03698) atteint 99,7 % de précision / 97,3 % de rappel sur un découpage favorable mais **95,3 % / 75,7 %** en validation croisée, sur des images télé ; un modèle appliqué à un autre contexte s'effondre (22,9 % de rappel tennis→badminton) → le **réentraînement sur l'angle iPhone est probable**. TrackNetV4 (arXiv 2409.14543) ajoute des cartes d'attention de mouvement, testé sur tennis.

## 8. Laissé au builder

- Modèle de pose (ex. YOLO-pose, RTMPose, MediaPipe, Vision d'Apple via pyobjc…) et détection des joueurs.
- Détection des lignes du court et projection sur un plan du court (homographie) pour la carte des fautes.
- Méthode de classification des coups (règles sur la pose, petit classifieur sur séquences de pose, etc.) et de détection des frappes/rebonds.
- Indicateurs techniques exacts par coup et seuils.
- Format de stockage local par match (JSON, SQLite…).
- Outil d'annotation pour créer les données de réentraînement de TrackNet et de vérification (vérité terrain).
- Choix et licence des jeux de données publics (TrackNet, RacketVision…) et des modèles pré-entraînés.

## 9. Risques principaux

1. **Suivi de balle sur vidéo amateur** (balle petite/floue, 30 i/s) : en vue filet, il sert surtout à dater les frappes ; en vue arrière c'est le pilier du bilan B. À valider tôt sur une vraie vidéo.
2. **Fiabilité de la classification coup droit / revers / service** depuis le côté du court.
3. **Qualité des conseils** : dépend de mesures techniques fiables ; prévoir de valider les conseils sur quelques matchs réels.
4. **Pas encore de vidéo arrière de l'utilisateur** : la partie 2 est mise au point sur des images télé (caméra plus haute, jeu plus rapide) et devra être revalidée.
5. **Vue filet** : le joueur est de face ; distinguer coup droit/revers et mesurer la rotation des épaules depuis cet angle est à valider.
