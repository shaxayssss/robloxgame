---
name: luau-best-practices
description: Bonnes pratiques Luau pour Roblox : conventions, typage, OOP, modules, gestion des events, gestion d'erreurs. À consulter avant d'écrire du Luau.
---

# Bonnes pratiques Luau (Roblox)

## Conventions de nommage

- `PascalCase` : modules, services, classes.
- `camelCase` : variables, fonctions, paramètres.
- `UPPER_SNAKE_CASE` : constantes.
- Préfixes utiles : `is`, `has`, `can` pour les booléens (`isAlive`, `hasItem`).

## Typage progressif

```lua
-- Typage des paramètres et retours quand c'est clair
local function add(a: number, b: number): number
    return a + b
end

-- Types pour les structures de données
type PlayerData = {
    coins: number,
    level: number,
    inventory: { [string]: number },
}

-- Types unions et optionnels
type Result = { ok = true, value: any } | { ok = false, error: string }
```

## Modules (ModuleScript)

```lua
-- Un module = une API claire, un seul responsabilité
local MySystem = {}
MySystem.__index = MySystem

function MySystem.new(...)
    local self = setmetatable({}, MySystem)
    -- init
    return self
end

function MySystem:Start()
    -- ...
end

return MySystem
```

## OOP (programmation orientée objet)

```lua
-- Classe complète avec héritage
local BaseClass = {}
BaseClass.__index = BaseClass

function BaseClass.new()
    local self = setmetatable({}, BaseClass)
    return self
end

function BaseClass:Method()
    -- ...
end

-- Héritage
local DerivedClass = setmetatable({}, BaseClass)
DerivedClass.__index = DerivedClass

function DerivedClass.new()
    local self = BaseClass.new()
    setmetatable(self, DerivedClass)
    return self
end

function DerivedClass:Method() -- override
    BaseClass.Method(self) -- appel du parent
    -- ...
end
```

## Gestion des events (anti-fuite mémoire)

```lua
-- TOUJOURS déconnecter les connexions quand on n'en a plus besoin
local conn = someEvent:Connect(function() end)
-- ...
conn:Disconnect()

-- Ou attacher à un objet qui sera détruit
local conn = someEvent:Connect(function() end)
someInstance.Destroying:Connect(function()
    conn:Disconnect()
end)
```

## Signaux personnalisés (BindableEvent)

```lua
-- Pour créer ses propres événements découplés
local signal = Instance.new("BindableEvent")

-- Émettre
signal:Fire(data)

-- Écouter
local conn = signal.Event:Connect(function(data)
    -- ...
end)
```

## Gestion d'erreurs

```lua
-- pcall : protéger un appel qui peut échouer
local ok, result = pcall(function()
    return riskyOperation()
end)
if not ok then
    warn("Erreur : " .. tostring(result))
end

-- xpcall : avec un handler d'erreur
xpcall(function()
    riskyOperation()
end, function(err)
    warn("Erreur : " .. err)
end)
```

## Boucles

```lua
-- ❌ À éviter
while true do
    wait() -- imprécis, peut bloquer
end

-- ✅ Préférer les events
RunService.Heartbeat:Connect(function(dt)
    -- dt = delta time
end)

-- ✅ Ou task.wait() pour une pause non-bloquante
task.wait(1)
```

## Performance de base

- Éviter de créer des instances dans les boucles chaudes.
- Mettre en cache les références (`local Players = game:GetService("Players")`).
- Utiliser `table.create` et pré-allouer quand possible.
- `ipairs` > `pairs` pour les tableaux séquentiels (perf).

## Organisation des dossiers (ce projet)

Le code vit sur disque et Rojo le synchronise — voir `CLAUDE.md`. Écris dans
`KaijuHeist/src/`, jamais dans une arborescence Roblox imaginaire :

```
KaijuHeist/src/
  Shared/    → ReplicatedStorage.Shared   (Constants, KaijuDatabase, Remotes, MapData)
  Server/    → ServerScriptService.Server (un module par service + Main.server.lua)
  Client/    → StarterPlayer.StarterPlayerScripts.Client
```

- Un module = `NomDuService.lua` → devient un `ModuleScript`.
- Seuls les scripts d'amorçage portent `.server.lua` / `.client.lua`.
- Le dossier `Remotes` n'existe pas sur disque : il est créé à l'exécution par
  `Shared/Remotes.lua` (`EnsureCreated()`), et récupéré côté client par `Get()`.
- `Shared/MapData.lua` est **généré** par `blender/build_map.py` : ne l'édite pas.
