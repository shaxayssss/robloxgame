# 🗺️ MAPS — De Blender à une partie jouable dans Roblox

> Guide complet de la map de Kaiju Heist : ce qu'elle contient, comment la
> générer dans Blender, comment l'importer dans Roblox Studio, et ce qui la rend
> jouable une fois importée. `ZONES.md` détaille les 5 zones ; ce document-ci
> couvre toute la chaîne.

---

## 1. Ce que contient la map

Ordre de marche, d'ouest en est :

```
LOBBY ──pont──► Zone Verte ► Zone de Lave ► Zone de Glace ► Zone de Pierre ► Zone Désert
 (spawn)         2 bases      2 bases        2 bases         2 bases          arène du boss
```

![Vue aérienne](KaijuHeist/assets/map/preview_aerial.png)

| Section | Taille | Contenu |
|---|---|---|
| **Lobby** | île de 220 × 220 | fontaine + **8 points de spawn**, **6 portails** (MA BASE, VERTE, LAVE, GLACE, PIERRE, BOSS), tableau CLASSEMENT + podium 1-2-3, vitrine des **5 raretés**, stand BOUTIQUE, coffre CADEAU, panneau COMMENT JOUER, arche KAIJU HEIST |
| **Pont** | 70 × 32 | relie le lobby à l'île principale, garde-corps solides |
| **Zone 1 — Verte** | 208 studs de long | place d'entrée (arche « ZONE VERTE », portail retour LOBBY) + 2 bases |
| **Zone 2 — Lave** | 148 | portique « ZONE DE LAVE », obsidienne, fissures de lave, volcans + 2 bases |
| **Zone 3 — Glace** | 148 | portique, pics de glace, château de glace, cristaux + 2 bases |
| **Zone 4 — Pierre** | 160 | portique, stalagmites, arche rocheuse, éboulis + 2 bases |
| **Zone 5 — Désert** | 203 | portique, cactus, 2 pyramides à gradins (escaladables), **autel du boss**, portail retour LOBBY |
| **Bases (« cases »)** | 132 × 122 chacune | 8 bases identiques N1…N4 / S1…S4 : 6 enclos avec portillon et socle, maison, VENDRE, BOUTIQUE, machine à éclore, tapis roulant, ligne ZONE SÛRE |

Les 8 bases sont **strictement identiques** (même modèle instancié) : aucun
joueur n'a une meilleure base qu'un autre. Elles restent en herbe verte dans
toutes les zones pour être reconnaissables d'un coup d'œil.

| Lobby | Rue (zone Verte → Lave → Glace) |
|---|---|
| ![Lobby](KaijuHeist/assets/map/preview_lobby.png) | ![Rue](KaijuHeist/assets/map/preview_street.png) |

| Une base | Arène du boss |
|---|---|
| ![Base](KaijuHeist/assets/map/preview_plot.png) | ![Boss](KaijuHeist/assets/map/preview_boss.png) |

---

## 2. Générer la map dans Blender

Un seul script : `KaijuHeist/blender/build_map.py`. Deux façons de le lancer.

