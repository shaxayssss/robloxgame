# 📘 Guide de passation — Studio d'agents IA pour jeux Roblox

> **À lire en premier.** Ce document contient tout ce qu'il faut savoir pour
> installer, comprendre et utiliser l'équipe d'agents IA qui développe des jeux
> Roblox à fort potentiel (+1M joueurs).

---

## 1. C'est quoi ?

Un **système d'agents IA spécialisés** pour Claude Code. Au lieu de tout coder
toi-même, tu parles à un **chef d'orchestre** (l'agent `lead`) qui découpe ta
demande et délègue à des **agents spécialisés** (gameplay, GUI, map, données,
sécurité, etc.).

```
Toi → lead (découpe) → agents spécialisés (implémentent)
                     → qa (vérifie) → lead (intègre) → Toi
```

## 2. Prérequis

| Outil | Rôle | Où l'obtenir |
|---|---|---|
| **Claude Code** | L'outil qui exécute les agents | [claude.com/claude-code](https://claude.com/claude-code) |
| **Compte Claude** (abonnement) | Fournit le modèle IA | claude.com |
| **Roblox Studio** | L'éditeur du jeu | create.roblox.com |
| **Node.js** (≥ 18) | Requis par Claude Code | nodejs.org |

> 🎨 **Higgsfield** est relié à Claude Code via un **MCP** pour générer des
> **modèles 3D** (pas seulement des vidéos). Il s'utilise via les skills
> `map-reference-analysis` et `higgsfield-3d-assets`.

## 3. Installation (5 minutes)

### Étape 1 — Copier les fichiers dans le projet

Copie ces deux éléments **dans le dossier racine de ton jeu Roblox** :

```
ton-jeu-roblox/
├── CLAUDE.md            ← à copier ici
├── .claude/             ← tout le dossier (agents + skills)
│   ├── agents/
│   └── skills/
└── ... (tes fichiers de jeu)
```

### Étape 2 — Ouvrir un terminal dans ce dossier

```bash
cd chemin/vers/ton-jeu-roblox
```

### Étape 3 — Lancer Claude Code

```bash
claude
```

Claude Code détecte **automatiquement** le dossier `.claude/` et charge les
agents + skills. Pour vérifier :

```
/agents
```

Tu dois voir 14 agents listés.

---

## 4. Comment ça marche ?

### Les agents (`.claude/agents/`)

Chaque fichier `.md` définit un **agent spécialisé** avec :
- un **nom** (`name`)
- une **description** (utilisée pour le routage automatique)
- des **outils** autorisés (`tools`)
- un **modèle** (`model`) — `opus` pour le lead, `sonnet` pour les autres
- des **instructions** (son rôle, ses règles, ses frontières)

### Les skills (`.claude/skills/`)

Chaque dossier contient un `SKILL.md` : un **pack de connaissances** (bonnes
pratiques Luau, patterns DataStore, anti-cheat…). Ils sont chargés
**automatiquement** quand une tâche correspond.

### Le CLAUDE.md

La **source de vérité** du projet : vision, règles, architecture, état. Tous les
agents s'y réfèrent. **À mettre à jour** à chaque décision majeure.

---

## 5. Utilisation au quotidien

### Parler au chef d'orchestre (recommandé)

Écris ta demande normalement, le `lead` découpe et délègue :

```
Je veux un système de double saut + un inventaire + une map de forêt.
```

### Cibler un agent précis avec `@`

```
@performance  Optimise ma map, elle lag sur mobile.
@security     Audite mon système d'achat de devises.
@gui          Crée le menu principal responsive.
```

### Forcer un skill

```
Utilise le skill datastore-patterns pour implémenter la sauvegarde.
```

---

## 6. Référence des 14 agents

