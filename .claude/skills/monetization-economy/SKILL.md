---
name: monetization-economy
description: Patterns de monétisation Roblox : MarketplaceService, ProcessReceipt, gamepasses, dev products, équilibrage économique, pricing psychologique. À consulter pour tout achat.
---

# Monétisation & économie Roblox

## Principe : rétention avant monétisation

Un joueur qui reste joue et finit par payer. Un joueur frustré part. **Jamais
pay-to-win** écrasant.

## MarketplaceService

```lua
local MarketplaceService = game:GetService("MarketplaceService")

-- Déclencher un achat (gamepass)
MarketplaceService:PromptGamePassPurchase(player, gamepassId)

-- Déclencher un achat (dev product)
MarketplaceService:PromptProductPurchase(player, productId)
```

## ProcessReceipt (source de vérité)

```lua
local function processReceipt(receiptInfo)
    local player = Players:GetPlayerByUserId(receiptInfo.PlayerId)
    if not player then return Enum.ProductPurchaseDecision.NotProcessedYet end

    -- Anti-duplication : vérifier si déjà traité
    if alreadyProcessed(receiptInfo.PurchaseId) then
        return Enum.ProductPurchaseDecision.PurchaseGranted
    end

    -- Accorder le produit
    local ok = grantProduct(player, receiptInfo.ProductId)
    if ok then
        markProcessed(receiptInfo.PurchaseId)
        return Enum.ProductPurchaseDecision.PurchaseGranted
    end

    return Enum.ProductPurchaseDecision.NotProcessedYet -- retry
end

MarketplaceService.ProcessReceipt = processReceipt
```

## Gamepass vs Dev Product

| Type | Usage |
|---|---|
| **Gamepass** | Permanent, achat unique (accès, cosmétique permanent, multiplicateur) |
| **Dev Product** | Consommable, achats répétés (devises, boosts temporaires) |

## Équilibrage économique

- **Petits achats fréquents** > gros achats rares.
- Le jeu doit être **agréable sans dépenser** ; la monétisation **accélère**.
- **Paliers de prix** psychologiques (ex. 50, 100, 250, 500 Robux).
- **Offres limitées** / packs pour stimuler l'achat.
- Suivre l'**ARPPU** et la **conversion** (via `analytics`).

## Pricing psychologique

- **Ancrage** : afficher un prix "barré" à côté d'un prix réduit.
- **Paliers** : 3 options (petit/moyen/gros) → le "moyen" est le plus vendu.
- **Bundle** : regrouper plusieurs items à prix réduit.
- **Offres limitées** : rareté temporelle (FOMO).
- **Premier achat** : une offre spéciale pour convertir les non-payeurs.

## Anti-fraude

- Toujours valider via `ProcessReceipt` (jamais confiance au client).
- Gérer les **retries** et **duplicatas** de `ProcessReceipt`.
- Journaliser les transactions.
- Vérifier le **solde** côté serveur avant d'accorder un produit.

## Métriques à suivre

- **Conversion** : % de joueurs qui achètent.
- **ARPPU** : revenu moyen par payeur.
- **ARPU** : revenu moyen par joueur (tous joueurs confondus).
- **LTV** : valeur vie d'un joueur.
