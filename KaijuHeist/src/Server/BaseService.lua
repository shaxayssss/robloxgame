-- Handles the two upgrade tracks players spend Ichor on: base income multiplier
-- and guard defense chance against being stolen from.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Constants = require(ReplicatedStorage.Shared.Constants)
local PlayerDataService = require(script.Parent.PlayerDataService)

local BaseService = {}

function BaseService.Start(remotes)
	remotes.RequestUpgrade.OnServerInvoke = function(player, upgradeType)
		local profile = PlayerDataService.Get(player)
		if not profile then
			return { ok = false, reason = "No profile loaded yet." }
		end

		if upgradeType == "Base" then
			local nextLevel = profile.BaseLevel + 1
			if nextLevel > Constants.MAX_BASE_LEVEL then
				return { ok = false, reason = "Base is already at max level." }
			end

			local upgrade = Constants.BASE_UPGRADES[nextLevel]
			if profile.Ichor < upgrade.cost then
				return { ok = false, reason = "Not enough Ichor." }
			end

			profile.Ichor -= upgrade.cost
			profile.BaseLevel = nextLevel

			return { ok = true, upgradeType = "Base", newLevel = nextLevel, ichor = profile.Ichor }
		elseif upgradeType == "Guard" then
			local nextLevel = profile.GuardLevel + 1
			if nextLevel > Constants.MAX_GUARD_LEVEL then
				return { ok = false, reason = "Guard is already at max level." }
			end

			local upgrade = Constants.GUARD_UPGRADES[nextLevel]
			if profile.Ichor < upgrade.cost then
				return { ok = false, reason = "Not enough Ichor." }
			end

			profile.Ichor -= upgrade.cost
			profile.GuardLevel = nextLevel

			return { ok = true, upgradeType = "Guard", newLevel = nextLevel, ichor = profile.Ichor }
		end

		return { ok = false, reason = "Unknown upgrade type." }
	end
end

return BaseService
