# CLAUDE.md — Contexte global du projet Roblox

Ce fichier est la **source de vérité** du projet. Tous les agents (subagents) et
skills s'y réfèrent. Mets-le à jour à chaque décision d'architecture importante.

## 🎯 Vision

Créer des jeux Roblox **à fort potentiel de croissance** (objectif : +1M joueurs),
robustes, sécurisés, performants et rentables. La qualité de production prime sur
la rapidité de prototypage.

## 🧭 Principes directeurs (non négociables)

1. **Performance d'abord** — un jeu qui lag perd ses joueurs. Chaque feature doit
   être pensée pour tourner à 60 FPS sur mobile bas de gamme.
2. **Sécurité par défaut** — tout ce qui touche à l'argent, aux stats ou aux
   classements est validé **côté serveur**. Jamais de confiance au client.
3. **Fiabilité des données** — aucune perte de données de joueur n'est acceptable.
   DataStore avec retry, cache et sauvegardes périodiques.
4. **Rétention avant monétisation** — on fidélise d'abord, on monétise ensuite.
5. **Code maintenable** — modules, fonctions courtes, commentaires en français,
   séparation client/serveur stricte.

## 🧱 Architecture technique

- **Langage** : Luau (Roblox).
- **Modèle** : client/serveur strict.
  - `ServerScriptService` → logique serveur (autorité).
  - `StarterPlayerScripts` / `StarterCharacterScripts` → logique client (rendu, input).
  - `ReplicatedStorage` → modules partagés + RemoteEvents/RemoteFunctions.
  - `ServerStorage` → assets serveur (pas répliqués).
- **Communication** : RemoteEvents (fire) et RemoteFunctions (request/response),
  **jamais** d'appel direct entre client et serveur en dehors de ça.
- **State management** : un module `State` côté serveur fait autorité ; le client
  ne fait que refléter l'état répliqué.

## 📁 Conventions

- Nommage : `PascalCase` pour les modules/services, `camelCase` pour les variables.
- Chaque système = un ModuleScript avec une API claire.
- **Code et commentaires en anglais**, partout (Luau comme Python/Blender).
  Seule la documentation Markdown est en français.
- Pas de `while true do ... wait()` sans garde-fou ; préférer `RunService.Heartbeat`
  ou les events.

## 🗂️ Où écrire les fichiers (Rojo) — IMPÉRATIF

Le projet n'est **pas** édité directement dans Studio : le code vit sur disque et
Rojo le synchronise. `KaijuHeist/default.project.json` définit le mapping. Écris
toujours dans `src/`, **jamais** dans une arborescence Roblox imaginaire :

| Dossier disque | Destination Roblox |
|---|---|
| `KaijuHeist/src/Shared/` | `ReplicatedStorage.Shared` |
| `KaijuHeist/src/Server/` | `ServerScriptService.Server` |
| `KaijuHeist/src/Client/` | `StarterPlayer.StarterPlayerScripts.Client` |

Règles :
- Un module = `NomDuService.lua` (devient un `ModuleScript`).
- Seul un script d'amorçage porte `.server.lua` / `.client.lua` (devient un
  `Script` / `LocalScript`). Aujourd'hui : `Main.server.lua` et `Main.client.lua`.
- Un module serveur require ses voisins via `script.Parent.NomDuService`, et les
  modules partagés via `game:GetService("ReplicatedStorage").Shared.X`.
- Lancer la synchro : `rojo serve` depuis `KaijuHeist/`, puis « Connect » dans le
  plugin Rojo de Studio.

⚠️ `src/Shared/MapData.lua` est **généré** par `blender/build_map.py`. Ne l'édite
jamais à la main : il est écrasé à chaque génération de la map.

## 🤖 Comment piloter les agents

Parle à l'agent `lead` (chef d'orchestre). Il découpe ta demande et délègue aux
agents spécialisés. Tu peux aussi appeler un agent directement avec `@agent`.

Exemples :
- `@lead "Je veux un système de double saut + un inventaire + une map de forêt."`
- `@performance "Optimise ma map, elle lag sur mobile."`
- `@security "Audite mon système d'achat de devises."`

## 🎨 Génération d'assets 3D

### Voie principale : Blender procédural (c'est ce qui est en place)

