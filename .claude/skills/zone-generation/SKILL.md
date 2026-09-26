---
name: zone-generation
description: Méthode pour générer des zones de couloir Roblox (map quasi infinie) via un MCP de génération 3D. À utiliser pour créer chaque zone de la map comme un modèle 3D distinct, avec une richesse croissante.
---

# Génération de zones de couloir (map quasi infinie)

## ⚠️ Sur CE projet, les zones sont déjà faites — et autrement

Le couloir de Kaiju Heist traverse 5 biomes (Verte → Lave → Glace → Pierre →
Désert) **générés procéduralement** par `KaijuHeist/blender/build_map.py`
(liste `BIOMES`). Voir `ZONES.md`.

N'applique pas la méthode ci-dessous au couloir. Raison : des segments qui
doivent se raccorder au stud près ne peuvent pas sortir d'un générateur 3D par
IA, qui produit une géométrie différente à chaque appel — deux zones générées
séparément ne se raccorderaient jamais. Pour modifier une zone, édite `BIOMES`
et relance le script.

**Ce skill reste utile pour** : un objet organique unique posé *dans* une zone
(créature, statue, épave, décor sculpté), et pour tout autre projet où la map
n'est pas procédurale. Lis la suite dans ce cadre.

## Concept

La map est un **couloir quasi infini** composé de **zones qui se suivent** le long
d'un axe (ex. Zone Verte → Zone de Lave → Zone de Glace → …).

## ⚠️ RÈGLE FONDAMENTALE : une zone = un modèle 3D distinct

- **Chaque zone est générée comme un modèle 3D SÉPARÉ et INDÉPENDANT** (un FBX/OBJ par zone).
- **Ne fusionne JAMAIS plusieurs zones dans un seul modèle.** Un MCP de génération
  3D gère mal une map entière d'un coup : il faut découper en modèles distincts.
- Pour N zones, tu génères **N modèles 3D distincts**, un par zone.
- Chaque modèle est ensuite importé **séparément** dans Roblox Studio, puis aligné
  bout à bout le long de l'axe Z.

## Spécification d'une zone (standard)

- **Dimensions** : 25 studs de long (sens de progression) × 40 studs de large × 15 studs de haut.
- **Structure** : sol + 2 murs latéraux + plafond optionnel.
- **Sens de progression** : le long de l'axe Z.
- **Contraintes Roblox** : low-poly (< 2000 triangles/objet), échelle 1 stud = 1 unité, FBX/OBJ, textures ≤ 1024×1024.

## Principe de progression (richesse croissante)

- **Zones de départ** : basiques (peu de décor, couleurs simples).
- **Zones avancées** : plus riches (plus d'objets, mécaniques visuelles, effets).
- Plus on avance dans le couloir, plus la zone est riche en contenu.

## Méthode de génération (batch de zones)

1. **Définir la liste des zones** (thème + ordre), ex. : Verte → Lave → Glace → Désert → Pierre.
2. **Pour CHAQUE zone**, écrire un prompt de génération **séparé** (dimensions, sol, murs, plafond, décor, style, contraintes).
3. **Générer CHAQUE zone comme un modèle 3D distinct** via le MCP (voir skill `higgsfield-3d-assets`). Un appel MCP = un modèle = une zone.
4. **Importer CHAQUE modèle séparément** dans Roblox Studio.
5. **Aligner** les modèles bout à bout le long de l'axe Z (chaque zone = 25 studs de long).
6. **Vérifier** le raccord entre zones (largeur identique 40 studs, murs alignés).

## Template de prompt (un par zone, à adapter)

```
Génère un modèle 3D distinct de segment de couloir Roblox "Zone [THÈME]", [basique/riche] :

- Dimensions : 25 studs de long × 40 studs de large × 15 studs de haut.
- Sol : [matériau + couleur hex].
- Murs latéraux : [matériau + couleur hex], hauteur 15 studs.
- Plafond : [ouvert / rocheux / …].
- Éléments de décor ([simples/riches]) :
  - [liste des objets avec forme + couleur].
- Style : low-poly cartoon, ambiance [chaud/froid/sombre/…].
- Export : FBX ou OBJ, low-poly (< 2000 triangles par objet).
- IMPORTANT : ceci est UN SEUL modèle 3D indépendant (une seule zone).
```

## Règles

- **Une zone = un modèle 3D distinct = un appel MCP.** Ne génère jamais la map entière d'un coup.
- **Richesse croissante** : les premières zones sont simples, les suivantes plus détaillées.
- **Cohérence** : toutes les zones ont la même largeur (40 studs) et hauteur (15 studs) pour se raccorder.
- **Thèmes variés** : alterne les ambiances (chaud/froid/nature/urbain) pour la variété.
- **Nommage** : nomme chaque modèle clairement (`ZoneVerte.fbx`, `ZoneLave.fbx`, …) pour l'import.
