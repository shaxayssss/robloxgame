-- State: read-only mirror of the player's data. The server writes player
-- attributes (Coins, Power, Idx_<id>...), the interface observes them here.

local Players = game:GetService("Players")

local player = Players.LocalPlayer

local State = {}

local listeners: { [string]: { (any) -> () } } = {}
local anyListeners: { (string, any) -> () } = {}

function State.get(key: string): any
	return player:GetAttribute(key)
end

function State.number(key: string): number
	return tonumber(player:GetAttribute(key)) or 0
end

-- Calls fn(value) now and every time the attribute changes.
function State.observe(key: string, fn: (any) -> ())
	local list = listeners[key]
	if not list then
		list = {}
		listeners[key] = list
	end
	table.insert(list, fn)
	fn(player:GetAttribute(key))
end

-- Calls fn(key, value) for every attribute change.
function State.onAnyChange(fn: (string, any) -> ())
	table.insert(anyListeners, fn)
end

-- Server clock (os.time on the server), synced on the client.
function State.serverNow(): number
	return workspace:GetServerTimeNow()
end

player.AttributeChanged:Connect(function(key)
	local value = player:GetAttribute(key)
	local list = listeners[key]
	if list then
		for _, fn in list do
			fn(value)
		end
	end
	for _, fn in anyListeners do
		fn(key, value)
	end
end)

return State
