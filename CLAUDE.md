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

⚠️ `src/Shared/MapData.lua` et `src/Server/MapColliders.lua` sont **générés** par
`blender/build_map.py`. Ne les édite jamais à la main : ils sont écrasés à chaque
génération de la map.

La map elle-même (le GLB importé) vit dans `Workspace` de la place Studio, pas
dans Rojo : après l'avoir importée, **enregistre la place**. Guide : `MAPS.md`.

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

- Sortie : `KaijuHeist/assets/map/kaiju_heist_map.blend` + `.glb`, un GLB par
  section dans `assets/map/sections/`, 5 previews PNG, plus `MapData.lua` et
  `MapColliders.lua`. Le script s'auto-vérifie (`CHECKS passed=… failed=…`).
- Tout se règle en haut du script : `CONFIG` (tailles), `BIOMES` (zones),
  `PALETTE` (couleurs + matière Roblox). **Ne modifie jamais le `.blend` à la
  main** : il est écrasé à chaque exécution. Modifie le script, puis relance.
- Une pièce (ou un groupe) avec l'attribut `KeepStudioLook = true` garde la
  couleur réglée dans Studio au lieu de la palette.
- Contrat avec Roblox (voir `MAPS.md`) : **une matière par objet**, nommé
  `<Nom>__<clé>` ; les collisions sont des volumes invisibles listés dans
  `MapColliders.lua`, jamais les meshes ; 3 repères `REF_*` permettent à
  `MapService` de recaler le modèle importé.
- Le script doit rester tolérant à la langue de Blender : accède aux nœuds par
  **type** et aux sockets par **identifier**, jamais par nom traduit
  (un Blender en français nomme le nœud `BSDF guidée`).

### Voie optionnelle : génération 3D par MCP

Pour des assets ponctuels (créatures, props détaillés) qu'un script procédural
rend mal : skills `map-reference-analysis` puis `higgsfield-3d-assets`.

### Exigences Roblox (communes aux deux voies)

- Échelle : 1 stud = 1 unité Blender.
- **Limite dure : 10 000 triangles par MeshPart.** Le script découpe tout seul
  au-delà de 9 500 (la map actuelle : 217 objets, 86 656 tris, max 4 148 par
  objet).
- Textures PBR ≤ 1024×1024, couleurs fidèles à la référence.
- Import Studio : onglet Avatar → **3D Importer** → sélectionner le `.glb`.

## 🍝 Second projet — BRAINROT FIGHTER

Jeu de combat/collection (formule Anime Fighters Simulator, univers « brainrot »).
Tout vit dans `BrainrotFighter/` (le reste de ce fichier concerne Kaiju Heist).
- Zone 1 « Spaghetti Beach » : `BrainrotFighter/blender/z1_spaghetti_beach.py`
  génère le kit de décor (20 assets `Z1_*`, une couleur par mesh), l'aperçu de la
  zone 800 × 800 et un **FBX par asset** (réglages Roblox). Guide :
  `BrainrotFighter/README.md`. Pas encore importé dans Studio.

## 📋 État du projet — KAIJU HEIST

- **Type de jeu** : simulateur de collection + vol PvP entre joueurs
  (formule « Steal a Brainrot × Pet Simulator »).
- **Boucle de jeu** : ramasser des **capsules** dans le monde → les faire éclore
  en **kaijus** (5 raretés) → les kaijus génèrent de l'**Ichor** passif →
  dépenser l'Ichor en upgrades de base (revenu) et de garde (défense) →
  **voler** l'Ichor des autres joueurs.
- **Plateformes** : PC + Mobile + Console. Session cible ~15 min.
- **Monétisation** : _(à définir — pas encore commencée)_
- **Statut** : prototype. La map en T (lobby + 4 bases + 5 zones + arène) est
  générée et **reliée aux services** : spawn au lobby, portails, attribution des
  bases, capsules dans les zones. Pas encore testée dans Studio (voir `MAPS.md` §6).

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
| Bandeau de zone | `src/Client/ZoneBanner.lua` | Nom de la zone à l'entrée |
| Map | `blender/build_map.py` → `assets/map/` | Plan en T : lobby + 4 bases + 5 zones + arène, GLB prêt à importer |
| Ancres de map | `src/Shared/MapData.lua` (généré) | Consommé par les services ci-dessous |
| Collisions de map | `src/Server/MapColliders.lua` (généré) | 501 volumes invisibles |
| Mise en jeu de la map | `src/Server/MapService.lua` | Recalage, couleurs, collisions, spawns, portails |
| Bases | `src/Server/PlotService.lua` | 1 base par joueur, étiquette du propriétaire |
| Assets UI | `tools/build_ui_assets.py` → `assets/ui/` | 90 PNG style simulateur (boutons, tuiles, fenêtres, icônes, logo), voir `assets/ui/README.md` |

### La map en chiffres

Plan en **T** dessiné par l'utilisateur (`assets/map/plan_reference.png`).
La barre : un **lobby** de 440 × 660 studs (statue géante d'un kaiju au centre
d'un bassin, colonnade, 8 spawns, galerie de 6 portails, classement, 5 œufs de
rareté, cadeau du jour, tutoriel, 4 tours), avec **4 bases** (B1…B4, 132 × 122,
murs de marbre) alignées sur son côté ouest et **deux boutiques** (BOUTIQUE /
VENTE et VITESSE) à l'entrée du couloir. La tige : une **porte monumentale**
puis un **couloir** de 112 de large et 900 de long, découpé en 5 zones, qui
finit sur l'**arène circulaire du boss**. Par base : 6 enclos, maison, stand
VENDRE, stand BOUTIQUE, machine à éclore, tapis roulant, ligne « ZONE SÛRE ».
Les bases sont identiques (un seul modèle instancié ; `base_count` dans
`CONFIG`).

Le couloir traverse **5 biomes** — Verte → Lave → Glace → Pierre → Désert —
définis dans la liste `BIOMES` de `build_map.py` et détaillés dans `ZONES.md`.
Ils sont exposés au gameplay par `MapData.zones` / `MapData.GetZoneAt()` /
`MapData.GetAreaAt()` (lobby compris), où `index` croît avec la distance au
lobby et sert de palier de difficulté. Chaque zone a son `spawn` (destination
de portail) et sa `capsuleArea`.
Les bases restent en herbe verte, pour rester lisibles.

### Prochaine étape (la vraie priorité)

1. **Tester l'import dans Studio** (`MAPS.md` §3) : c'est la seule partie de la
   chaîne qui n'a pas pu être mesurée. Vérifier les deux lignes `MapService:`
   de l'Output.
2. **Vol physique** — `StealService` cible les joueurs via une liste d'UI.
   Remplacer par un `ProximityPrompt` posé sur `plot.house` du plot visé, en
   gardant la validation serveur existante (cooldown + défense).
3. **Kaijus visibles** sur les socles des enclos (`MapData.plots[i].pens`).

### Dettes connues

- Pas de tests, pas d'anti-cheat au-delà de la validation serveur de base.
- `StreamingEnabled` reste à activer dans Studio. (`CanCollide` / `CanQuery`
  du décor sont désormais réglés par `MapService` au lancement.)

_Mets à jour cette section à chaque étape majeure._
