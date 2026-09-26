-- Kaiju definitions: id, display name, rarity tier, roll weight, passive income per tick, placeholder color.
-- Swap `color` for a real model/mesh id once art is ready; everything else keys off `id`.
local KaijuDatabase = {}

KaijuDatabase.Rarities = {
	Common = { weight = 60, color = Color3.fromRGB(150, 150, 150) },
	Rare = { weight = 25, color = Color3.fromRGB(70, 140, 255) },
	Epic = { weight = 11, color = Color3.fromRGB(170, 70, 255) },
	Legendary = { weight = 3.5, color = Color3.fromRGB(255, 170, 30) },
	Mythic = { weight = 0.5, color = Color3.fromRGB(255, 60, 90) },
}

KaijuDatabase.Kaijus = {
	{ id = "sludgling", name = "Sludgling", rarity = "Common", incomePerTick = 2 },
	{ id = "cindercrab", name = "Cindercrab", rarity = "Common", incomePerTick = 2 },
	{ id = "mossbite", name = "Mossbite", rarity = "Common", incomePerTick = 3 },
	{ id = "voltoad", name = "Voltoad", rarity = "Rare", incomePerTick = 6 },
	{ id = "gloomhorn", name = "Gloomhorn", rarity = "Rare", incomePerTick = 7 },
	{ id = "shardfang", name = "Shardfang", rarity = "Epic", incomePerTick = 16 },
	{ id = "tidalmaw", name = "Tidalmaw", rarity = "Epic", incomePerTick = 18 },
	{ id = "duskcolossus", name = "Duskcolossus", rarity = "Legendary", incomePerTick = 45 },
	{ id = "starwyrm", name = "Starwyrm", rarity = "Mythic", incomePerTick = 120 },
}

local kaijuById = {}
for _, def in ipairs(KaijuDatabase.Kaijus) do
	kaijuById[def.id] = def
end

function KaijuDatabase.GetById(id)
	return kaijuById[id]
end

-- Weighted random roll across all kaijus, weighted by rarity.
function KaijuDatabase.RollRandomKaiju(randomObj)
	local rng = randomObj or Random.new()

	local totalWeight = 0
	for _, def in ipairs(KaijuDatabase.Kaijus) do
		totalWeight += KaijuDatabase.Rarities[def.rarity].weight
	end

	local roll = rng:NextNumber() * totalWeight
	local cumulative = 0
	for _, def in ipairs(KaijuDatabase.Kaijus) do
		cumulative += KaijuDatabase.Rarities[def.rarity].weight
		if roll <= cumulative then
			return def
		end
	end

	return KaijuDatabase.Kaijus[1]
end

return KaijuDatabase