La map est **générée par script**, pas modélisée à la main. Source unique :
`KaijuHeist/blender/build_map.py`.

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python "KaijuHeist/blender/build_map.py"
```

- Sortie : `KaijuHeist/assets/map/kaiju_heist_map.blend` + `.glb` + 3 previews PNG.
- Tout se règle dans le dict `CONFIG` en haut du script (nombre de plots, tailles,
  hauteur des murs, damier). **Ne modifie jamais le `.blend` à la main** : il est
  écrasé à chaque exécution. Modifie le script, puis relance.
- Le script doit rester tolérant à la langue de Blender : accède aux nœuds par
  **type** et aux sockets par **identifier**, jamais par nom traduit
  (un Blender en français nomme le nœud `BSDF guidée`).

### Voie optionnelle : génération 3D par MCP

Pour des assets ponctuels (créatures, props détaillés) qu'un script procédural
rend mal : skills `map-reference-analysis` puis `higgsfield-3d-assets`.

### Exigences Roblox (communes aux deux voies)

- Échelle : 1 stud = 1 unité Blender.
- **Limite dure : 10 000 triangles par MeshPart.** Découpe en plusieurs objets
  si besoin (la map actuelle : 38 objets, 93 718 tris, max 7 584 par objet).
- Textures PBR ≤ 1024×1024, couleurs fidèles à la référence.
- Import Studio : onglet Avatar → **3D Importer** → sélectionner le `.glb`.

## 📋 État du projet — KAIJU HEIST

- **Type de jeu** : simulateur de collection + vol PvP entre joueurs
  (formule « Steal a Brainrot × Pet Simulator »).
- **Boucle de jeu** : ramasser des **capsules** dans le monde → les faire éclore
  en **kaijus** (5 raretés) → les kaijus génèrent de l'**Ichor** passif →
  dépenser l'Ichor en upgrades de base (revenu) et de garde (défense) →
  **voler** l'Ichor des autres joueurs.
- **Plateformes** : PC + Mobile + Console. Session cible ~15 min.
- **Monétisation** : _(à définir — pas encore commencée)_
- **Statut** : prototype. Systèmes et map existent mais **ne sont pas encore
  reliés** (voir « Prochaine étape »).

### Ce qui existe

| Domaine | Fichiers | État |
|---|---|---|
| Économie / données | `src/Server/PlayerDataService.lua` | DataStore + autosave + cache |
| Capsules | `src/Server/CapsuleService.lua` | Spawn monde + ramassage au contact |
| Éclosion | `src/Server/HatchService.lua` | Tirage pondéré par rareté |
| Revenu passif | `src/Server/IncomeService.lua` | Tick toutes les 5 s |
| Vol PvP | `src/Server/StealService.lua` | Cooldown par paire, défense de la cible |
| Upgrades | `src/Server/BaseService.lua` | Base (revenu) + Garde (défense) |
| Données partagées | `src/Shared/Constants.lua`, `KaijuDatabase.lua`, `Remotes.lua` | Équilibrage centralisé |
| HUD | `src/Client/Main.client.lua` | Généré en code, fonctionnel mais brut |
| Map | `blender/build_map.py` → `assets/map/` | Générée, non importée en jeu |
| Ancres de map | `src/Shared/MapData.lua` (généré) | Prêt, pas encore consommé |

### La map en chiffres

Île flottante ~**950 × 430 studs**. Rue centrale de 72 studs de large, bordée de
**8 plots** (4 par côté) de 132 × 122 studs, séparés par des murs de 16
d'épaisseur et 40 de haut. Plaza de spawn à une extrémité, autel de boss à
l'autre. Par plot : 6 enclos, maison, stand VENDRE, stand BOUTIQUE, machine à
éclore, tapis roulant, ligne « ZONE SÛRE ».

Le couloir traverse **5 biomes** — Verte → Lave → Glace → Pierre → Désert —
définis dans la liste `BIOMES` de `build_map.py` et détaillés dans `ZONES.md`.
Ils sont exposés au gameplay par `MapData.zones` / `MapData.GetZoneAt()`, où
`index` croît avec la distance au spawn et sert de palier de difficulté.
Les plots restent en herbe verte dans tous les biomes, pour rester lisibles.

### Prochaine étape (la vraie priorité)

**Consommer `MapData.lua` dans les services.** Les coordonnées existent
désormais, plus rien n'est à deviner. Il reste trois branchements :

1. **Attribution de plot** — un nouveau `PlotService` assigne un des 8 plots
   (`MapData.plots`) à chaque joueur qui rejoint, et le téléporte sur son
   `plot.spawn`.
2. **Capsules dans la rue** — `CapsuleService` fait aujourd'hui spawn les
   capsules dans un rayon autour de l'origine. Remplacer par un tirage dans
   `MapData.capsuleZone`.
3. **Vol physique** — `StealService` cible les joueurs via une liste d'UI.
   Remplacer par un `ProximityPrompt` posé sur `plot.house` du plot visé, en
   gardant la validation serveur existante (cooldown + défense).

### Dettes connues

- Pas de tests, pas d'anti-cheat au-delà de la validation serveur de base.
- Propriétés Roblox non gérées par Blender, à régler après import :
  `StreamingEnabled`, `CanCollide` / `CanQuery` sur le décor, tags
  `CollectionService` sur les éléments interactifs.

_Mets à jour cette section à chaque étape majeure._
