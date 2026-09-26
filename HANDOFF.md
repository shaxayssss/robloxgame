# 🧠 HANDOFF — Mémoire du projet Kaiju Heist

> **À lire en premier dans une nouvelle conversation.** `CLAUDE.md` décrit l'état
> du projet ; ce document-ci explique **pourquoi** il est dans cet état. Il
> contient les décisions prises, ce qui a été essayé et a échoué, et les pièges
> déjà rencontrés. Sans lui, une nouvelle session refera les mêmes erreurs.

---

## 1. D'où vient le projet

Point de départ : une analyse de **Steal An Egg** (Roblox, ~11-14 M joueurs
simultanés) et la question « comment ce jeu fait autant de joueurs ».

La demande initiale était de scraper Roblox pour en extraire les assets. **Ça a
été refusé** — extraire les scripts, modèles et données propriétaires d'un studio
tiers pose un problème de propriété intellectuelle. À la place, on a repris la
**formule de game design** (qui n'est pas protégeable) et construit un jeu
original dessus.

La formule retenue, commune à Steal a Brainrot / Pet Simulator / Steal An Egg :

1. Boucle lisible en 5 secondes
2. PvP asymétrique léger (le vol entre joueurs crée l'imprévu, pas un script)
3. Rareté et collection
4. Sessions courtes (~15 min)
5. Progression méta persistante

Le thème **« Capsules → Kaijus »** a été choisi par l'utilisateur parmi trois
propositions (les deux autres : cristaux/golems, coffres/esprits).

---

## 2. Décisions structurantes (ne pas re-litiger sans raison)

### La map est procédurale, pas modélisée ni générée par IA

`blender/build_map.py` est la **source unique** de la map. Le `.blend` est une
sortie, pas une source : il est écrasé à chaque exécution.

**Pourquoi pas un générateur 3D par IA :** des segments qui doivent se raccorder
au stud près ne peuvent pas en sortir — il produit une géométrie différente à
chaque appel. Ce n'est pas une opinion, ça a été testé (voir §3).

### Code en anglais, documentation en français

Décidé explicitement par l'utilisateur. Les commentaires de `build_map.py` ont
été traduits FR → EN en conséquence. Les `.md` restent en français.

### Les plots restent verts dans tous les biomes

Le couloir traverse 5 biomes, mais les plots des joueurs gardent leur herbe
verte. Raison : un joueur doit reconnaître une base d'un coup d'œil. Les teinter
rendrait la map illisible.

### Deux productions de zones coexistent, et c'est voulu

- `build_map.py` peint les 5 biomes en bandes dans l'île principale → c'est la
  map que le jeu utilise.
- `build_zones.py` produit les 5 mêmes zones en **modèles autonomes** de
  40 × 25 studs (format demandé par le kit), raccordables, un GLB chacun.

Ne supprime pas l'un en croyant qu'il double l'autre.

---

## 3. Ce qui a été essayé et n'a pas marché

### Génération des zones par MCP 3D — abandonné après test

Test réel du 26/09/2026, `tripo_3d`, 5 crédits dépensés. Prompt décrivant
explicitement sol, murs latéraux, arbres et rochers.

| Attendu | Obtenu |
|---|---|
| Sol plat + 2 murs latéraux | **aucun des deux** |
| Segment 25 × 40 × 15 studs | 1.0 × 0.74 × 0.31 (unités normalisées) |
| < 2000 triangles | 1946 ✅ |

Résultat : **4 arbres et 3 rochers flottants**, sans structure. Ces modèles
reconstruisent *un objet cohérent unique*, pas une scène architecturée : ils se
sont accrochés aux props énumérables et ont ignoré l'architecture.

**Conclusion :** le budget MCP va aux **kaijus** (objet organique unique = ce que
ces modèles savent faire), pas aux zones. Le GLB raté est conservé dans
`assets/zones/` — les arbres et rochers sont récupérables comme props.

Contraintes découvertes au passage, valables pour tout usage futur du MCP :
- La sortie est du **GLB**, jamais du FBX/OBJ (sans gravité, Roblox lit le GLB).
- **Aucun modèle n'accepte de dimensions.** Tout sort à échelle arbitraire.
- Coûts constatés : `tripo_3d` 5 crédits, `hunyuan3d_v3_1` 7, `meshy_v6` 25.

---

## 4. Pièges techniques déjà rencontrés (ils coûtent cher à re-découvrir)

### Blender est en FRANÇAIS sur cette machine

Le nœud Principled s'appelle `BSDF guidée`, et **les noms de sockets sont
traduits aussi**. Conséquence, dans tout script Blender :

- accéder aux nœuds par **type** (`node.type == "BSDF_PRINCIPLED"`),
- accéder aux sockets par **identifier**, jamais par nom.

`build_map.py` a des helpers `find_node()` / `find_socket()` pour ça. Un script
écrit avec `nodes.get("Principled BSDF")` plantera.

### `read_factory_settings()` casse le contexte dans l'UI

Lancé depuis l'éditeur de texte de Blender, il invalide le contexte du script en
cours et l'export glTF échoue ensuite sur `bpy.context.active_object`. La scène
est donc vidée **manuellement** (`reset_scene()`), sans rechargement.

Effet de bord historique : `read_factory_settings` remettait aussi l'interface en
anglais, ce qui masquait le problème de langue ci-dessus.

### Conversion d'axes Blender → Roblox

Blender est Z-up, Roblox/glTF est Y-up. Avec `export_yup=True` :

```
Blender (x, y, z) → Roblox (x, z, -y)
```

Deux conséquences qui ont déjà produit des bugs :
1. Toute ancre exportée doit passer par `to_roblox()`, sinon elle atterrit
   ailleurs que le mesh auquel elle appartient.
2. **La conversion retourne l'axe Y**, donc une paire de coins n'est plus triée
   après conversion. Les `bounds` doivent être re-triés composante par
   composante (`_bounds()`), sinon tout test d'appartenance échoue en silence.

### Limite Roblox : 10 000 triangles par MeshPart

`build_map.py` affiche `MESH_BUDGET` à chaque exécution et signale tout objet
au-dessus. État actuel : 38 objets, ~92 600 triangles, max ~7 300.

### `ensure_active_object()` et les entrées nulles

Juste après une reconstruction de scène, `view_layer.objects` peut renvoyer des
entrées `None`. Le helper itère donc `bpy.data.objects` et utilise l'échec de
`select_set()` comme test d'appartenance au view layer.

---

## 5. Le kit « studio-agents-roblox »

Un kit d'agents et de skills a été fourni en deux versions (v1 puis v2 en zip).

**Il est générique et ne connaît pas le projet.** Chaque version réécrit les
agents et `CLAUDE.md` dans leur état d'origine. **Ne jamais l'extraire par-dessus
le projet** : ça efface tout le travail d'adaptation. La méthode correcte est un
merge — prendre le nouveau contenu, préserver ce qui est spécifique au projet.

Défauts corrigés dans le kit, à re-vérifier si une v3 arrive :

| Défaut | Correction |
|---|---|
| `.claude/config.json` inerte (Claude Code lit `settings.json`) | supprimé |
| Agent `lead` déclarait l'outil `Task`, pas `Agent` → ne pouvait pas déléguer | corrigé |
| `CLAUDE.md` générique, « type de jeu : à définir » | réécrit sur le projet réel |
| Pipeline d'assets imposant Higgsfield/FBX | remplacé par Blender/GLB |
| Exemple de spec map inventé dans `map-reference-analysis` | remplacé par la vraie spec |
| Skill demandant à un subagent de taper `/mcp` (impossible) | reformulé |
| Arborescence de dossiers contredisant le Rojo réel | alignée |
| Faute « non-bloante » | corrigée (revient à chaque version du kit) |

Les 14 agents ont reçu un bloc **« Contexte projet — Kaiju Heist »** qui les rend
conscients des fichiers réels de leur domaine.

⚠️ **L'agent `map` n'a aucun outil MCP** dans son frontmatter (`Read, Write,
Edit, Glob, Grep, Bash`). Lui demander de générer des assets 3D échouera tant
qu'on ne lui ajoute pas l'accès.

---

## 6. Où en est le projet

**Les systèmes et la map existent, mais ne se parlent pas encore.** Aucun service
ne lit `MapData.lua`. C'est LA priorité.

| # | Tâche | Dépend de |
|---|---|---|
| 1 | `PlotService` : assigner un des 8 plots par joueur, spawn sur `plot.spawn` | — |
| 2 | `CapsuleService` : spawn dans `MapData.capsuleZone` au lieu de l'origine | 1 |
| 3 | Vol par `ProximityPrompt` sur `plot.house` au lieu de la liste d'UI | 1 |

### Dettes connues

- Aucun test automatisé.
- **`PlayerDataService` n'a ni `version` ni migration** — le premier changement de
  schéma cassera les sauvegardes existantes.
- **`Load()` retombe sur un profil vide si le DataStore échoue**, donc un incident
  réseau peut faire écraser une vraie sauvegarde au prochain autosave. À traiter
  avant toute sortie publique.
- **Aucun anti-spam sur les remotes** — un client peut marteler `RequestHatch`.
- `StreamingEnabled`, `CanCollide`/`CanQuery` et les tags `CollectionService`
  restent à régler dans Studio après import.

---

## 7. Comment reprendre

```bash
# Régénérer la map (île + biomes + MapData.lua)
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python "KaijuHeist/blender/build_map.py"

# Régénérer les 5 zones autonomes
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python "KaijuHeist/blender/build_zones.py"

# Synchroniser le code vers Roblox Studio
cd KaijuHeist && rojo serve
```

**Fichiers générés — ne jamais éditer à la main :**
`KaijuHeist/src/Shared/MapData.lua`, `assets/map/*.blend`, `assets/map/*.glb`,
`assets/zones/*.glb`.

Crédits MCP restants au moment de l'export : **5**.
