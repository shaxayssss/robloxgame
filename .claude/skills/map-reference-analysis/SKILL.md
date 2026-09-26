---
name: map-reference-analysis
description: Méthode pour analyser des screenshots de référence et en tirer une spécification de map fidèle + des assets compatibles Roblox. À utiliser dès qu'on fournit des images de map à reproduire.
---

# Analyse de map à partir de screenshots

## Objectif

Quand on te fournit un ou plusieurs **screenshots** d'une map à reproduire, tu
dois en extraire une **spécification fidèle** et des **assets compatibles
Roblox**, sans rien inventer. Tu travailles main dans la main avec le skill
`higgsfield-3d-assets` pour générer les modèles 3D via le MCP Higgsfield.

## ⚠️ Règle absolue

> Tu ne décris **QUE** ce qui est visible dans l'image. Si un élément n'est pas
> visible ou est flou, écris « NON VISIBLE ». Ne complète jamais par déduction.
> Ne réinvente jamais la map : reproduis ce que le screenshot montre.

## Méthode en 5 étapes

### 1. Description littérale (avant toute interprétation)
- Point de vue de la caméra (dessus, face, hauteur, angle).
- Disposition générale (ligne droite, couloir, zone ouverte, multi-niveaux).
- Couleurs dominantes (ciel, sol, murs, objets).
- Chaque élément distinct avec sa position (gauche/centre/droite, avant/arrière-plan).

### 2. Extraction structurée
- **Layout** : ligne droite / couloir / boucle / multi-niveaux ? Direction du déplacement ?
- **Zones** (dans l'ordre de parcours) : nom, position, contenu, proportions relatives.
- **Objets** : forme, couleur, matériau apparent, taille relative au personnage.
- **Ambiance** : éclairage (jour/nuit/néon), style (low-poly/cartoon/réaliste), palette.

### 3. Spécification de map (format structuré)

```
### MAP
- Type de layout : …
- Direction : …
- Longueur estimée : … studs (1 stud ≈ 1 m) ou « très longue / quasi infinie »
- Largeur estimée : … studs

### ZONES (dans l'ordre)
| # | Nom | Position | Dimensions (studs) | Contenu |

### OBJETS / STRUCTURES
| Objet | Zone | Forme | Couleur/Matériau | Taille (studs) |

### AMBIANCE
- Éclairage / Style / Palette
```

### 4. Choisir la voie de production

Une fois la spec écrite, **tranche entre les deux voies** avant de produire quoi
que ce soit :

| La spec décrit… | Voie | Sortie |
|---|---|---|
| Des formes géométriques répétées (sols, murs, clôtures, bâtiments simples, layout) | **Blender procédural** — `KaijuHeist/blender/build_map.py` | `.glb` |
| Des formes organiques uniques (créatures, statues, props sculptés) | **MCP 3D** — skill `higgsfield-3d-assets` | `.fbx` / `.obj` |

En pratique une map entière relève de la première voie : c'est du paramétrage
(nombre de plots, pas de grille, épaisseur des murs), pas de la modélisation.
Ne pars sur la génération MCP que pour les objets qu'un script rendrait mal.

Pour chaque objet, produis une fiche asset : type (MeshPart / Part / Model),
dimensions en studs, matériau Roblox, couleur hex.
**Limite dure : 10 000 triangles par MeshPart.**

### 5. Vérification de fidélité
- [ ] Chaque zone est réellement visible dans le screenshot.
- [ ] Aucun élément inventé.
- [ ] Proportions et couleurs fidèles.
- [ ] Éléments incertains marqués « À CONFIRMER ».

## Règles assets Roblox (impératives)

- Échelle : 1 stud = 1 unité ≈ 1 mètre.
- Low-poly pour la performance mobile.
- Textures PBR si réaliste, max 1024×1024.
- Couleurs EXACTEMENT fidèles au screenshot.

## Exemple réel : la map Kaiju Heist

Spec extraite des screenshots de référence au début du projet (historique :
la map actuelle suit depuis un plan en T dessiné par l'utilisateur, voir
`MAPS.md`). Les dimensions ci-dessous étaient celles du `CONFIG` de
l'époque ; la source de vérité reste le script.

```
### MAP
- Type de layout : île flottante rectangulaire, rue centrale axiale
- Direction : plaza de spawn à une extrémité → désert/boss à l'autre
- Dimensions : ~950 × 430 studs
- Largeur de la rue centrale : 72 studs

### ZONES
| # | Nom | Position | Dimensions | Contenu |
|---|---|---|---|---|
| 1 | Plaza de spawn | extrémité -X | 140 × 140 | fontaine, arche, podium de classement |
| 2 | Rue centrale | axe médian | ~590 × 72 | herbe damier, lampadaires, déco de bord |
| 3 | Plots joueurs | 4 de chaque côté de la rue | 132 × 122 chacun | enclos, stands, machine |
| 4 | Murs séparateurs | entre plots | 16 × 122 × 40 | terre damier, sommet herbeux |
| 5 | Zone désert | extrémité +X | 215 × 430 | dunes, cactus, autel de boss |

### OBJETS (par plot)
| Objet | Forme | Couleur | Taille |
|---|---|---|---|
| Enclos ×6 | clôture bois + socle pierre | bois clair / gris | 30 × 32 |
| Maison | cube + toit à deux pans | beige + toit terracotta | 18 × 16 × 16 |
| Stand VENDRE | comptoir + auvent rayé | rouge/blanc | 18 × 9 × 16 |
| Stand BOUTIQUE | comptoir + auvent rayé | jaune/blanc | 18 × 9 × 16 |
| Machine à éclore | bloc métal + panneaux | sombre + vert émissif | 16 × 13 × 16 |
| Ligne ZONE SÛRE | bande au sol + texte | rouge / blanc | largeur du plot |

### AMBIANCE
- Éclairage : nuit claire, ciel bleu dégradé étoilé
- Style : low-poly blocky saturé (Roblox), sols et murs en damier deux tons
```

### Ce que cet exemple montre

- Les **dimensions sont chiffrées en studs**, pas décrites en mots.
- Les **motifs répétés** (plots, enclos) sont décrits une fois + un compte, ce
  qui se traduit directement en boucle dans le script de génération.
- Une map de cette taille se **génère par script**, elle ne se modélise pas à la
  main : la spec doit donc sortir des paramètres (nombre de plots, pas de la
  grille, épaisseur des murs), pas une liste d'objets individuels.

## Conseils de fiabilité

- Demander des screenshots **nets** (pas flous, pas trop zoomés).
- Demander **plusieurs angles** si possible (vue de dessus + vue de face).
- Si l'image est ambiguë, **demander une précision** plutôt que d'inventer.
