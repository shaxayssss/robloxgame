-- BrainrotUI client: builds the interface in code and wires it to the server.
-- The server decides everything; this script only displays and asks.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local SocialService = game:GetService("SocialService")

local player = Players.LocalPlayer
local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local remotes = shared:WaitForChild("Remotes")
local requestRemote = remotes:WaitForChild("Request") :: RemoteFunction

local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Widgets = require(script:WaitForChild("Widgets"))
local State = require(script:WaitForChild("State"))
local Notify = require(script:WaitForChild("Notify"))
local Effects = require(script:WaitForChild("Effects"))
local Windows = require(script:WaitForChild("Windows"))
local Purchases = require(script:WaitForChild("Purchases"))
local Hud = require(script:WaitForChild("Hud"))
local ShopWindow = require(script:WaitForChild("ShopWindow"))
local RebirthWindow = require(script:WaitForChild("RebirthWindow"))
local IndexWindow = require(script:WaitForChild("IndexWindow"))
local WheelWindow = require(script:WaitForChild("WheelWindow"))
local PickupFx = require(script:WaitForChild("PickupFx"))

local Text = Config.Text

-- Server request that never throws: always returns a table with `ok`.
local function request(action: string, argument: any?): { [string]: any }
	local ok, result = pcall(function()
		return requestRemote:InvokeServer(action, argument)
	end)
	if ok and type(result) == "table" then
		return result
	end
	return { ok = false, message = Text.GenericError }
end

local function invite()
	local ok, canInvite = pcall(function()
		return SocialService:CanSendGameInviteAsync(player)
	end)
	if ok and canInvite then
		pcall(function()
			SocialService:PromptGameInvite(player)
		end)
	else
		Notify.show(Text.InviteUnavailable, "info")
	end
end

-- Screen ----------------------------------------------------------------------

local playerGui = player:WaitForChild("PlayerGui")
local previous = playerGui:FindFirstChild("BrainrotUI")
if previous then
	previous:Destroy()
end
local screenGui = Widgets.create("ScreenGui", {
	Name = "BrainrotUI",
	ResetOnSpawn = false,
	IgnoreGuiInset = false,
	ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets,
	ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
	DisplayOrder = 5,
	Parent = playerGui,
}) :: ScreenGui

Widgets.init(screenGui)
Notify.init(screenGui)
Effects.init(screenGui)
Windows.init(screenGui)
Purchases.init()

Hud.build(screenGui, {
	OpenShop = function()
		Windows.open("Shop")
	end,
	OpenRebirth = function()
		Windows.open("Rebirth")
	end,
	OpenIndex = function()
		Windows.open("Index")
	end,
	OpenWheel = function()
		Windows.open("Wheel")
	end,
	Invite = invite,
})
ShopWindow.build()
RebirthWindow.build(request)
IndexWindow.build(request)
WheelWindow.build(request)
PickupFx.start(Config.Pickups.Tag)

-- HUD badges -------------------------------------------------------------------

local function refreshBadges()
	local rebirth = Hud.getTile("Rebirth")
	if rebirth then
		rebirth.Badge.Set(if RebirthWindow.isReady() then "!" else nil)
	end
	local wheel = Hud.getTile("Wheel")
	if wheel then
		local spins = WheelWindow.availableSpins()
		wheel.Badge.Set(if spins > 0 then tostring(math.min(spins, 99)) else nil)
	end
	local index = Hud.getTile("Index")
	if index then
		index.Badge.Set(if IndexWindow.hasNews() then "!" else nil)
	end
end

State.onAnyChange(refreshBadges)
IndexWindow.onChanged(refreshBadges)
refreshBadges()

-- Server messages ------------------------------------------------------------------

local notifyRemote = remotes:WaitForChild("Notify") :: RemoteEvent
local rewardRemote = remotes:WaitForChild("Reward") :: RemoteEvent

notifyRemote.OnClientEvent:Connect(function(text, kind)
	if type(text) == "string" then
		Notify.show(text, kind)
	end
end)

rewardRemote.OnClientEvent:Connect(function(payload)
	if type(payload) ~= "table" then
		return
	end
	if payload.Stat and type(payload.Amount) == "number" then
		Hud.showGain(payload.Stat, payload.Amount)
	end
	if payload.Item and payload.New then
		local item = Rules.ItemById[payload.Item]
		if item then
			IndexWindow.markNew(item.Id)
			Notify.show(Text.IndexNewItem:format(item.Name), "reward")
		end
	end
	local product = payload.Product and Rules.ProductByKey[payload.Product]
	if product then
		local grant = product.Grant or {}
		local info = Rules.describe(grant)
		if grant.RebirthSkip then
			Effects.rewardPopup("🔁", Text.RebirthDone, nil, Widgets.Theme.Purple)
		elseif grant.Boosts then
			Effects.rewardPopup(product.Icon or info.Icon, product.Name, Text.BoostStarted:format(product.Name), Widgets.Theme.Gold)
		else
			Effects.rewardPopup(product.Icon or info.Icon, "+" .. info.Long, nil, Widgets.Theme.Gold)
		end
	end
	local pass = payload.Pass and Rules.PassByKey[payload.Pass]
	if pass then
		Effects.rewardPopup(pass.Icon, pass.Name, Text.ThanksPurchase, pass.Colors[1])
	end
end)

-- Once-per-second refresh (countdowns, boosts, free spin) -----------------------------

local elapsed = 1
RunService.Heartbeat:Connect(function(dt)
	elapsed += dt
	if elapsed < 1 then
		return
	end
	elapsed = 0
	Hud.tick()
	if Windows.isOpen("Wheel") then
		WheelWindow.refresh()
	end
	refreshBadges()
end)

-- Warn testers when progress is not saved (Studio without API access).
task.spawn(function()
	while player:GetAttribute("DataReady") ~= true do
		player:GetAttributeChangedSignal("DataReady"):Wait()
	end
	if player:GetAttribute("DataSaved") == false then
		Notify.show(Text.SessionOnly, "info", 6)
	end
end)
