# ace-vision

Analyse des vidéos de matchs de tennis (simple) d'un joueur amateur, pour lui dire comment améliorer son jeu.

## Le jeu

**Frappe**:
Tout contact entre une raquette et la balle, du joueur ou de l'adversaire.
_Avoid_: hit, touche

**Coup**:
Une frappe du joueur, avec son type : coup droit, revers, service ou autre (volée, smash, lob…).
_Avoid_: shot (côté interface), geste

**Échange**:
La suite de frappes entre un service et le moment où la balle est morte. Une première balle de service faute forme à elle seule un échange d'une frappe.
_Avoid_: rallye, jeu

**Point**:
Ce qu'un joueur gagne ou perd ; il contient un ou deux échanges (deux si la première balle de service est faute).
_Avoid_: échange

## L'analyse

**Match**:
Une vidéo analysée, avec sa date, sa durée, sa vue et un titre libre facultatif.
_Avoid_: session, partie

**Vue**:
D'où l'iPhone filmait : « vue filet » (posé près du filet, tourné vers le joueur) ou « vue arrière » (derrière le joueur, tout le court visible).
_Avoid_: angle, cadrage

**Défaut**:
Un problème technique mesuré sur un seul coup (ex. préparation tardive sur ce coup droit).
_Avoid_: erreur, faute (réservé à la balle qui sort ou va dans le filet)

**Constat**:
Un défaut qui revient souvent sur un match, avec son chiffre (ex. préparation tardive sur 11 coups droits sur 25).
_Avoid_: diagnostic, insight

**Conseil**:
Texte rédigé à l'avance, avec un exercice, associé à un défaut.
_Avoid_: recommandation, astuce

**Faute**:
Frappe dont la balle finit dans le filet ou hors du court.
_Avoid_: erreur, défaut
