-- Core PvP loop: steal a slice of another online player's Ichor stash.
-- Success chance is attacker-neutral (no attacker "power" stat yet, kept simple)
-- minus the target's guard defense chance, clamped to a sane floor so a maxed
-- guard never makes a base fully un-stealable.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Constants = require(ReplicatedStorage.Shared.Constants)
local PlayerDataService = require(script.Parent.PlayerDataService)

local StealService = {}

local rng = Random.new()

local function getDefenseChance(profile)
	local guard = Constants.GUARD_UPGRADES[profile.GuardLevel] or Constants.GUARD_UPGRADES[0]
	return guard.defenseChance
end

function StealService.Start(remotes)
	remotes.GetNearbyTargets.OnServerInvoke = function(player)
		local results = {}
		for _, other in ipairs(Players:GetPlayers()) do
			if other ~= player then
				local profile = PlayerDataService.Get(other)
				if profile then
					local tier = "Low"
					if profile.Ichor > 5000 then
						tier = "High"
					elseif profile.Ichor > 500 then
						tier = "Medium"
					end
					table.insert(results, { userId = other.UserId, name = other.Name, tier = tier })
				end
			end
		end
		return results
	end

	remotes.RequestSteal.OnServerInvoke = function(player, targetUserId)
		local attackerProfile = PlayerDataService.Get(player)
		if not attackerProfile then
			return { ok = false, reason = "No profile loaded yet." }
		end

		local targetPlayer = Players:GetPlayerByUserId(targetUserId)
		if not targetPlayer or targetPlayer == player then
			return { ok = false, reason = "Target is not available." }
		end

		local targetProfile = PlayerDataService.Get(targetPlayer)
		if not targetProfile then
			return { ok = false, reason = "Target has no profile loaded." }
		end

		local lastAttempt = attackerProfile.StealCooldowns[tostring(targetUserId)]
		local now = os.time()
		if lastAttempt and (now - lastAttempt) < Constants.STEAL_COOLDOWN_SECONDS then
			local remaining = Constants.STEAL_COOLDOWN_SECONDS - (now - lastAttempt)
			return { ok = false, reason = ("On cooldown for %ds."):format(remaining) }
		end

		attackerProfile.StealCooldowns[tostring(targetUserId)] = now

		if targetProfile.Ichor <= 0 then
			return { ok = false, reason = "Target has nothing worth stealing." }
		end

		local successChance = math.max(
			Constants.STEAL_MIN_SUCCESS_CHANCE,
			Constants.STEAL_BASE_SUCCESS_CHANCE - getDefenseChance(targetProfile)
		)

		local success = rng:NextNumber() <= successChance

		if not success then
			remotes.StealResult:FireClient(player, { ok = true, success = false, targetName = targetPlayer.Name })
			remotes.StealResult:FireClient(targetPlayer, {
				ok = true,
				success = false,
				wasVictim = true,
				attackerName = player.Name,
			})
			return { ok = true, success = false }
		end

		local amount = math.min(targetProfile.Ichor * Constants.STEAL_PERCENT_TAKEN, Constants.STEAL_MAX_TAKEN)
		targetProfile.Ichor -= amount
		attackerProfile.Ichor += amount

		remotes.StealResult:FireClient(player, {
			ok = true,
			success = true,
			amount = amount,
			targetName = targetPlayer.Name,
		})
		remotes.StealResult:FireClient(targetPlayer, {
			ok = true,
			success = true,
			wasVictim = true,
			amount = amount,
			attackerName = player.Name,
		})

		return { ok = true, success = true, amount = amount }
	end
end

return StealService
