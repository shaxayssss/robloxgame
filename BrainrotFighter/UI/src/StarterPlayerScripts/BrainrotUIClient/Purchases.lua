-- Purchases: opens the Roblox purchase prompts and shows live prices.
-- Nothing is granted here: the server grants in ProcessReceipt.

local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Notify = require(script.Parent:WaitForChild("Notify"))
local Effects = require(script.Parent:WaitForChild("Effects"))
local State = require(script.Parent:WaitForChild("State"))

local Text = Config.Text
local player = Players.LocalPlayer

local Purchases = {}

local PROMPT_TIMEOUT = 30

local pending = false
local promptToken = 0
local prices: { [string]: number } = {}

local function finish()
	pending = false
	Effects.purchaseOverlay(false)
end

local function entryFor(kind: string, key: string): { [string]: any }?
	return if kind == "Pass" then Rules.PassByKey[key] else Rules.ProductByKey[key]
end

-- kind = "Product" (developer product) or "Pass" (game pass), key = its Key in UIConfig.
function Purchases.prompt(kind: string, key: string)
	local entry = entryFor(kind, key)
	if not entry then
		return
	end
	if not entry.Id or entry.Id <= 0 then
		Notify.show(Text.ProductMissing:format(entry.Name or key), "error", 4)
		return
	end
	if kind == "Pass" and State.get("Pass_" .. key) == true then
		Notify.show(Text.AlreadyOwned, "info")
		return
	end
	if pending then
		return
	end
	pending = true
	promptToken += 1
	local token = promptToken
	Effects.purchaseOverlay(true)
	local ok = pcall(function()
		if kind == "Pass" then
			MarketplaceService:PromptGamePassPurchase(player, entry.Id)
		else
			MarketplaceService:PromptProductPurchase(player, entry.Id)
		end
	end)
	if not ok then
		finish()
		Notify.show(Text.PurchaseError, "error")
		return
	end
	-- never leave the overlay stuck if Roblox does not answer
	task.delay(PROMPT_TIMEOUT, function()
		if pending and promptToken == token then
			finish()
		end
	end)
end

local function priceText(entry: { [string]: any }, cacheKey: string): string
	local price = prices[cacheKey] or entry.PriceHint
	return if price then "R$ " .. price else "R$ ?"
end

-- Calls update(text) with the price hint now, then with the real price once known.
function Purchases.observePrice(kind: string, key: string, update: (string) -> ())
	local entry = entryFor(kind, key)
	if not entry then
		return
	end
	local cacheKey = kind .. ":" .. key
	update(priceText(entry, cacheKey))
	if not entry.Id or entry.Id <= 0 or prices[cacheKey] then
		return
	end
	task.spawn(function()
		local infoType = if kind == "Pass" then Enum.InfoType.GamePass else Enum.InfoType.Product
		local ok, info = pcall(function()
			return MarketplaceService:GetProductInfoAsync(entry.Id, infoType)
		end)
		if not ok then
			-- older engines only know the previous name
			ok, info = pcall(function()
				return (MarketplaceService :: any):GetProductInfo(entry.Id, infoType)
			end)
		end
		if ok and type(info) == "table" and type(info.PriceInRobux) == "number" then
			prices[cacheKey] = info.PriceInRobux
			update(priceText(entry, cacheKey))
		end
	end)
end

function Purchases.init()
	MarketplaceService.PromptProductPurchaseFinished:Connect(function(userId, _, purchased)
		if userId ~= player.UserId then
			return
		end
		finish()
		if not purchased then
			Notify.show(Text.PurchaseCancelled, "info", 2)
		end
	end)
	MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(who, _, purchased)
		if who ~= player then
			return
		end
		finish()
		if not purchased then
			Notify.show(Text.PurchaseCancelled, "info", 2)
		end
	end)
end

return Purchases
