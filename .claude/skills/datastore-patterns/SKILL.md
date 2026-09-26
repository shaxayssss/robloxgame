---
name: datastore-patterns
description: Patterns fiables pour DataStore Roblox : retry, caching, autosave, versioning, UpdateAsync, OrderedDataStore, budget. À consulter pour toute persistance de données.
---

# Patterns DataStore fiables (Roblox)

## Objectif

**Aucune donnée de joueur ne doit être perdue.** Pour un jeu +1M joueurs, la
fiabilité des données est critique (une perte de progression = churn massif).

## Structure recommandée

```lua
-- ServerScriptService/DataService (ModuleScript)
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")

local store = DataStoreService:GetDataStore("PlayerData")

local cache = {} -- cache en mémoire par joueur

local DataService = {}
```

## Load avec retry

```lua
local function loadWithRetry(player, attempts)
    attempts = attempts or 3
    for i = 1, attempts do
        local ok, result = pcall(function()
            return store:GetAsync(player.UserId)
        end)
        if ok then
            return result or getDefaultData()
        end
        task.wait(2 ^ i) -- backoff exponentiel
    end
    return getDefaultData() -- fallback (mieux vaut des données par défaut que rien)
end
```

## Save avec retry + autosave

```lua
local function saveWithRetry(player, data, attempts)
    attempts = attempts or 3
    for i = 1, attempts do
        local ok = pcall(function()
            store:SetAsync(player.UserId, data)
        end)
        if ok then return true end
        task.wait(2 ^ i)
    end
    warn("Échec de sauvegarde pour " .. player.Name)
    return false
end

-- Autosave périodique
task.spawn(function()
    while true do
        task.wait(60) -- toutes les 60s
        for player, data in pairs(cache) do
            saveWithRetry(player, data)
        end
    end
end)

-- Sauvegarde à la sortie
Players.PlayerRemoving:Connect(function(player)
    if cache[player] then
        saveWithRetry(player, cache[player])
        cache[player] = nil
    end
end)
```

## UpdateAsync (opérations atomiques)

```lua
-- Pour les transactions (ex. ajouter des coins) sans race condition
local function addCoins(player, amount)
    local ok, result = pcall(function()
        return store:UpdateAsync(player.UserId, function(oldData)
            oldData = oldData or getDefaultData()
            oldData.coins += amount
            return oldData
        end)
    end)
    return ok and result or nil
end
```

## Session locking (anti-double connexion)

```lua
-- Empêcher qu'un joueur charge ses données deux fois (double session)
local activeSessions = {}

local function load(player)
    if activeSessions[player.UserId] then
        player:Kick("Session déjà active")
        return
    end
    activeSessions[player.UserId] = true
    -- ... load
end

Players.PlayerRemoving:Connect(function(player)
    activeSessions[player.UserId] = nil
end)
```

## OrderedDataStore (classements / leaderboards)

```lua
local orderedStore = DataStoreService:GetOrderedDataStore("Leaderboard")

-- Mettre à jour le score (trié automatiquement)
orderedStore:SetAsync(player.UserId, playerScore)

-- Récupérer le top 10
local ok, pages = pcall(function()
    return orderedStore:GetSortedAsync(false, 10):GetCurrentPage()
end)
if ok then
    for rank, entry in ipairs(pages) do
        print(rank, entry.key, entry.value)
    end
end
```

## Versioning (migrations)

```lua
local CURRENT_VERSION = 2

local function migrate(data)
    if not data.version then
        data.version = 1
    end
    if data.version < 2 then
        -- migration v1 -> v2
        data.newField = data.oldField or 0
        data.version = 2
    end
    return data
end
```

## Gestion du budget (throttling)

```lua
-- DataStore a un budget de requêtes par minute. Utiliser GetRequestBudgetForRequestType
local budget = DataStoreService:GetRequestBudgetForRequestType(
    Enum.DataStoreRequestType.SetIncrementAsync)

-- Vérifier avant une opération coûteuse
if budget < 1 then
    warn("Budget DataStore faible, opération différée")
end
```

## Limites à connaître

- **4 Mo** par clé DataStore.
- **Throttling** : limite de requêtes par minute (gérer les retries).
- Utiliser `GetDataStore` avec des **scopes** pour organiser.
- Préférer **un seul dictionnaire** par joueur (moins de clés = moins de requêtes).
- **OrderedDataStore** pour les classements (trié automatiquement).
