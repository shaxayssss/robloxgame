-- BrainrotUI server bootstrap: creates the remotes, starts the services and
-- routes the client requests. Every request is validated and rate limited here;
-- the rules themselves live in Economy.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local PlayerData = require(script:WaitForChild("PlayerData"))
local Economy = require(script:WaitForChild("Economy"))
local Store = require(script:WaitForChild("Store"))
local Pickups = require(script:WaitForChild("Pickups"))

local Text = Config.Text

local function ensure(parent: Instance, className: string, name: string): Instance
	local existing = parent:FindFirstChild(name)
	if existing and existing.ClassName == className then
		return existing
	end
	if existing then
		existing:Destroy()
	end
	local instance = Instance.new(className)
	instance.Name = name
	instance.Parent = parent
	return instance
end

local remotes = ensure(shared, "Folder", "Remotes") :: Folder
local request = ensure(remotes, "RemoteFunction", "Request") :: RemoteFunction
ensure(remotes, "RemoteEvent", "Notify")
ensure(remotes, "RemoteEvent", "Reward")

Economy.Init(remotes)
PlayerData.Start()
Store.Start()
Pickups.Start()

-- Minimum seconds between two calls of the same action by one player.
local COOLDOWNS = {
	Spin = 0.6,
	Rebirth = 1,
	ClaimIndex = 0.5,
}

local handlers = {
	Spin = function(player: Player)
		return Economy.Spin(player)
	end,
	Rebirth = function(player: Player)
		return Economy.Rebirth(player, false)
	end,
	ClaimIndex = function(player: Player, rarityKey: any)
		return Economy.ClaimIndex(player, rarityKey)
	end,
}

local lastCalls: { [Player]: { [string]: number } } = {}

request.OnServerInvoke = function(player: Player, action: any, argument: any)
	if type(action) ~= "string" or not handlers[action] then
		return { ok = false }
	end
	local calls = lastCalls[player]
	if not calls then
		calls = {}
		lastCalls[player] = calls
	end
	local now = os.clock()
	if now - (calls[action] or 0) < COOLDOWNS[action] then
		return { ok = false, message = Text.TooFast }
	end
	calls[action] = now
	local ok, result = pcall(handlers[action], player, argument)
	if not ok then
		warn(("[BrainrotUI] %s failed for %s: %s"):format(action, player.Name, tostring(result)))
		return { ok = false, message = Text.GenericError }
	end
	return result
end

Players.PlayerRemoving:Connect(function(player)
	lastCalls[player] = nil
end)
