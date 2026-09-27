-- Economy: the game rules behind the interface. Server only, always authoritative.
--
-- Other server scripts can use it too:
--   local Economy = require(game.ServerScriptService.BrainrotUIServer.Economy)
--   Economy.Earn(player, "Power", 10)     -- gameplay gain, multipliers applied
--   Economy.Add(player, { Gems = 5 })     -- raw grant, no multiplier
--   Economy.Discover(player, "Pizzarotto") -- reveals an Index entry
--   Economy.Notify(player, "Hello!", "success")

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Format = require(shared:WaitForChild("Format"))
local PlayerData = require(script.Parent:WaitForChild("PlayerData"))

local Text = Config.Text

local Economy = {}

local rng = Random.new()
local remotes: Folder? = nil

type Result = { ok: boolean, message: string?, [string]: any }

function Economy.Init(remoteFolder: Folder)
	remotes = remoteFolder
end

-- Toast on the player's screen. kind: "info" | "success" | "error" | "reward"
function Economy.Notify(player: Player, text: string, kind: string?)
	local folder = remotes
	if folder then
		(folder:FindFirstChild("Notify") :: RemoteEvent):FireClient(player, text, kind or "info")
	end
end

-- Visual feedback for a gain (floating numbers, new Index entry, purchase popup).
function Economy.Reward(player: Player, payload: { [string]: any })
	local folder = remotes
	if folder then
		(folder:FindFirstChild("Reward") :: RemoteEvent):FireClient(player, payload)
	end
end

function Economy.BoostActive(player: Player, name: string): boolean
	local data = PlayerData.Get(player)
	return data ~= nil and (data.Boosts[name] or 0) > os.time()
end

-- Total multiplier on a stat ("Power" or "Coins"): rebirths, passes and boosts.
function Economy.Multiplier(player: Player, stat: string): number
	local data = PlayerData.Get(player)
	if not data then
		return 1
	end
	local multiplier = 1
	if stat == "Power" then
		multiplier *= Rules.rebirthMultiplier(data.Rebirths)
	end
	for _, pass in Config.GamePasses do
		local bonus = pass.Multipliers and pass.Multipliers[stat]
		if bonus and player:GetAttribute("Pass_" .. pass.Key) == true then
			multiplier *= bonus
		end
	end
	for name, boost in Config.Boosts do
		if boost.Stat == stat and Economy.BoostActive(player, name) then
			multiplier *= boost.Multiplier
		end
	end
	return multiplier
end

-- Raw grant of a reward table: Coins, Gems, Power, Spins, Boosts = { Name = seconds }.
function Economy.Add(player: Player, reward: { [string]: any }): boolean
	local data = PlayerData.Get(player)
	if not data then
		return false
	end
	for _, stat in { "Coins", "Gems", "Power", "Spins" } do
		local amount = reward[stat]
		if type(amount) == "number" then
			data[stat] = math.max(0, (data[stat] or 0) + amount)
		end
	end
	if type(reward.Boosts) == "table" then
		local now = os.time()
		for name, seconds in reward.Boosts do
			if Config.Boosts[name] and type(seconds) == "number" then
				-- stacking: a new boost extends the running one
				data.Boosts[name] = math.max(data.Boosts[name] or 0, now) + seconds
			end
		end
	end
	PlayerData.Replicate(player)
	return true
end

-- Gameplay gain with every multiplier applied. Returns the amount actually gained.
function Economy.Earn(player: Player, stat: string, base: number): number
	local gained = math.max(0, math.floor(base * Economy.Multiplier(player, stat) + 0.5))
	Economy.Add(player, { [stat] = gained })
	return gained
end

-- Adds one copy of an Index entry. Returns true the first time it is found.
function Economy.Discover(player: Player, itemId: string): boolean
	local data = PlayerData.Get(player)
	if not data or not Rules.ItemById[itemId] then
		return false
	end
	local count = (data.Index[itemId] or 0) + 1
	data.Index[itemId] = count
	PlayerData.Replicate(player)
	return count == 1
end

-- Rebirth. `ignoreRequirement` is used by the paid skip.
function Economy.Rebirth(player: Player, ignoreRequirement: boolean?): Result
	local data = PlayerData.Get(player)
	if not data then
		return { ok = false, message = Text.GenericError }
	end
	local required = Rules.rebirthRequirement(data.Rebirths)
	if not ignoreRequirement and data.Power < required then
		return { ok = false, message = Text.RebirthNotReady }
	end
	data.Rebirths += 1
	data.Power = 0
	if Config.Rebirth.ResetCoins then
		data.Coins = 0
	end
	local gems = Rules.rebirthGems(data.Rebirths)
	data.Gems += gems
	PlayerData.Replicate(player)
	return { ok = true, rebirths = data.Rebirths, gems = gems }
end

-- Wheel spin: uses the free spin first, then a bought one. The reward is drawn
-- and granted here; the client only animates towards the returned index.
function Economy.Spin(player: Player): Result
	local data = PlayerData.Get(player)
	if not data then
		return { ok = false, message = Text.GenericError }
	end
	local now = os.time()
	local free = now >= (data.FreeSpinAt or 0)
	if free then
		data.FreeSpinAt = now + Config.Wheel.FreeSpinCooldown
	elseif data.Spins > 0 then
		data.Spins -= 1
	else
		return { ok = false, message = Text.NoSpins }
	end
	local index = Rules.pickWeighted(Config.Wheel.Rewards, rng)
	Economy.Add(player, Config.Wheel.Rewards[index])
	return { ok = true, index = index, free = free }
end

-- Series reward of the Index, once every entry of a rarity has been found.
function Economy.ClaimIndex(player: Player, rarityKey: any): Result
	local rarity = if type(rarityKey) == "string" then Rules.RarityByKey[rarityKey] else nil
	local data = PlayerData.Get(player)
	if not rarity or not data then
		return { ok = false, message = Text.GenericError }
	end
	if data.IndexClaimed[rarity.Key] then
		return { ok = false, message = Text.IndexAlreadyClaimed }
	end
	for _, item in Rules.ItemsByRarity[rarity.Key] do
		if (data.Index[item.Id] or 0) == 0 then
			return { ok = false, message = Text.IndexIncomplete }
		end
	end
	data.IndexClaimed[rarity.Key] = true
	data.Gems += rarity.IndexReward
	PlayerData.Replicate(player)
	return {
		ok = true,
		gems = rarity.IndexReward,
		message = Text.IndexClaimDone:format(rarity.Label, Format.short(rarity.IndexReward)),
	}
end

return Economy
