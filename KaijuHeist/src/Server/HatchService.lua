-- Handles turning a collected capsule into a kaiju via a weighted rarity roll.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local KaijuDatabase = require(ReplicatedStorage.Shared.KaijuDatabase)
local PlayerDataService = require(script.Parent.PlayerDataService)

local HatchService = {}

local rng = Random.new()

function HatchService.Start(remotes)
	remotes.RequestHatch.OnServerInvoke = function(player)
		local profile = PlayerDataService.Get(player)
		if not profile then
			return { ok = false, reason = "No profile loaded yet." }
		end

		if profile.Capsules < 1 then
			return { ok = false, reason = "You have no capsules to hatch." }
		end

		profile.Capsules -= 1
		local kaijuDef = KaijuDatabase.RollRandomKaiju(rng)
		PlayerDataService.AddKaiju(player.UserId, kaijuDef.id, 1)

		return {
			ok = true,
			kaijuId = kaijuDef.id,
			kaijuName = kaijuDef.name,
			rarity = kaijuDef.rarity,
			remainingCapsules = profile.Capsules,
		}
	end
end

return HatchService
