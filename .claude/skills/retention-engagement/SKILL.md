---
name: retention-engagement
description: Patterns de rétention et d'engagement Roblox : onboarding, progression, daily rewards, streaks, boucles sociales, événements. À consulter pour fidéliser les joueurs.
---

# Rétention & engagement Roblox

## Pourquoi c'est critique

Pour un jeu +1M joueurs, la **rétention** (D1, D7, D30) est la métrique reine.
Un bon onboarding + de bonnes boucles = des joueurs qui reviennent.

## Les 60 premières secondes (FTUE)

- Le joueur comprend le but **immédiatement**.
- Première récompense **dans les 30 secondes** (dopamine rapide).
- Tutoriel **progressif** : on apprend en jouant, pas en lisant.
- Zéro friction : pas de menu complexe, pas de chargement long.

## Boucles de rétention

### Progression
- Niveaux, paliers, déblocages réguliers.
- Barre de progression toujours visible.

### Quotidien (daily rewards)
```lua
-- Récompense de connexion journalière
local function claimDaily(player)
    local last = data:Get(player, "lastDaily")
    local today = os.date("%Y-%m-%d")
    if last == today then return end -- déjà réclamé
    data:Set(player, "lastDaily", today)
    data:Set(player, "coins", data:Get(player, "coins") + 100)
end
```

### Streaks (séries de connexions)
```lua
-- Récompense croissante pour les connexions consécutives
local function claimStreak(player)
    local streak = data:Get(player, "streak") or 0
    local last = data:Get(player, "lastLogin")
    local today = os.date("%Y-%m-%d")

    if last == today then return end -- déjà fait aujourd'hui

    local yesterday = os.date("%Y-%m-%d", os.time() - 86400)
    if last == yesterday then
        streak += 1 -- série continue
    else
        streak = 1 -- série brisée, on recommence
    end

    data:Set(player, "streak", streak)
    data:Set(player, "lastLogin", today)
    -- Récompense proportionnelle au streak
    data:Set(player, "coins", data:Get(player, "coins") + streak * 10)
end
```

### Social
- Guildes/groupes, amis, classements, défis entre joueurs.
- Le social est le **meilleur levier de rétention** long terme.

### Collection
- Objets à collectionner, raretés, complétion.
- Crée un objectif long terme.

### Événements limités
- Événements temporaires (FOMO positif).
- Récompenses exclusives.

## Principes

- **Récompenses fréquentes** : progression constante ressentie.
- **Objectifs clairs** : toujours un but atteignable à court terme.
- **Feedback** : chaque action a un retour visuel/sonore.
- **Pas de frustration** : éviter les punitions lourdes (perte de progression).

## Mesure (via analytics)

- Suivre D1/D7/D30, durée de session, funnel d'abandon.
- Identifier où les joueurs partent et itérer.
