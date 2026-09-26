-- Central place that both server and client require to get consistent RemoteEvent/RemoteFunction
-- instances. The server calls EnsureCreated() once at boot; the client just calls Get().
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = {}

local EVENT_NAMES = {
	"CapsuleCollected", -- server -> client, capsule pickup feedback
	"KaijuHatched", -- server -> client, hatch reveal payload
	"IncomeUpdated", -- server -> client, {ichor, incomePerTick}
	"StealResult", -- server -> client (both attacker & victim), steal outcome
	"UpgradeResult", -- server -> client, base/guard upgrade confirmation
	"ProfileReady", -- server -> client, initial profile snapshot on join
}

local FUNCTION_NAMES = {
	"RequestHatch",
	"RequestSteal",
	"RequestUpgrade",
	"GetNearbyTargets", -- returns list of other online players + rough ichor tier
}

function Remotes.EnsureCreated()
	local folder = ReplicatedStorage:FindFirstChild("Remotes")
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = "Remotes"
		folder.Parent = ReplicatedStorage
	end

	for _, name in ipairs(EVENT_NAMES) do
		if not folder:FindFirstChild(name) then
			local event = Instance.new("RemoteEvent")
			event.Name = name
			event.Parent = folder
		end
	end

	for _, name in ipairs(FUNCTION_NAMES) do
		if not folder:FindFirstChild(name) then
			local func = Instance.new("RemoteFunction")
			func.Name = name
			func.Parent = folder
		end
	end

	return folder
end

function Remotes.Get()
	local folder = ReplicatedStorage:WaitForChild("Remotes")
	local proxy = {}
	for _, name in ipairs(EVENT_NAMES) do
		proxy[name] = folder:WaitForChild(name)
	end
	for _, name in ipairs(FUNCTION_NAMES) do
		proxy[name] = folder:WaitForChild(name)
	end
	return proxy
end

return Remotes
