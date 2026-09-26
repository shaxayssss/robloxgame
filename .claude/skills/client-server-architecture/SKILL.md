---
name: client-server-architecture
description: Architecture client/serveur Roblox : RemoteEvents, RemoteFunctions, validation serveur, réplication, rate limiting. À consulter pour toute communication réseau.
---

# Architecture client/serveur Roblox

## Principe fondamental

**Le serveur est la seule autorité.** Le client ne fait que :
1. Envoyer des **intentions** (via remotes).
2. Afficher l'**état** répliqué.

Jamais de logique critique (argent, stats, drops) côté client.

## Centraliser les remotes

```lua
-- ReplicatedStorage/Remotes (ModuleScript)
local Remotes = {}

Remotes.Jump = Instance.new("RemoteEvent")
Remotes.Jump.Name = "Jump"
Remotes.Jump.Parent = replicatedStorage

Remotes.RequestData = Instance.new("RemoteFunction")
Remotes.RequestData.Name = "RequestData"
Remotes.RequestData.Parent = replicatedStorage

return Remotes
```

## RemoteEvent (fire-and-forget)

```lua
-- Client : envoie une intention
Remotes.Jump:FireServer()

-- Serveur : reçoit et VALIDE
Remotes.Jump.OnServerEvent:Connect(function(player)
    -- Validation : le joueur est-il autorisé à sauter ?
    if not canJump(player) then return end
    -- Logique d'autorité
    doJump(player)
end)
```

## RemoteFunction (requête/réponse)

```lua
-- Client : demande des données
local data = Remotes.RequestData:InvokeServer()

-- Serveur : répond
Remotes.RequestData.OnServerInvoke = function(player)
    -- Validation des permissions
    return getDataFor(player)
end
```

## RemoteEvent vs RemoteFunction (quand choisir quoi)

| Critère | RemoteEvent | RemoteFunction |
|---|---|---|
| Sens | Unidirectionnel | Requête/réponse |
| Bloquant | Non | Oui (le client attend) |
| Usage | Actions, mises à jour | Demandes de données |
| Fréquence | Haute fréquence OK | À limiter (coûteux) |

> Préférer `RemoteEvent` pour les actions fréquentes, `RemoteFunction` pour les
> rares demandes de données.

## Validation serveur (checklist)

```lua
Remotes.BuyItem.OnServerEvent:Connect(function(player, itemId)
    -- 1. Types
    if typeof(itemId) ~= "string" then return end
    -- 2. Bornes / existence
    if not Items[itemId] then return end
    -- 3. Permissions
    if not player:GetAttribute("CanBuy") then return end
    -- 4. Anti-spam (cooldown)
    if isOnCooldown(player, "buy", 0.5) then return end
    -- 5. État du jeu
    if gameState ~= "playing" then return end
    -- ... logique métier
end)
```

## Rate limiting (anti-spam robuste)

```lua
local cooldowns = {}
local function throttle(player, key, seconds)
    local now = os.clock()
    local entry = cooldowns[player]
    if entry and entry[key] and now - entry[key] < seconds then
        return true -- bloqué
    end
    if not entry then
        entry = {}
        cooldowns[player] = entry
    end
    entry[key] = now
    return false
end

-- Nettoyage à la déconnexion
Players.PlayerRemoving:Connect(function(player)
    cooldowns[player] = nil
end)
```

## Réplication d'état (Attributes)

```lua
-- Le serveur met à jour un attribut répliqué
player:SetAttribute("Coins", newCoins)

-- Le client écoute les changements (répliqués automatiquement)
player:GetAttributeChangedSignal("Coins"):Connect(function()
    updateUI(player:GetAttribute("Coins"))
end)
```

## Gérer la déconnexion

```lua
Players.PlayerRemoving:Connect(function(player)
    -- Sauvegarder les données
    -- Nettoyer les cooldowns, états
    cooldowns[player] = nil
end)
```

## Anti-triche : vérifier la distance

```lua
-- Valider que le joueur est bien à portée de l'action
local function isInRange(player, target)
    local character = player.Character
    if not character then return false end
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root then return false end
    return (root.Position - target.Position).Magnitude < 50 -- 50 studs
end
```