| Agent | Rôle | Quand l'utiliser |
|---|---|---|
| `lead` | Chef d'orchestre | Toute demande globale / nouvelle feature |
| `gameplay` | Mécaniques de jeu (Luau) | Combat, déplacements, progression, pouvoirs |
| `gui` | UI/UX | Menus, HUD, inventaire, boutique |
| `map` | Level design / environnement | Terrain, builds, niveaux, éclairage |
| `data` | DataStore / persistance / économie | Sauvegarde, devises, inventaire |
| `networking` | Client/serveur / réplication | RemoteEvents, RemoteFunctions |
| `art` | Assets / animation / VFX / sons | Modèles 3D, animations, effets |
| `monetization` | Monétisation / équilibrage | Gamepasses, dev products, prix |
| `performance` | Optimisation | FPS, mémoire, lags, profilage |
| `security` | Anti-cheat / durcissement | Validation serveur, exploits |
| `qa` | Revue de code / tests | Fin de cycle, détection de bugs |
| `onboarding` | Tutoriel / rétention | Première expérience, fidélisation |
| `localization` | i18n / traduction | Rendre le jeu multilingue |
| `analytics` | Télémétrie / live-ops | Mesure, rétention, itération |

## 7. Référence des 10 skills

| Skill | Contenu |
|---|---|
| `luau-best-practices` | Conventions, typage, modules, gestion des events |
| `roblox-api-reference` | Services et API Roblox essentiels |
| `client-server-architecture` | Remotes, validation serveur, anti-spam |
| `datastore-patterns` | Retry, caching, autosave, versioning, UpdateAsync |
| `performance-optimization` | FPS, streaming, LOD, anti-fuite mémoire |
| `monetization-economy` | ProcessReceipt, gamepasses, équilibrage |
| `retention-engagement` | Onboarding, daily rewards, boucles sociales |
| `security-hardening` | Anti-cheat, anti-duplication, validation |
| `map-reference-analysis` | Analyse de screenshots → spec de map fidèle |
| `higgsfield-3d-assets` | Génération de modèles 3D via le MCP Higgsfield |

---

## 8. Workflow recommandé

1. **Définir le jeu** → remplir la section "État du projet" de `CLAUDE.md`.
2. **Prototyper** → demander au `lead` une première feature jouable.
3. **Itérer** → ajouter des features via le `lead`.
4. **Auditer** → `@qa` + `@security` + `@performance` régulièrement.
5. **Mesurer** → `@analytics` pour suivre la rétention.
6. **Lancer** → publier, puis itérer par la donnée.

## 9. Bonnes pratiques pour viser +1M joueurs

1. **Performance d'abord** — un jeu qui lag perd ses joueurs. Teste sur mobile.
2. **Sécurité par défaut** — jamais de confiance au client.
3. **Fiabilité des données** — aucune perte de progression.
4. **Rétention avant monétisation** — fidélise, puis monétise.
5. **Itère par la donnée** — mesure, corrige, re-mesure.

## 10. FAQ / Dépannage

**Q : `/agents` ne montre pas mes agents ?**
→ Vérifie que le dossier `.claude/` est bien à la **racine** du projet et que tu
as lancé `claude` **dans ce dossier**.

**Q : Un agent ne s'active pas automatiquement ?**
→ Utilise `@nom-agent` pour le forcer explicitement.

**Q : Je veux ajouter un agent ?**
→ Crée un fichier `.claude/agents/mon-agent.md` avec le même format (frontmatter
`name`/`description`/`tools`/`model` + instructions).

**Q : Je veux changer de modèle ?**
→ Modifie le champ `model` dans le frontmatter de l'agent (`opus`, `sonnet`,
`haiku`, ou `inherit`).

**Q : Comment Higgsfield s'intègre ?**
→ Via un MCP relié à Claude Code. Il génère des modèles 3D (skills
`map-reference-analysis` + `higgsfield-3d-assets`). Vérifie les outils avec `/mcp`.

## 11. Personnalisation

- **Type de jeu** → mets à jour `CLAUDE.md` (section "État du projet").
- **Nouveau domaine** → ajoute un agent dédié (ex. `sound-design`).
- **Budget** → ajuste les `model` (haiku pour les tâches simples = moins cher).
- **Règles d'équipe** → ajoute tes conventions dans `CLAUDE.md`.
