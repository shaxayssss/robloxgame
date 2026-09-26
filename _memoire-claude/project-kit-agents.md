---
name: project-kit-agents
description: Le kit studio-agents-roblox est generique et ecrase le travail projet a chaque version
metadata:
  type: project
---

L'utilisateur recoit periodiquement un kit `studio-agents-roblox.zip` (agents +
skills Claude Code pour Roblox). Deux versions recues a ce jour.

**Why:** chaque version contient les agents et `CLAUDE.md` dans leur etat
**generique d'origine**. Extraire le zip par-dessus le projet efface tout le
travail d'adaptation — c'est ce qui a failli arriver avec la v2, evite en
comparant avant d'extraire.

**How to apply:** ne jamais extraire par-dessus. Extraire a part, comparer
fichier par fichier, prendre le nouveau contenu et preserver le specifique au
projet. Defauts qui reviennent a chaque version : la faute « non-bloante » dans
le skill Luau, une arborescence de dossiers qui contredit le Rojo reel, et un
`config.json` inerte (Claude Code lit `settings.json`).

A savoir : l'agent `map` n'a **aucun outil MCP** dans son frontmatter, il ne peut
donc pas generer d'assets 3D tant qu'on ne le lui ajoute pas.
