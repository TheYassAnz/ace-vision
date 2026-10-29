# CLAUDE.md

## Workflow Git

Trunk Based Development : `main` est le seul tronc et reste toujours livrable.
Pas de branche `develop` ni `release/` ; une release est un tag `v*` (voir `.github/workflows/release.yml`).

### Branches

- Toujours partir de `main` à jour (`git pull --ff-only` puis `git switch -c ...`).
- Nom : `<type>/<description-courte-en-kebab-case>`, par exemple `fix/skeleton-overlay`.
- Types autorisés : `feature/`, `fix/`, `hotfix/`, `docs/`, `chore/`, `refactor/`.
- Branches courtes : 1 à 2 jours maximum. Se resynchroniser sur `main` avant d'ouvrir la PR, supprimer la branche après le merge.

### Interdit

- Committer sur `main`.
- Pousser sur `main`, force-push compris. Tout passe par une Pull Request.

Si tu es sur `main` au moment de modifier du code, crée d'abord la branche avec le bon préfixe.
Le hook `.claude/hooks/git_guard.py` bloque ces cas ; ne le contourne pas.

### Commits

Conventional Commits : `type(scope): sujet`, le scope est facultatif (par exemple `fix(app): ...`).
Types : `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci`.
