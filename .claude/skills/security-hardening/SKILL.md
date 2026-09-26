---
name: security-hardening
description: Techniques de durcissement anti-cheat Roblox : validation serveur, anti-duplication, protection des remotes, patterns d'exploit. À consulter pour sécuriser le jeu.
---

# Durcissement sécurité / anti-cheat Roblox

## Principe fondamental

**Le serveur est la seule autorité.** Le client est un affichage + un émetteur
d'intentions. Tout ce qui a de la valeur se décide côté serveur.

## Menaces courantes

- **Exploits** : injection de scripts côté client (executors).
- **Duplication** : créer des objets de valeur en boucle.
- **Remote abuse** : envoyer des requêtes malveillantes aux remotes.
- **Backdoors** : code qui exécute des commandes arbitraires.
- **Teleport abuse** : se téléporter à des endroits interdits.
- **Speed/fly hack** : modifier la vitesse de déplacement.

## Checklist de durcissement

### Validation des remotes
```lua
Remotes.Action.OnServerEvent:Connect(function(player, ...)
    -- 1. Types
    -- 2. Bornes
    -- 3. Permissions
    -- 4. Cooldown (anti-spam)
    -- 5. État du jeu
    -- ... puis seulement la logique
end)
```

### Anti-duplication
- Toute création d'objet de valeur passe par le **serveur**.
- Le client ne peut pas instancier des items dans son inventaire.

### ProcessReceipt
- Toujours valider les achats via `ProcessReceipt` (jamais confiance au client).

### Pas de secrets côté client
- Clés, formules, taux de drop → côté serveur uniquement.
- Le client reçoit le **résultat**, pas la formule.

## Anti-spam

```lua
local cooldowns = {}
local function throttle(player, key, seconds)
    local now = os.clock()
    local last = cooldowns[player] and cooldowns[player][key]
    if last and now - last < seconds then return true end
    cooldowns[player] = cooldowns[player] or {}
    cooldowns[player][key] = now
    return false
end
```

## Anti speed/fly hack (validation de déplacement)

```lua
-- Vérifier la vitesse de déplacement côté serveur
local function validateMovement(player)
    local character = player.Character
    if not character then return end
    local root = character:FindFirstChild("HumanoidRootPart")
    local humanoid = character:FindFirstChild("Humanoid")
    if not root or not humanoid then return end

    local speed = root.AssemblyLinearVelocity.Magnitude
    local maxSpeed = humanoid.WalkSpeed + 10 -- marge

    if speed > maxSpeed then
        -- Triche détectée : corriger ou kick
        root.AssemblyLinearVelocity = Vector3.zero
    end
end
```

## Anti-teleport (vérification de distance)

```lua
-- Vérifier que le joueur ne se téléporte pas trop loin
local lastPosition = {}
local function validatePosition(player)
    local character = player.Character
    if not character then return end
    local root = character:FindFirstChild("HumanoidRootPart")
    if not root then return end

    local last = lastPosition[player]
    if last and (root.Position - last).Magnitude > 100 then
        -- Téléportation suspecte
        root.CFrame = last
    end
    lastPosition[player] = root.CFrame
end
```

## Protéger les modules sensibles

- Ne pas exposer les modules serveur au client.
- Utiliser `ServerScriptService` (jamais répliqué) pour la logique sensible.

## Audit régulier

1. Chercher les remotes sans validation.
2. Chercher la logique critique côté client.
3. Chercher les `loadstring` / exécution dynamique (backdoor).
4. Tester les cas de triche (spam, valeurs extrêmes, duplication, téléportation).
