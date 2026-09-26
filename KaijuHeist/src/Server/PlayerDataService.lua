-- Owns the in-memory profile cache + DataStore persistence for every online player.
-- Every other server service reads/writes profiles exclusively through this module
-- so there is a single source of truth and a single place that talks to the DataStore.
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")

local Constants = require(game:GetService("ReplicatedStorage").Shared.Constants)

local PlayerDataService = {}

local store = DataStoreService:GetDataStore(Constants.DATASTORE_NAME)
local profiles = {} -- [userId] = profile table
local profileLocks = {} -- [userId] = true while a save is in flight

local function defaultProfile()
	return {
		Ichor = 0,
		Capsules = 0,
		Kaijus = {}, -- [kaijuId] = count
		BaseLevel = 1,
		GuardLevel = 0,
		StealCooldowns = {}, -- [targetUserId] = os.time() of last attempt
	}
end

function PlayerDataService.Load(player)
	local userId = player.UserId
	local success, data = pcall(function()
		return store:GetAsync("Player_" .. userId)
	end)

	if success and data then
		profiles[userId] = data
	else
		if not success then
			warn(("KaijuHeist: failed to load data for %s (%d): %s"):format(player.Name, userId, tostring(data)))
		end
		profiles[userId] = defaultProfile()
	end

	return profiles[userId]
end

function PlayerDataService.Get(userIdOrPlayer)
	local userId = typeof(userIdOrPlayer) == "Instance" and userIdOrPlayer.UserId or userIdOrPlayer
	return profiles[userId]
end

function PlayerDataService.Save(player)
	local userId = player.UserId
	local profile = profiles[userId]
	if not profile or profileLocks[userId] then
		return
	end

	profileLocks[userId] = true
	local success, err = pcall(function()
		store:SetAsync("Player_" .. userId, profile)
	end)
	profileLocks[userId] = false

	if not success then
		warn(("KaijuHeist: failed to save data for %s (%d): %s"):format(player.Name, userId, tostring(err)))
	end
end

function PlayerDataService.Release(player)
	profiles[player.UserId] = nil
end

function PlayerDataService.AddKaiju(userId, kaijuId, count)
	local profile = profiles[userId]
	if not profile then
		return
	end
	profile.Kaijus[kaijuId] = (profile.Kaijus[kaijuId] or 0) + (count or 1)
end

function PlayerDataService.GetOnlineProfiles()
	local list = {}
	for _, player in ipairs(Players:GetPlayers()) do
		local profile = profiles[player.UserId]
		if profile then
			list[player] = profile
		end
	end
	return list
end

-- Autosave loop; call once from Main.server.lua
function PlayerDataService.StartAutosave()
	task.spawn(function()
		while true do
			task.wait(Constants.AUTOSAVE_INTERVAL_SECONDS)
			for _, player in ipairs(Players:GetPlayers()) do
				PlayerDataService.Save(player)
			end
		end
	end)
end

return PlayerDataService
