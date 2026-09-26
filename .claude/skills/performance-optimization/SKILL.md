---
name: performance-optimization
description: Techniques d'optimisation Roblox : FPS, mémoire, streaming, LOD, profilage, micro-optimisations. À consulter pour optimiser ou diagnostiquer des lags.
---

# Optimisation performance Roblox

## Cibles (jeu +1M joueurs)

- **60 FPS** stable sur mobile bas de gamme.
- **< 1-2 Go** de mémoire.
- Chargement rapide (StreamingEnabled).

## Profilage

- Utiliser le **MicroProfiler** (Ctrl+F6 dans Studio) et le **Developer Console**.
- Mesurer **avant** d'optimiser. Identifier CPU vs GPU vs mémoire vs réseau.
- Utiliser `debug.profilebegin` / `debug.profileend` pour cibler des sections.

```lua
debug.profilebegin("MyHeavyFunction")
-- ... code à profiler
debug.profileend()
```

## Streaming & chargement

```lua
-- Activer le streaming (dans les propriétés de Workspace)
workspace.StreamingEnabled = true
workspace.StreamingMinDistance = 64
workspace.StreamingTargetRadius = 256
```

## Réduire le nombre de parts

- Utiliser des **meshes** (`MeshPart`) au lieu d'assemblages de parts.
- **Union** les géométries statiques complexes.
- Désactiver `CanQuery` et `CanTouch` quand inutile :
```lua
part.CanQuery = false
part.CanTouch = false
```

## LOD (niveaux de détail)

- Modèles complexes → versions simplifiées à distance.
- Utiliser `ModelStreamingMode` et des modèles avec LOD.

## Scripts

```lua
-- ❌ Coûteux
while true do
    wait(0.1)
    -- travail lourd
end

-- ✅ Event-driven
someEvent:Connect(function()
    -- travail seulement quand nécessaire
end)

-- ✅ task.wait au lieu de wait (plus précis, moins de surcharge)
task.wait(0.1)
```

## Mémoire (anti-fuite)

```lua
-- Déconnecter les events
local conn = event:Connect(fn)
-- ...
conn:Disconnect()

-- Nettoyer les tables
local cache = {}
-- quand on n'en a plus besoin :
table.clear(cache)

-- Détruire les instances inutiles
instance:Destroy()
```

## Micro-optimisations Luau

```lua
-- Cache les services et références fréquentes
local Players = game:GetService("Players")

-- Pré-allouer les tables
local list = table.create(100)

-- Éviter les concaténations de strings en boucle (utiliser table.concat)
local parts = {}
for i = 1, 100 do
    parts[i] = "x" .. i
end
local result = table.concat(parts, ",")
```

## Rendu / effets

- Limiter les **lumières dynamiques** (PointLight, SpotLight) — très coûteuses.
- Limiter les **particules** simultanées (`ParticleEmitter`).
- Désactiver les **ombres** (`CastShadow = false`) sur les objets non essentiels.
- Utiliser `Material` léger et des textures compressées.

## Checklist rapide

- [ ] StreamingEnabled activé
- [ ] Pas de boucle lourde par frame
- [ ] Events déconnectés (pas de fuite)
- [ ] Peu de lumières dynamiques
- [ ] CanQuery/CanTouch désactivés quand inutile
- [ ] Meshes/Unions au lieu de milliers de parts
- [ ] Services et références en cache
