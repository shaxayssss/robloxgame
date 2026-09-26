# 🗺️ ZONES — Les biomes du couloir

> **État : implémenté.** Les 5 zones décrites ici existent dans la map et sont
> exposées au gameplay via `MapData.zones`. Ce document décrit ce qui *est*,
> pas une intention.

---

## 1. Le principe

Le couloir central traverse **5 biomes** qui se suivent, du spawn vers le boss.
Plus le joueur s'éloigne du spawn, plus la zone est hostile — c'est l'axe de
progression du jeu.

```
Plaza de spawn → Verte → Lave → Glace → Pierre → Désert (autel du boss)
```

**Les plots restent en herbe verte dans tous les biomes.** C'est délibéré : un
joueur doit reconnaître une base d'un coup d'œil. Seuls le sol du couloir, les
murs séparateurs, le liseré de l'île et le décor changent de thème.

---

## 2. Comment c'est produit (⚠️ lis ça avant de toucher à quoi que ce soit)

Les zones sont **générées procéduralement** par `KaijuHeist/blender/build_map.py`,
dans la liste `BIOMES` en haut du fichier. Elles ne sont **pas** générées par un
MCP 3D, et c'est une décision technique, pas une préférence :

> Des segments qui doivent se raccorder **au stud près** ne peuvent pas sortir
> d'un générateur 3D par IA, qui produit une géométrie différente à chaque appel.
> Deux zones générées séparément ne se raccorderaient jamais proprement.

Pour modifier une zone : édite son entrée dans `BIOMES`, relance le script.

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python "KaijuHeist/blender/build_map.py"
```

Le skill `zone-generation` (génération d'une zone comme modèle 3D distinct via
MCP) ne s'applique **pas** au couloir. Il reste valable pour des objets
organiques uniques posés *dans* une zone (créature, statue, épave).

### Test effectué (26/09/2026) — ne pas refaire

La Zone Verte a été générée via le MCP (`tripo_3d`, text-to-3D, 5 crédits) avec
un prompt décrivant sol, murs latéraux, arbres et rochers. Résultat mesuré :

| Attendu | Obtenu |
|---|---|
| Sol plat + 2 murs latéraux | **aucun des deux** |
| Segment 25 × 40 × 15 studs | 1.0 × 0.74 × 0.31 (unités normalisées) |
| < 2000 triangles | 1946 ✅ |

Le modèle a produit **4 arbres et 3 rochers flottants**, sans structure. C'est le
comportement normal de ces générateurs : ils reconstruisent **un objet cohérent
unique**, pas une scène architecturée. Ils se sont accrochés aux éléments
énumérables du prompt (les props) et ont ignoré le sol et les murs.

Conclusion : le budget MCP de ce projet doit aller aux **kaijus** (objet
organique unique = exactement ce que ces modèles savent faire), pas aux zones.
Le fichier produit est conservé dans `assets/zones/` : les arbres et rochers
sont récupérables comme props isolés.

---

## 2 bis. Les 5 zones en modèles séparés

En plus des bandes peintes dans la map principale, les 5 zones existent comme
**modèles autonomes**, un GLB chacun, au format du kit (40 × 25 studs au sol,
murs de 15 de haut). Script : `KaijuHeist/blender/build_zones.py`.

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python "KaijuHeist/blender/build_zones.py"
```

Sortie dans `assets/zones/` : `ZoneVerte.glb`, `ZoneLave.glb`, `ZoneGlace.glb`,
`ZoneDesert.glb`, `ZonePierre.glb`, plus un aperçu par zone et `zones_chained.png`
qui montre les 5 raccordées.

| Zone | Dimensions (X × Y × Z) | Triangles |
|---|---|---|
| ZoneVerte | 40 × 16 × 25 | 588 |
| ZoneLave | 40 × 16 × 25 | 504 |
| ZoneGlace | 40 × 16 × 25 | 496 |
| ZoneDesert | 40 × 16 × 25 | 516 |
| ZonePierre | 40 × 16 × 25 | 520 |

Les 16 de hauteur = 15 de mur + 1 de dalle sous le sol praticable, dont la
surface est à Y = 0.

**Ils se raccordent bout à bout**, et c'est garanti par construction, pas par
chance : la section des murs est uniforme sur toute la longueur, et aucun prop
ne franchit les plans d'extrémité (`PROP_MARGIN` dans le script). Pose-les à
Z = 25 × n, ils s'emboîtent au stud près.

⚠️ Si tu ajoutes du décor, garde-le entre `PROP_MARGIN` et `LENGTH -
PROP_MARGIN`. Un prop qui dépasse d'un bout casse le raccordement de **toute**
la chaîne.

Les coulées de lave traversent volontairement toute la largeur et touchent donc
les murs latéraux : ça ne gêne pas le raccordement, qui ne dépend que des
extrémités.

## 3. Les 5 zones

Chaque bande couvre toute la largeur de l'île (430 studs) sur une longueur de
**148 studs** (une cellule de plot), sauf la première (288 studs, elle absorbe
la plaza de spawn) et le désert (203 studs).

| # | Zone | Sol | Murs | Liseré | Décor |
|---|---|---|---|---|---|
| 1 | **Zone Verte** | herbe `#33A81C` / `#59D933` | terre `#9E6E40` | vert vif | arbres, buissons, rochers |
| 2 | **Zone de Lave** | roche sombre `#3D2624` | volcanique `#332B2B` | lave émissive `#FF5722` | obsidienne, fissures de lave |
| 3 | **Zone de Glace** | glace `#82D4FA` | neige `#E3F2FD` | cristal émissif | pics de glace, congères |
| 4 | **Zone de Pierre** | pierre `#757575` | roche `#424242` | pierre claire | stalagmites, rochers |
| 5 | **Zone Désert** | sable `#E6C778` | sable sombre | sable | cactus, rochers, dunes |

Le liseré de lave et celui de glace sont **émissifs** : l'arête de l'île rougeoie
dans la zone volcanique et brille dans la zone glaciaire. C'est ce qui rend la
progression lisible de loin, y compris en vue aérienne.

---

## 4. Côté gameplay

`src/Shared/MapData.lua` (généré) expose :

```lua
MapData.zones               -- 5 entrées, contiguës, sans trou
-- { id = "lava", label = "Zone de Lave", index = 2,
--   bounds = { min = Vector3, max = Vector3 } }

MapData.GetZoneAt(position) -- renvoie la zone contenant une position
```

`index` croît avec la distance au spawn : il sert directement de **palier de
difficulté ou de récompense**. Exemples d'usages prévus :

- faire varier la rareté des capsules selon `zone.index` ;
- n'autoriser certains kaijus qu'à partir d'une zone donnée ;
- afficher le nom de la zone quand le joueur en change.

⚠️ Les zones sont **contiguës et sans trou** : `GetZoneAt` ne renvoie `nil` que
hors de l'île. Si tu modifies `BIOMES` ou le nombre de plots, vérifie que c'est
toujours vrai.

---

## 5. Ajouter une zone

1. Ajoute une entrée dans `BIOMES` (`build_map.py`), avec ses clés `floor`,
   `wall`, `cap`, `rim`, `decor`.
2. Si le décor est d'un type nouveau, ajoute un `add_*` et branche-le dans
   `add_biome_decor()`.
3. Augmente `CONFIG["plots_per_side"]` si tu veux une cellule de plus — sinon la
   nouvelle zone ne sera pas affichée, seules les `plots_per_side` premières le
   sont (plus le désert, toujours en dernier).
4. Relance le script et vérifie la ligne `MESH_BUDGET` : la limite Roblox est de
   **10 000 triangles par MeshPart**.
