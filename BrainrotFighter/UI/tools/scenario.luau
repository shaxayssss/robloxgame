-- Integration scenario: runs the real server + client code in the mock, drives
-- the interface like a player, checks the rules, and prints GUI snapshots.

local passed, failed = 0, 0
local function check(name, condition, detail)
	if condition then
		passed += 1
	else
		failed += 1
		print("CHECK FAILED: " .. name .. (if detail then " (" .. tostring(detail) .. ")" else ""))
	end
end

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local Players = game:GetService("Players")

mountTree(ReplicatedStorage, TREE.shared, "ReplicatedStorage")
local serverScript = mountTree(ServerScriptService, TREE.server, "ServerScriptService")

local player = makePlayer(1001, "Tester")
LOCAL_PLAYER = player
rawset(Players, "_getters", { LocalPlayer = function() return player end })

runScript(serverScript)
advance(0.2)
player.Parent = Players
Players.PlayerAdded:Fire(player)
advance(0.5)
check("data ready", player:GetAttribute("DataReady") == true)
check("data persistent (in-memory store)", player:GetAttribute("DataSaved") == true)
check("lock written", DATASTORE["player_1001"] and DATASTORE["player_1001"].Lock ~= nil)

local clientScript = mountTree(player.PlayerScripts, TREE.client, "StarterPlayerScripts")
runScript(clientScript)
advance(1)

local screenGui = player.PlayerGui:FindFirstChild("BrainrotUI")
check("screen gui built", screenGui ~= nil)

local function snap(name)
	advance(0.001)
	print(("SNAP %s %d %d %d %s"):format(name, VIEWPORT.X, VIEWPORT.Y, TOP_INSET, snapshot(screenGui)))
end

local function find(path)
	local node = screenGui
	for part in string.gmatch(path, "[^/]+") do
		node = node and node:FindFirstChild(part)
	end
	assert(node, "path not found: " .. path)
	return node
end

local function click(path)
	find(path).Activated:Fire()
	advance(0.05)
end

local shared = ReplicatedStorage.BrainrotUI
local Config = requireModule(shared.UIConfig)
local Rules = requireModule(shared.Rules)
local Format = requireModule(shared.Format)
local Economy = requireModule(serverScript.Economy)
local PlayerData = requireModule(serverScript.PlayerData)
local Store = requireModule(serverScript.Store)

-- Format ---------------------------------------------------------------
local cases = {
	{ 0, "0" }, { 999, "999" }, { 1000, "1K" }, { 1234, "1.23K" }, { 12345, "12.3K" }, { 123456, "123K" },
	{ 999999, "999K" }, { 1e6, "1M" }, { 2.5e9, "2.5B" }, { 1e15, "1Qa" }, { 100000, "100K" }, { 1050, "1.05K" },
}
for _, case in cases do
	check("Format.short " .. case[1], Format.short(case[1]) == case[2], Format.short(case[1]))
end
check("Format.clock", Format.clock(75) == "1:15" and Format.clock(3725) == "1:02:05", Format.clock(3725))
check("Format.full", Format.full(1234567) == "1 234 567", Format.full(1234567))
check("Format.percent", Format.percent(0.3) == "30%" and Format.percent(0.06) == "6%" and Format.percent(0.025) == "2.5%", Format.percent(0.025))
check("Format.duration", Format.duration(300) == "5 min" and Format.duration(5400) == "1 h 30", Format.duration(5400))

-- Rules ------------------------------------------------------------------
check("rebirth requirement", Rules.rebirthRequirement(0) == 100 and Rules.rebirthRequirement(2) == 900)
local odds = Rules.wheelOdds()
local sum = 0
for _, v in odds do sum += v end
check("odds sum to 1", math.abs(sum - 1) < 1e-9)
local rng = Random.new(7)
local counts = {}
for _ = 1, 20000 do
	local i = Rules.pickWeighted(Config.Wheel.Rewards, rng)
	counts[i] = (counts[i] or 0) + 1
end
for i, reward in Config.Wheel.Rewards do
	local observed = (counts[i] or 0) / 20000
	check("weighted draw " .. i, math.abs(observed - odds[i]) < 0.02, observed)
end

