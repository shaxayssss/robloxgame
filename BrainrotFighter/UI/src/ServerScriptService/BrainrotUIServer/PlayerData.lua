-- PlayerData: loads, caches, replicates and saves player profiles.
--
-- * One DataStore key per player, always written with UpdateAsync.
-- * A light session lock stops two servers from writing the same profile
--   (a player who rejoins fast, a teleport): a record locked by another live
--   server is never overwritten.
-- * Retries with backoff, autosave, save on leave and on shutdown.
-- * A profile that could not be loaded is never saved (no wipe with defaults).
-- * In Studio without API access, profiles live for the session only.
--
-- The rest of the server mutates the table returned by PlayerData.Get, then calls
-- PlayerData.Replicate so attributes and leaderstats follow.

local Players = game:GetService("Players")
local DataStoreService = game:GetService("DataStoreService")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))

local PlayerData = {}

local KEY_PREFIX = "player_"
local LOCK_TIMEOUT = 150 -- a lock older than this belongs to a dead server
local LOAD_ATTEMPTS = 6
local SAVE_ATTEMPTS = 3
local MAX_RECEIPTS = 50
local SHUTDOWN_TIMEOUT = 25

type Profile = {
	data: { [string]: any },
	persistent: boolean,
	saving: boolean,
	releasing: boolean,
}

local store: DataStore? = nil
local profiles: { [Player]: Profile } = {}
local loadedEvent = Instance.new("BindableEvent")

-- Fired with the player once their profile is ready.
PlayerData.Loaded = loadedEvent.Event

local function defaultData(): { [string]: any }
	local data = {
		Index = {},
		IndexClaimed = {},
		Boosts = {},
		PassRewards = {},
		Receipts = {},
		ReceiptOrder = {},
		FreeSpinAt = 0,
	}
	for key, value in Config.StartingData do
		data[key] = value
	end
	return data
end

-- Fills fields added in later versions, keeps everything else.
local function reconcile(record: any): { [string]: any }
	local data = if type(record) == "table" then record else {}
	for key, value in defaultData() do
		if data[key] == nil then
			data[key] = value
		end
	end
	data.Lock = nil
	return data
end

local function isLockedElsewhere(lock: any): boolean
	return type(lock) == "table"
		and lock.JobId ~= game.JobId
		and os.time() - (tonumber(lock.Time) or 0) < LOCK_TIMEOUT
end

local function keyFor(userId: number): string
	return KEY_PREFIX .. userId
end

local function openStore()
	local ok, result = pcall(function()
		return DataStoreService:GetDataStore(Config.Data.StoreName)
	end)
	if not ok then
		warn("[BrainrotUI] DataStore unavailable, progress is kept for this session only: " .. tostring(result))
		return
	end
	if RunService:IsStudio() then
		local probeOk, probeError = pcall(function()
			return result:GetAsync("__probe")
		end)
		if not probeOk then
			warn(
				"[BrainrotUI] Studio cannot reach DataStores (Game Settings > Security > Enable Studio Access to API Services). "
					.. "Progress is kept for this session only. "
					.. tostring(probeError)
			)
			return
		end
	end
	store = result
end

-- Returns (data, persistent) or nil when the profile cannot be loaded safely.
local function loadAsync(player: Player): ({ [string]: any }?, boolean)
	local dataStore = store
	if not dataStore then
		return defaultData(), false
	end
	local key = keyFor(player.UserId)
	for attempt = 1, LOAD_ATTEMPTS do
		local lockedElsewhere = false
		local ok, result = pcall(function()
			return dataStore:UpdateAsync(key, function(old)
				if type(old) == "table" and isLockedElsewhere(old.Lock) then
					lockedElsewhere = true
					return nil -- leave the record untouched
				end
				local record = if type(old) == "table" then old else defaultData()
				record.Lock = { JobId = game.JobId, Time = os.time() }
				return record
			end)
		end)
		if ok and not lockedElsewhere then
			return reconcile(result), true
		end
		if not ok then
			warn(("[BrainrotUI] Load attempt %d failed for %s: %s"):format(attempt, player.Name, tostring(result)))
		end
		if player.Parent ~= Players then
			return nil, false
		end
		task.wait(if lockedElsewhere then 5 else math.min(2 ^ attempt, 10))
	end
	return nil, false
end

-- One UpdateAsync write. Never overwrites a record another live server holds.
local function writeAsync(userId: number, data: { [string]: any }, release: boolean): boolean
	local dataStore = store
	if not dataStore then
		return true
	end
	local snapshot = table.clone(data)
	snapshot.Lock = if release then nil else { JobId = game.JobId, Time = os.time() }
	local stolen = false
	local ok, err = pcall(function()
		dataStore:UpdateAsync(keyFor(userId), function(old)
			if type(old) == "table" and isLockedElsewhere(old.Lock) then
				stolen = true
				return nil
			end
			return snapshot
		end)
	end)
	if stolen then
		warn(("[BrainrotUI] Profile %d is held by another server, save skipped"):format(userId))
		return false
	end
	if not ok then
		warn(("[BrainrotUI] Save failed for %d: %s"):format(userId, tostring(err)))
	end
	return ok
