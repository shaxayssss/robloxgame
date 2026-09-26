-- Every INCOME_TICK_SECONDS, pays every online player passive Ichor based on the
-- kaijus they own, scaled by their base upgrade multiplier.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Constants = require(ReplicatedStorage.Shared.Constants)
local KaijuDatabase = require(ReplicatedStorage.Shared.KaijuDatabase)
local PlayerDataService = require(script.Parent.PlayerDataService)

local IncomeService = {}

local function computeIncomePerTick(profile)
	local total = 0
	for kaijuId, count in pairs(profile.Kaijus) do
		local def = KaijuDatabase.GetById(kaijuId)
		if def then
			total += def.incomePerTick * count
		end
	end

	local upgrade = Constants.BASE_UPGRADES[profile.BaseLevel] or Constants.BASE_UPGRADES[1]
	return total * upgrade.multiplier
end

function IncomeService.Start(remotes)
	task.spawn(function()
		while true do
			task.wait(Constants.INCOME_TICK_SECONDS)

			for player, profile in pairs(PlayerDataService.GetOnlineProfiles()) do
				local income = computeIncomePerTick(profile)
				if income > 0 then
					profile.Ichor += income
					remotes.IncomeUpdated:FireClient(player, {
						ichor = profile.Ichor,
						incomePerTick = income,
					})
				end
			end
		end
	end)
end

IncomeService.ComputeIncomePerTick = computeIncomePerTick

return IncomeService
