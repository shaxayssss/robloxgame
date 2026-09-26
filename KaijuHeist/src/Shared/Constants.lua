-- Shared game balance constants. Tune these first when playtesting.
local Constants = {}

Constants.CAPSULE_SPAWN_INTERVAL = 6 -- seconds between world capsule spawns
Constants.CAPSULE_MAX_IN_WORLD = 40
Constants.CAPSULE_LIFETIME = 45 -- despawns if uncollected
-- Where capsules spawn comes from MapData.zones[i].capsuleArea (generated with the map).

Constants.INCOME_TICK_SECONDS = 5

Constants.STEAL_COOLDOWN_SECONDS = 45 -- per attacker-target pair
Constants.STEAL_BASE_SUCCESS_CHANCE = 0.65
Constants.STEAL_MIN_SUCCESS_CHANCE = 0.1
Constants.STEAL_PERCENT_TAKEN = 0.15 -- fraction of target's Ichor stolen on success
Constants.STEAL_MAX_TAKEN = 5000

Constants.AUTOSAVE_INTERVAL_SECONDS = 120

-- Base (income multiplier) upgrade: level -> {cost, multiplier}
Constants.BASE_UPGRADES = {
	[1] = { cost = 0, multiplier = 1.0 },
	[2] = { cost = 250, multiplier = 1.15 },
	[3] = { cost = 750, multiplier = 1.35 },
	[4] = { cost = 2000, multiplier = 1.6 },
	[5] = { cost = 5000, multiplier = 2.0 },
	[6] = { cost = 12000, multiplier = 2.5 },
	[7] = { cost = 30000, multiplier = 3.2 },
}

-- Guard (defense) upgrade: level -> {cost, defenseChance}
Constants.GUARD_UPGRADES = {
	[0] = { cost = 0, defenseChance = 0 },
	[1] = { cost = 300, defenseChance = 0.08 },
	[2] = { cost = 900, defenseChance = 0.16 },
	[3] = { cost = 2500, defenseChance = 0.24 },
	[4] = { cost = 6000, defenseChance = 0.32 },
	[5] = { cost = 15000, defenseChance = 0.4 },
}

Constants.MAX_BASE_LEVEL = 7
Constants.MAX_GUARD_LEVEL = 5

Constants.DATASTORE_NAME = "KaijuHeist_PlayerData_v1"

return Constants