**En ligne de commande** (le plus fiable) :

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python "KaijuHeist/blender/build_map.py"
```

**Depuis Blender** : onglet *Scripting* → *Ouvrir* → `build_map.py` → *Exécuter
le script*. Le script vide la scène lui-même (sans `read_factory_settings`) et
marche avec l'interface en français.

### Ce qui est produit

| Fichier | Rôle |
|---|---|
| `assets/map/kaiju_heist_map.glb` | **la map entière, à importer dans Roblox** |
| `assets/map/kaiju_heist_map.blend` | la même scène, pour la regarder dans Blender |
| `assets/map/sections/*.glb` | la même map découpée : `Lobby`, `Island`, `Zone1_Verte`… `Zone5_Desert`, `Plots` |
| `assets/map/preview_*.png` | 5 rendus : aerial, lobby, street, plot, boss |
| `src/Shared/MapData.lua` | positions pour le gameplay (spawns, portails, zones, bases, couleurs) |
| `src/Server/MapColliders.lua` | les 642 volumes de collision invisibles |

Tous ces fichiers sont **générés** : ne les modifie jamais à la main, relance le
script.

### Ce que le script vérifie tout seul

À chaque exécution, il mesure sa propre sortie et affiche :

```
MESH_BUDGET total=87320 objects=303 unique_meshes=133 max=1440 (...)
COLLIDERS total=642 {'ground': 17, 'solid': 611, 'barrier': 14}
CHECKS passed=373 failed=0
```

Les 373 contrôles : zones contiguës, chaque spawn posé sur un sol et libre de
tout mur, chaque portail atteignable, chaque zone de capsules dans sa zone et
libre de tout obstacle, chaque base dans la bonne zone, chaque objet sous
10 000 triangles avec **une seule** matière et un nom au bon format. Une ligne
`CHECK_FAIL` dit exactement quoi et où.

### Réglages par variables d'environnement (optionnel)

| Variable | Effet |
|---|---|
| `KAIJU_SKIP_RENDER=1` | ne fait pas les rendus (génération en quelques secondes) |
| `KAIJU_RENDER_ENGINE=CYCLES` | rendus sur CPU, pour une machine sans GPU |
| `KAIJU_RENDER_PERCENT=50` | rendus à 50 % de la taille (1600 × 900 par défaut) |

---

## 3. Importer dans Roblox Studio

1. Lance la synchro du code comme d'habitude : `rojo serve` depuis `KaijuHeist/`,
   puis *Connect* dans le plugin Rojo.
2. Supprime l'ancienne map importée s'il y en a une.
3. Importe **`assets/map/kaiju_heist_map.glb`** avec le 3D Importer (onglet
   Avatar → Import 3D). Laisse le modèle dans `Workspace`, **peu importe où il
   atterrit** : `MapService` le recale tout seul (voir §4).
4. **Enregistre la place.** Rojo ne gère pas `Workspace` : la map vit dans le
   fichier de la place, pas dans le dépôt.
5. Paramètres du jeu → nombre de joueurs max = **8** (une base par joueur).
6. *Play*. Dans la fenêtre Output, tu dois voir :

```
MapService: aligned Workspace.<nom du modèle> (moved ... studs, scale x1.000, residual 0.000)
MapService: 1 map model(s), 642 colliders, 8 spawns, 8 portals
```

Variante : importer les `sections/*.glb` une par une au lieu de la map entière
(utile pour itérer sur une seule zone). Chaque section embarque les repères
d'alignement et se recale indépendamment. N'importe pas les deux à la fois,
tu aurais la map en double.

---

## 4. Ce qui la rend jouable (le contrat Blender ↔ Roblox)

Un GLB importé tel quel n'est **pas** jouable : couleurs incertaines, collisions
approximatives sur les gros maillages, rien pour spawn ni se téléporter. Le
script Blender et `MapService` sont écrits l'un pour l'autre :

| Problème | Côté Blender | Côté Roblox (`src/Server/MapService.lua`) |
|---|---|---|
| Couleurs et matières | **1 matière par objet**, nom `<Nom>__<clé>` (ex. `Zone2_Lave__lava_glow`) | lit la clé, applique couleur + matière Roblox depuis `MapData.materials` (**Neon** pour tout ce qui brille) |
| Collisions | liste chaque mur, sol, prop solide → `MapColliders.lua` | crée 642 parts invisibles exactes ; les meshes deviennent de purs visuels (groupe de collision `MapVisual`) mais la caméra les évite toujours |
| Position à l'import | 3 repères `REF_Origin`, `REF_AxisX`, `REF_AxisY` enfouis sous l'île | mesure les repères, corrige échelle, rotation et position, puis rend les repères invisibles |
| Spawn | 8 pads autour de la fontaine → `MapData.lobby.spawns` | 8 `SpawnLocation` invisibles, orientées vers les portails |
| Portails | déclencheurs → `MapData.portals` | téléporte au contact : zone → début de la zone, MA BASE → sa base, LOBBY → un spawn du lobby |
| Baseplate du modèle Studio | — | supprimée (elle z-fighterait avec le sol à Y = 0) |

Autres services branchés sur la map :

- **`PlotService`** attribue une base à chaque joueur (dans l'ordre N1, S1, N2,
  S2… : les premières bases sont les plus proches du lobby), affiche
  « Base de *Pseudo* » au-dessus de la machine, libère la base au départ.
  Attribut joueur `PlotId`.
- **`CapsuleService`** fait apparaître les capsules dans la voie de course de
  chaque zone (`MapData.zones[i].capsuleArea`), jamais dans un mur. Chaque
  capsule porte l'attribut `ZoneIndex` (1 → 5), prêt pour une rareté qui monte
  avec la zone.
- **`ZoneBanner`** (client) affiche le nom de la zone, dans sa couleur, quand le
  joueur y entre.

---

## 5. Modifier la map

Tout se règle en haut de `build_map.py` :

| Tu veux… | Modifie |
|---|---|
| changer une taille (rue, bases, murs, lobby, pont) | `CONFIG` |
| changer une zone (sol, murs, couleur de lueur, quantité de décor) | son entrée dans `BIOMES` |
| changer une couleur ou une matière Roblox | `PALETTE` (clé `rbx` pour la matière Roblox) |
| ajouter un prop | une fonction `add_*` ; `solid=True` pour qu'il bloque les joueurs |

Puis : relance le script → supprime l'ancienne map dans Studio → réimporte le
GLB. `MapData.lua` et `MapColliders.lua` suivent automatiquement (Rojo les
synchronise).

⚠️ `plots_per_side` doit rester égal à `len(BIOMES) - 1` : chaque zone sauf le
désert contient une cellule de 2 bases.

---

## 6. Ce qui a été vérifié (26/09/2026)

Vérifié par mesure, sur Blender 5.0.1 (module `bpy`) :

- génération complète sans erreur, **373/373 contrôles** passés ;
- GLB réimporté dans une scène vide : 303 pièces, 133 meshes (les 8 bases
  partagent les leurs), **aucune** pièce multi-matière, 2,3 Mo ;
- les 3 repères tombent **exactement** sur les coordonnées de `MapData.reference` ;
  le portail MA BASE et les machines des bases N1 et S3 tombent sur leurs
  ancres `MapData` ;
- les 16 fichiers Luau compilent (compilateur Luau réel) ;
- `MapData.lua` et `MapColliders.lua` exécutés dans une VM Luau avec des tests :
  chaque nom du GLB trouve sa couleur, chaque spawn est dans la bonne zone,
  chaque portail a une destination, zones contiguës ; `PlotService` testé
  (8 bases attribuées dans l'ordre, 9e joueur sans base, libération et
  réattribution).

**Pas vérifié** : l'exécution dans Roblox Studio lui-même (pas de Studio dans
cet environnement). Le comportement exact du 3D Importer (noms des pièces,
matières créées, ancrage) est anticipé, pas mesuré : `MapService` est écrit
pour s'adapter (il avertit s'il trouve une pièce sans clé de matière). À la
première importation, vérifie les deux lignes Output du §3.

Les aperçus du dépôt ont été rendus avec Cycles (pas de GPU ici) ; chez toi le
script rend avec EEVEE.

---

## 7. Reste à faire

- **Vol physique** : `ProximityPrompt` sur `plot.house` au lieu de la liste
  d'UI (`MapData.plots[i].house` est prêt).
- Afficher les kaijus sur les socles des enclos (`MapData.plots[i].pens`).
- Brancher un vrai classement sur `MapData.lobby.leaderboard` (position,
  taille, orientation de l'écran fournies).
- `StreamingEnabled` à activer dans Studio (propriété de `Workspace`).
