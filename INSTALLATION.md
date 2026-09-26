# ⚙️ INSTALLATION COMPLÈTE — Studio d'agents Roblox

> Le guide pas-à-pas pour que **tout marche**. Suis les étapes dans l'ordre.

---

## 1. Ce qu'il faut avoir (prérequis)

| # | Élément | Comment l'obtenir |
|---|---|---|
| 1 | **Node.js** ≥ 18 | [nodejs.org](https://nodejs.org) — installe la version LTS |
| 2 | **Claude Code** | Dans un terminal : `npm install -g @anthropic-ai/claude-code` |
| 3 | **Compte Claude** (abonnement) | [claude.com](https://claude.com) — nécessaire pour utiliser Claude Code |
| 4 | **Roblox Studio** | [create.roblox.com](https://create.roblox.com) |
| 5 | **MCP Higgsfield** (optionnel, pour la 3D) | Voir section 5 |

## 2. Les fichiers (déjà prêts)

```
studio-agents-roblox.zip
├── CLAUDE.md                    ← source de vérité du projet
├── README.md                    ← résumé rapide
├── GUIDE-COLLABORATEUR.md       ← guide complet
└── .claude/
    ├── agents/                  ← 14 agents spécialisés
    └── skills/                  ← 10 packs de connaissances
```

## 3. Mise en place (5 minutes)

### Étape 1 — Dézipper dans le dossier du jeu

Dézippe `studio-agents-roblox.zip` **à la racine du dossier de ton jeu Roblox**.
Résultat attendu :

```
ton-jeu-roblox/
├── CLAUDE.md
├── README.md
├── GUIDE-COLLABORATEUR.md
├── .claude/
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

### Étape 4 — Vérifier que tout est chargé

```
/agents    → doit lister 14 agents
/skills    → doit lister 10 skills
```

Si les agents n'apparaissent pas : vérifie que `.claude/` est bien **à la
racine** du dossier où tu as lancé `claude`.

## 4. Premier test

```
@map  Voici un screenshot d'une map type "Steal Egg". Analyse-le et
      reproduis la map fidèlement.
```

Ou une demande globale :

```
Je veux un système de double saut + un inventaire + une map de forêt.
```

## 5. Configurer le MCP Higgsfield (pour la génération 3D)

Le MCP relie Higgsfield à Claude Code pour générer des modèles 3D.

### Étape 1 — Récupérer la commande MCP

Va dans la doc Higgsfield et récupère la **commande d'installation MCP**
(elle ressemble généralement à quelque chose comme `npx higgsfield-mcp` ou une
URL de serveur). C'est cette commande que tu vas enregistrer.

### Étape 2 — Enregistrer le MCP dans Claude Code

```bash
claude mcp add higgsfield -- <commande fournie par Higgsfield>
```

*(Remplace `<commande fournie par Higgsfield>` par la vraie commande.)*

### Étape 3 — Vérifier

Dans Claude Code, tape :

```
/mcp
```

Tu dois voir le serveur `higgsfield` connecté avec ses outils.

> 💡 Le skill `higgsfield-3d-assets` est **générique** : il découvre les outils
> MCP dynamiquement, donc il marche avec n'importe quelle commande MCP de
> génération 3D (Higgsfield ou autre).

## 6. Utilisation au quotidien

- **Demande globale** → écris normalement, le `lead` découpe et délègue.
- **Agent précis** → `@nom-agent` (ex. `@performance`, `@security`, `@gui`).
- **Skill précis** → « Utilise le skill `datastore-patterns` ».

## 7. Transfert à un collègue

1. Envoie-lui `studio-agents-roblox.zip`.
2. Il suit ce guide (sections 1 à 5).
3. Il lance `claude` dans son dossier de jeu et vérifie avec `/agents`.

C'est tout. 🚀