end

local function setAttribute(player: Player, name: string, value: any)
	if player:GetAttribute(name) ~= value then
		player:SetAttribute(name, value)
	end
end

local function setupLeaderstats(player: Player)
	local folder = player:FindFirstChild("leaderstats")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "leaderstats"
		folder.Parent = player
	end
	for _, stat in Config.Leaderstats do
		if not folder:FindFirstChild(stat.Name) then
			local value = Instance.new("IntValue")
			value.Name = stat.Name
			value.Parent = folder
		end
	end
end

-- Pushes the profile to player attributes (read by the client) and leaderstats.
function PlayerData.Replicate(player: Player)
	local profile = profiles[player]
	if not profile then
		return
	end
	local data = profile.data
	for _, key in { "Coins", "Gems", "Power", "Rebirths", "Spins", "FreeSpinAt" } do
		setAttribute(player, key, data[key] or 0)
	end
	for name in Config.Boosts do
		setAttribute(player, "Boost_" .. name, data.Boosts[name] or 0)
	end
	for _, item in Config.Index do
		setAttribute(player, "Idx_" .. item.Id, data.Index[item.Id] or 0)
	end
	for _, rarity in Config.Rarities do
		setAttribute(player, "Claim_" .. rarity.Key, data.IndexClaimed[rarity.Key] == true)
	end
	local folder = player:FindFirstChild("leaderstats")
	if folder then
		for _, stat in Config.Leaderstats do
			local value = folder:FindFirstChild(stat.Name)
			if value and value:IsA("IntValue") then
				value.Value = math.floor(data[stat.Key] or 0)
			end
		end
	end
end

-- The live profile table, or nil while loading / after leaving.
function PlayerData.Get(player: Player): { [string]: any }?
	local profile = profiles[player]
	return if profile then profile.data else nil
end

-- Waits for the profile (used by ProcessReceipt, which can run before loading ends).
function PlayerData.WaitForData(player: Player, timeout: number): { [string]: any }?
	local deadline = os.clock() + timeout
	while not profiles[player] and player.Parent == Players and os.clock() < deadline do
		task.wait(0.25)
	end
	return PlayerData.Get(player)
end

-- Remembers a processed purchase so a retried receipt is never granted twice.
function PlayerData.RecordReceipt(player: Player, purchaseId: string)
	local data = PlayerData.Get(player)
	if not data then
		return
	end
	data.Receipts[purchaseId] = true
	table.insert(data.ReceiptOrder, purchaseId)
	while #data.ReceiptOrder > MAX_RECEIPTS do
		local oldest = table.remove(data.ReceiptOrder, 1)
		data.Receipts[oldest] = nil
	end
end

-- Saves now. Returns true when the profile is safely stored (or session-only).
function PlayerData.SaveAsync(player: Player, release: boolean?): boolean
	local profile = profiles[player]
	if not profile then
		return false
	end
	if not profile.persistent then
		return true
	end
	while profile.saving do
		task.wait(0.1)
	end
	profile.saving = true
	local ok = false
	for attempt = 1, SAVE_ATTEMPTS do
		ok = writeAsync(player.UserId, profile.data, release == true)
		if ok then
			break
		end
		task.wait(attempt)
	end
	profile.saving = false
	return ok
end

-- Final save + lock release, then forget the profile. Safe to call twice.
local function releaseAsync(player: Player)
	local profile = profiles[player]
	if not profile or profile.releasing then
		return
	end
	profile.releasing = true
	PlayerData.SaveAsync(player, true)
	profiles[player] = nil
end

local function onPlayerAdded(player: Player)
	local data, persistent = loadAsync(player)
	if player.Parent ~= Players then
		-- left while loading: give the lock back
		if data and persistent then
			writeAsync(player.UserId, data, true)
		end
		return
	end
	if not data then
		player:Kick(Config.Text.DataLoadFailed)
		return
	end
	profiles[player] = { data = data, persistent = persistent, saving = false, releasing = false }
	setupLeaderstats(player)
	PlayerData.Replicate(player)
	player:SetAttribute("DataSaved", persistent)
	player:SetAttribute("DataReady", true)
	loadedEvent:Fire(player)
end

local function startAutosave()
	local elapsed = 0
	RunService.Heartbeat:Connect(function(dt)
		elapsed += dt
		if elapsed < Config.Data.AutosaveInterval then
			return
		end
		elapsed = 0
		for player, profile in profiles do
			if profile.persistent and not profile.saving and not profile.releasing then
				task.spawn(PlayerData.SaveAsync, player, false)
			end
		end
	end)
end

function PlayerData.Start()
	openStore()
	Players.PlayerAdded:Connect(onPlayerAdded)
	Players.PlayerRemoving:Connect(releaseAsync)
	for _, player in Players:GetPlayers() do
		task.spawn(onPlayerAdded, player)
	end
	startAutosave()
	game:BindToClose(function()
		for player in profiles do
			task.spawn(releaseAsync, player)
		end
		local deadline = os.clock() + SHUTDOWN_TIMEOUT
		while next(profiles) ~= nil and os.clock() < deadline do
			task.wait(0.2)
		end
	end)
end

return PlayerData