-- fresh HUD ---------------------------------------------------------------
snap("hud_fresh")
local wheelBadge = find("HudLeft/Buttons/Wheel/Badge")
check("wheel badge shows spins", wheelBadge.Visible and wheelBadge.Text.Text == "2", wheelBadge.Text.Text)

-- progress ------------------------------------------------------------------
Economy.Add(player, { Coins = 12345, Gems = 250, Power = 150 })
for _, id in { "Pastarello", "Bananello", "Pizzarotto", "Espressino" } do
	Economy.Discover(player, id)
end
Economy.Add(player, { Boosts = { Power = 300 } })
Economy.Reward(player, { Stat = "Power", Amount = 8, Item = "Espressino", New = true })
advance(0.4)
snap("hud")
check("rebirth badge when ready", find("HudLeft/Buttons/Rebirth/Badge").Visible)
check("power multiplier with boost", Economy.Multiplier(player, "Power") == 2)
check("earn applies multiplier", Economy.Earn(player, "Power", 5) == 10)

-- shop ------------------------------------------------------------------------
click("HudLeft/Buttons/Shop")
advance(0.6)
check("shop open", find("Windows/Shop").Visible)
snap("shop")
find("Windows/Shop/Body/List").CanvasPosition = Vector2.new(0, 440)
snap("shop_scrolled")
find("Windows/Shop/Body/List").CanvasPosition = Vector2.new(0, 0)
click("Windows/Shop/Body/List/Boosts/BoostPower/Buy")
advance(0.3)
check("unconfigured product not prompted", #PROMPTS == 0)
click("Windows/Shop/Close")
advance(0.6)
check("shop closed", not find("Windows/Shop").Visible)

-- purchases through ProcessReceipt ----------------------------------------------
local MarketplaceService = game:GetService("MarketplaceService")
local coinsProduct = Rules.ProductByKey.Coins2
coinsProduct.Id = 555
Rules.ProductById[555] = coinsProduct
local coinsBefore = player:GetAttribute("Coins")
local decision = MarketplaceService.ProcessReceipt({ PlayerId = 1001, ProductId = 555, PurchaseId = "receipt-1" })
check("receipt granted", decision == Enum.ProductPurchaseDecision.PurchaseGranted)
local decision2 = MarketplaceService.ProcessReceipt({ PlayerId = 1001, ProductId = 555, PurchaseId = "receipt-1" })
check("receipt retry granted once", decision2 == Enum.ProductPurchaseDecision.PurchaseGranted and player:GetAttribute("Coins") == coinsBefore + 50000, player:GetAttribute("Coins") - coinsBefore)
check("receipt saved", DATASTORE["player_1001"].Receipts["receipt-1"] == true)
local unknown = MarketplaceService.ProcessReceipt({ PlayerId = 1001, ProductId = 999, PurchaseId = "receipt-2" })
check("unknown product not granted", unknown == Enum.ProductPurchaseDecision.NotProcessedYet)
advance(3)

-- rebirth -----------------------------------------------------------------------
click("HudLeft/Buttons/Rebirth")
advance(0.6)
snap("rebirth")
local gemsBefore = player:GetAttribute("Gems")
click("Windows/Rebirth/Body/Rebirth")
advance(0.5)
check("rebirth applied", player:GetAttribute("Rebirths") == 1 and player:GetAttribute("Power") == 0 and player:GetAttribute("Coins") == 0)
check("rebirth gems", player:GetAttribute("Gems") == gemsBefore + 15, player:GetAttribute("Gems") - gemsBefore)
snap("rebirth_done")
advance(3)
check("rebirth refused without power", Economy.Rebirth(player, false).ok == false)

-- index ---------------------------------------------------------------------------
click("HudLeft/Buttons/Index")
advance(0.6)
snap("index")
Economy.Discover(player, "Pagnotto")
advance(0.2)
check("common series complete → claimable", find("Windows/Index/Body/Tabs/Common/Badge").Visible)
local gemsBeforeClaim = player:GetAttribute("Gems")
click("Windows/Index/Body/Header/Claim")
advance(0.3)
check("index claim gives gems", player:GetAttribute("Gems") == gemsBeforeClaim + 25, player:GetAttribute("Gems") - gemsBeforeClaim)
advance(0.7)
check("claim is one-time", Economy.ClaimIndex(player, "Common").ok == false)
check("claim validates rarity", Economy.ClaimIndex(player, "Nope").ok == false and Economy.ClaimIndex(player, 12).ok == false)
advance(3)
click("Windows/Index/Body/Tabs/Rare")
advance(0.4)
snap("index_rare")
click("Windows/Index/Close")
advance(0.6)

-- wheel -----------------------------------------------------------------------------
click("HudLeft/Buttons/Wheel")
advance(0.6)
snap("wheel")
local spinsBefore = player:GetAttribute("Spins")
local freeBefore = player:GetAttribute("FreeSpinAt")
click("Windows/Wheel/Body/Side/Spin")
check("free spin used first", player:GetAttribute("Spins") == spinsBefore and player:GetAttribute("FreeSpinAt") > freeBefore)
advance(1.4)
snap("wheel_spinning")
advance(3.2)
snap("wheel_won")
advance(3)
click("Windows/Wheel/Body/Side/Spin")
check("bought spin used next", player:GetAttribute("Spins") == spinsBefore - 1)
advance(5)
local result = Economy.Spin(player)
check("no spin left refused", result.ok == false, result.message)
advance(3)
click("Windows/Wheel/Close")
advance(0.6)

-- wheel painting: the colour under every angle must be the sector that owns it
local Wheel = requireModule(clientScript.Wheel)
local holder = Instance.new("Frame")
local wheel = Wheel.new({ Parent = holder, Diameter = 400, Rewards = Config.Wheel.Rewards })
local mismatches, samples = 0, 0
local rngAngles = Random.new(3)
for _ = 1, 300 do
	local angle = rngAngles:NextNumber(0, 360)
	wheel:SetAngle(angle)
	for theta = 0.25, 359.75, 0.5 do
		local rel = (theta - angle) % 360
		local nearBoundary = math.abs(rel / wheel.width - math.floor(rel / wheel.width + 0.5)) * wheel.width < 0.3
		if not nearBoundary then
			local half = if theta < 180 then wheel.halves[1] else wheel.halves[2]
			local color
			for _, disk in half.disks do
				if disk.Visible and ((theta - disk.Rotation) % 360) < 180 then
					color = disk.BackgroundColor3
				end
			end
			local expected = wheel.colors[math.floor(rel / wheel.width) % wheel.count + 1]
			samples += 1
			if color ~= expected then
				mismatches += 1
			end
		end
	end
end
check("wheel painting exact", mismatches == 0, mismatches .. " / " .. samples)
wheel:SetAngle(123.4)
check("sector at pointer", wheel:SectorAtPointer() == math.floor(((-123.4) % 360) / wheel.width) + 1)

-- phone ----------------------------------------------------------------------------------
setViewport(Vector2.new(844, 390))
TOP_INSET = 36
screenGui:GetPropertyChangedSignal("AbsoluteSize"):Fire()
advance(0.3)
snap("phone_hud")
click("HudLeft/Buttons/Shop")
advance(0.6)
snap("phone_shop")
click("Windows/Shop/Close")
advance(0.6)
click("HudLeft/Buttons/Wheel")
advance(0.6)
snap("phone_wheel")
click("Windows/Wheel/Close")
advance(0.6)

-- save on shutdown ------------------------------------------------------------------------
for _, fn in BIND_TO_CLOSE do
	task.spawn(fn)
end
advance(1)
local record = DATASTORE["player_1001"]
check("saved on close", record ~= nil and record.Rebirths == 1 and record.Index.Pagnotto == 1)
check("lock released", record.Lock == nil)

-- a record locked by another live server is never overwritten
DATASTORE["player_2002"] = { Coins = 77, Lock = { JobId = "other-server", Time = math.floor(1790000000 + virtualNow()) } }
local other = makePlayer(2002, "Other")
other.Parent = Players
Players.PlayerAdded:Fire(other)
advance(2)
check("locked profile not loaded yet", other:GetAttribute("DataReady") == nil and DATASTORE["player_2002"].Coins == 77)

check("no script errors", #ERRORS == 0, #ERRORS)
print(("CHECKS passed=%d failed=%d"):format(passed, failed))
