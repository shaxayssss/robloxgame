---
name: higgsfield-3d-assets
description: Génération de modèles 3D compatibles Roblox via n'importe quel MCP de génération 3D (Higgsfield ou autre). À utiliser pour créer des assets 3D (meshes, modèles, objets) à partir d'une spécification, un modèle distinct par asset.
---

# Génération d'assets 3D via un MCP (générique)

## Contexte

Un outil de génération 3D (ex. Higgsfield) est relié à Claude Code via un
**MCP** (Model Context Protocol). Ce skill décrit une **méthode universelle**
pour produire des **assets compatibles Roblox Studio**, quel que soit le nom
exact des outils MCP disponibles.

## ⚠️ RÈGLE FONDAMENTALE : un asset = un modèle 3D distinct

- **Chaque asset (objet, zone, structure) est généré comme un modèle 3D SÉPARÉ**
  (un FBX/OBJ par asset).
- **Ne fusionne jamais plusieurs assets dans un seul modèle.** Les MCP de
  génération 3D produisent de meilleurs résultats sur des objets **uniques et
  ciblés** que sur des scènes complexes.
- Pour N assets, tu génères **N modèles 3D distincts**, un par asset.
- Chaque modèle est importé **séparément** dans Roblox Studio.

## 0. Ce skill est-il le bon ?

Pour une **map**, un **terrain** ou toute géométrie répétée (sols, murs,
clôtures, bâtiments simples, segments de couloir), n'utilise pas ce skill :
passe par le script Blender procédural `KaijuHeist/blender/build_map.py`
(voir `CLAUDE.md`). Raison : des segments qui doivent se raccorder au stud près
ne peuvent pas sortir d'un générateur 3D par IA, qui produit une géométrie
différente à chaque appel.

Ce skill sert aux objets **organiques et uniques** qu'un script rendrait mal :
créatures, kaijus, statues, props sculptés.

## 1. Découvrir les outils MCP disponibles (dynamique)

Ne suppose **jamais** le nom des outils : cherche-les dans les outils dont tu
disposes réellement à cet instant. Un subagent **ne peut pas** taper de commande
slash comme `/mcp` — cette voie n'existe que pour l'utilisateur humain.

Repère les outils pertinents par leur **description**, pas par leur nom : cherche
ceux qui mentionnent génération 3D, mesh, text-to-3D, image-to-3D, GLB, FBX, OBJ.
Si ton environnement expose un outil de recherche d'outils, utilise-le avec des
mots-clés comme « 3d », « mesh », « model ».

Si aucun outil de génération 3D n'est disponible, **dis-le** au lieu d'inventer
un appel : propose la voie Blender procédural à la place.

## 2. Workflow complet

```
Screenshot → analyse (skill map-reference-analysis)
          → spécification de map + fiches assets
          → génération 3D via le MCP (ce skill), un modèle par asset
          → import dans Roblox Studio (FBX/OBJ)
          → intégration par l'agent map/art
```

## 3. Préparer le prompt de génération 3D (universel)

Pour **chaque** asset de la spec, construis un prompt de génération **précis et
séparé** qui reprend fidèlement la fiche asset. Ce prompt fonctionne quel que
soit l'outil :

```
Génère un modèle 3D distinct low-poly de [objet] :
- Dimensions : X × Y × Z (en studs Roblox, 1 stud = 1 unité)
- Style : low-poly / cartoon / réaliste
- Matériau : Plastic / Metal / Wood / Neon / Glass
- Couleur : #RRGGBB (fidèle au screenshot de référence)
- Géométrie : < 2000 triangles
- Export : FBX ou OBJ
- IMPORTANT : ceci est UN SEUL modèle 3D indépendant (un seul objet).
```

Adapte ce prompt au format attendu par l'outil MCP identifié à l'étape 1
(texte, image de référence, ou paramètres structurés).

## 4. Exigences de compatibilité Roblox (à imposer à chaque génération)

Ces contraintes sont **indépendantes de l'outil** et doivent toujours être
respectées :

- **Échelle** : 1 stud = 1 unité ≈ 1 mètre. Vérifier la taille après import.
- **Low-poly** : limiter les triangles (< 2000 par objet) pour la performance mobile.
- **Format** : FBX ou OBJ (importables dans Roblox Studio).
- **Textures PBR** : ColorMap, NormalMap, MetalnessMap, RoughnessMap si réaliste.
- **Résolution textures** : max 1024×1024 (performance).
- **Couleurs** : EXACTEMENT fidèles au screenshot de référence.
- **Topologie propre** : pas de géométrie cassée, normales correctes.

## 5. Après génération : contrôle qualité (universel)

- [ ] Le modèle correspond à la fiche asset (forme, couleur, dimensions).
- [ ] Le polycount est raisonnable (< 2000 triangles).
- [ ] Le format est importable (FBX/OBJ).
- [ ] L'échelle est correcte après import (1 stud = 1 unité).
- [ ] Les textures sont légères (≤ 1024×1024).

Si un critère échoue, **régénère** en ajustant le prompt (ex. « réduire le nombre
de triangles », « corriger l'échelle ») jusqu'à obtenir un résultat conforme.

## 6. Import dans Roblox Studio

1. Dans Studio : **Avatar Importer** ou **Import 3D** (menu Fichier → Importer).
2. Sélectionner le FBX/OBJ généré.
3. Vérifier l'échelle et ajuster si nécessaire.
4. Convertir en `MeshPart` et appliquer le matériau/couleur.
5. Placer dans la map (coordonne-toi avec l'agent `map`).

## Frontières

- ❌ Ne génère pas d'assets sans une fiche asset précise (issue de l'analyse).
- ❌ Ne fusionne pas plusieurs assets dans un seul modèle.
- ✅ Tu transformes une spec en modèles 3D importables (un par asset), puis tu les intègres.
- ✅ Tu t'adaptes à n'importe quel outil MCP de génération 3D disponible.
