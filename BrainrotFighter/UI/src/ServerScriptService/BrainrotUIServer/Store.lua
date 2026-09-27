-- Store: Robux purchases. Owns the ONLY MarketplaceService.ProcessReceipt of the game
-- (Roblox keeps a single callback: a second script setting it silently wins).
--
-- * Developer products are granted in ProcessReceipt, saved, then confirmed.
--   A receipt already processed is never granted twice.
-- * Game passes: ownership is checked on join and after a purchase, the
--   one-time rewards are remembered in the profile.
-- * Paid random items (wheel spins) are flagged for players whose country
--   restricts them (PolicyService), the client hides those offers.

local Players = game:GetService("Players")
local MarketplaceService = game:GetService("MarketplaceService")
local PolicyService = game:GetService("PolicyService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local PlayerData = require(script.Parent:WaitForChild("PlayerData"))
local Economy = require(script.Parent:WaitForChild("Economy"))

local Text = Config.Text

local Store = {}

local function grantPass(player: Player, pass: { [string]: any })
	player:SetAttribute("Pass_" .. pass.Key, true)
	local data = PlayerData.Get(player)
	if not data or not pass.Rewards or data.PassRewards[pass.Key] then
		return
	end
	data.PassRewards[pass.Key] = true
	Economy.Add(player, pass.Rewards)
	Economy.Notify(player, Text.PassRewardGranted:format(pass.Name), "reward")
	task.spawn(PlayerData.SaveAsync, player, false)
end

local function checkPasses(player: Player)
	for _, pass in Config.GamePasses do
		if pass.Id and pass.Id > 0 then
			local ok, owns = pcall(function()
				return MarketplaceService:UserOwnsGamePassAsync(player.UserId, pass.Id)
			end)
			if ok and owns then
				grantPass(player, pass)
			end
		end
	end
end

local function checkPolicy(player: Player)
	local ok, info = pcall(function()
		return PolicyService:GetPolicyInfoForPlayerAsync(player)
	end)
	-- when the policy is unknown, stay on the safe side and hide paid random items
	local restricted = not ok or type(info) ~= "table" or info.ArePaidRandomItemsRestricted == true
	player:SetAttribute("PaidRandomRestricted", restricted)
end

local function onPlayerReady(player: Player)
	task.spawn(checkPolicy, player)
	task.spawn(checkPasses, player)
end

local function onPassPurchaseFinished(player: Player, passId: number, purchased: boolean)
	if not purchased then
		return
	end
	local pass = Rules.PassById[passId]
	if pass then
		grantPass(player, pass)
		Economy.Notify(player, Text.ThanksPurchase, "success")
		Economy.Reward(player, { Pass = pass.Key })
	end
end

local function grantProduct(player: Player, product: { [string]: any })
	local grant = product.Grant or {}
	if grant.RebirthSkip then
		Economy.Rebirth(player, true)
	else
		Economy.Add(player, grant)
	end
end

local function processReceipt(info: { [string]: any })
	local player = Players:GetPlayerByUserId(info.PlayerId)
	if not player then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	local data = PlayerData.WaitForData(player, 15)
	if not data then
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	local purchaseId = tostring(info.PurchaseId)
	if data.Receipts[purchaseId] then
		return Enum.ProductPurchaseDecision.PurchaseGranted
	end
	local product = Rules.ProductById[info.ProductId]
	if not product then
		warn(("[BrainrotUI] Unknown developer product %s: add it to UIConfig.Products"):format(tostring(info.ProductId)))
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	grantProduct(player, product)
	PlayerData.RecordReceipt(player, purchaseId)
	if not PlayerData.SaveAsync(player, false) then
		-- granted in memory and remembered: a retry in this session will not grant it again
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	Economy.Notify(player, Text.ThanksPurchase, "success")
	Economy.Reward(player, { Product = product.Key })
	return Enum.ProductPurchaseDecision.PurchaseGranted
end

function Store.Start()
	MarketplaceService.ProcessReceipt = processReceipt
	MarketplaceService.PromptGamePassPurchaseFinished:Connect(onPassPurchaseFinished)
	PlayerData.Loaded:Connect(onPlayerReady)
	for _, player in Players:GetPlayers() do
		if PlayerData.Get(player) then
			onPlayerReady(player)
		end
	end
end

return Store
