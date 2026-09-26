# Mémoire Claude — mode d'emploi

Ce dossier contient la **mémoire persistante** de Claude Code pour ce projet.
Elle est séparée du code : ce sont des notes sur *comment travailler sur ce
projet*, pas sur le projet lui-même.

## Pour la réactiver sur une autre machine

Copie le contenu de ce dossier vers :

```
~/.claude/projects/<slug-du-projet>/memory/
```

Sur Windows, le chemin ressemble à :

```
C:\Users\<toi>\.claude\projects\C--Users-<toi>-Desktop-JEUX-A-CREER\memory\
```

Le slug est dérivé du chemin absolu du projet : les séparateurs deviennent des
tirets. Si tu places le projet ailleurs, adapte le nom du dossier — sinon Claude
ne trouvera pas la mémoire.

## Pour t'en servir sans rien installer

Si tu ouvres simplement une nouvelle conversation, il suffit de dire à Claude de
lire ces fichiers, ou de lui donner `HANDOFF.md` à la racine du projet — qui
contient le contexte complet sous une forme lisible.

## Ce qu'il y a dedans

| Fichier | Contenu |
|---|---|
| `MEMORY.md` | index, chargé en premier |
| `user-profile.md` | qui tu es, ton projet, ta façon de travailler |
| `feedback-langue.md` | français pour parler, anglais pour coder |
| `feedback-verification.md` | mesurer et prouver plutôt qu'affirmer |
| `feedback-dire-non.md` | t'avertir avant de dépenser sur une piste vouée à l'échec |
| `project-blender-locale.md` | le piège du Blender en français |
| `project-kit-agents.md` | le kit d'agents à merger, jamais à extraire par-dessus |

## Hiérarchie des documents du projet

1. **`HANDOFF.md`** — pourquoi le projet est dans cet état (décisions, échecs, pièges)
2. **`CLAUDE.md`** — état actuel, règles, arborescence Rojo
3. **`ZONES.md`** — les 5 biomes et les 5 segments autonomes
4. **ce dossier** — comment collaborer

Dans une nouvelle conversation, l'ordre de lecture est celui-là.
