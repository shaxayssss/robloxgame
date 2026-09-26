---
name: roblox-api-reference
description: Référence des Services et API Roblox les plus utilisés (Players, RunService, ReplicatedStorage, CollectionService, TweenService, Raycast, Attributes, etc.). À consulter pour utiliser la bonne API.
---

# Référence API Roblox

## Services essentiels

| Service | Usage |
|---|---|
| `Players` | Joueurs, personnages, `PlayerAdded`/`PlayerRemoving` |
| `RunService` | Boucles (`Heartbeat`, `RenderStepped`, `Stepped`) |
| `ReplicatedStorage` | Modules partagés + remotes |
| `ServerStorage` | Assets serveur (non répliqués) |
| `ServerScriptService` | Scripts serveur |
| `StarterPlayerScripts` | Scripts client |
| `CollectionService` | Tags sur les instances (`AddTag`, `GetTagged`) |
| `TweenService` | Animations UI/objets |
| `DataStoreService` | Persistance |
| `MarketplaceService` | Achats (gamepasses, dev products) |
| `TeleportService` | Téléportation entre places |
| `LocalizationService` | Traduction |
| `AnalyticsService` | Télémétrie |
| `Lighting` | Éclairage, ambiance |
| `SoundService` | Sons, `SoundGroup` |
| `ContextActionService` | Bindings d'input (mobile + PC) |
| `PhysicsService` | Groupes de collision |
| `UserInputService` | Input clavier/souris/tactile |

## Patterns courants

### Récupérer un service (toujours en cache)
```lua
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
```

### Joueur + personnage
```lua
Players.PlayerAdded:Connect(function(player)
    player.CharacterAdded:Connect(function(character)
        local humanoid = character:WaitForChild("Humanoid")
        -- ...
    end)
end)
```

### CollectionService (tagging)
```lua
local CollectionService = game:GetService("CollectionService")
CollectionService:AddTag(part, "Interactable")
for _, obj in ipairs(CollectionService:GetTagged("Interactable")) do
    -- ...
end
```

### Attributes (données sur les instances)
```lua
-- Écrire
instance:SetAttribute("Coins", 100)
-- Lire
local coins = instance:GetAttribute("Coins")
-- Écouter les changements
instance:GetAttributeChangedSignal("Coins"):Connect(function()
    -- ...
end)
```

### Raycast (détection de collision)
```lua
local workspace = game:GetService("Workspace")
local origin = Vector3.new(0, 10, 0)
local direction = Vector3.new(0, -100, 0)

local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.FilterDescendantsInstances = { character }

local result = workspace:Raycast(origin, direction, params)
if result then
    print(result.Instance, result.Position, result.Normal)
end
```

### TweenService (animation)
```lua
local TweenService = game:GetService("TweenService")
local tweenInfo = TweenInfo.new(0.5, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local tween = TweenService:Create(uiElement, tweenInfo, { Position = UDim2.new(0, 0, 0, 0) })
tween:Play()
```

### Input (ContextActionService — mobile + PC)
```lua
local ContextActionService = game:GetService("ContextActionService")
ContextActionService:BindAction("Jump", function(actionName, inputState, inputObject)
    if inputState == Enum.UserInputState.Begin then
        -- action
    end
end, false, Enum.KeyCode.Space, Enum.KeyCode.ButtonA)
```

### Téléportation entre places
```lua
local TeleportService = game:GetService("TeleportService")
TeleportService:Teleport(placeId, player)
```

### Physique (groupes de collision)
```lua
local PhysicsService = game:GetService("PhysicsService")
PhysicsService:CreateCollisionGroup("NoCollide")
PhysicsService:CollisionGroupSetCollidable("NoCollide", "Default", false)
part.CollisionGroup = "NoCollide"
```
