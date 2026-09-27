-- Rules: formulas and lookups shared by the server (authority) and the client (display),
-- so both always agree on requirements, multipliers and odds.

local Config = require(script.Parent:WaitForChild("UIConfig"))
local Format = require(script.Parent:WaitForChild("Format"))

local Rules = {}

Rules.RarityByKey = {}
Rules.ItemById = {}
Rules.ItemsByRarity = {}
Rules.CurrencyByKey = {}
Rules.PassByKey = {}
Rules.PassById = {}
Rules.ProductByKey = {}
Rules.ProductById = {}

for order, rarity in Config.Rarities do
	rarity.Order = order
	Rules.RarityByKey[rarity.Key] = rarity
	Rules.ItemsByRarity[rarity.Key] = {}
end

for _, item in Config.Index do
	Rules.ItemById[item.Id] = item
	local list = Rules.ItemsByRarity[item.Rarity]
	if list then
		table.insert(list, item)
	else
		warn(("[BrainrotUI] Index item %s has an unknown rarity %s"):format(item.Id, tostring(item.Rarity)))
	end
end

for _, currency in Config.Currencies do
	Rules.CurrencyByKey[currency.Key] = currency
end

for _, pass in Config.GamePasses do
	Rules.PassByKey[pass.Key] = pass
	if pass.Id and pass.Id > 0 then
		Rules.PassById[pass.Id] = pass
	end
end

for _, product in Config.Products do
	Rules.ProductByKey[product.Key] = product
	if product.Id and product.Id > 0 then
		Rules.ProductById[product.Id] = product
	end
end

-- Power needed for the next rebirth, when `rebirths` have already been done.
function Rules.rebirthRequirement(rebirths: number): number
	local rebirth = Config.Rebirth
	return math.floor(rebirth.BasePower * rebirth.Growth ^ rebirths + 0.5)
end

-- Permanent power multiplier given by rebirths.
function Rules.rebirthMultiplier(rebirths: number): number
	return 1 + rebirths * Config.Rebirth.MultiplierPerRebirth
end

-- Gems given by rebirth number `rebirthNumber` (1 for the first one).
function Rules.rebirthGems(rebirthNumber: number): number
	return Config.Rebirth.GemsPerRebirth * rebirthNumber
end

-- Index of an entry drawn at random according to its Weight field.
function Rules.pickWeighted(entries: { any }, rng: Random): number
	local total = 0
	for _, entry in entries do
		total += entry.Weight or 0
	end
	local roll = rng:NextNumber() * total
	for index, entry in entries do
		roll -= entry.Weight or 0
		if roll < 0 then
			return index
		end
	end
	return #entries
end

-- Chance of each wheel reward, between 0 and 1.
function Rules.wheelOdds(): { number }
	local total = 0
	for _, reward in Config.Wheel.Rewards do
		total += reward.Weight or 0
	end
	local odds = {}
	for index, reward in Config.Wheel.Rewards do
		odds[index] = if total > 0 then (reward.Weight or 0) / total else 0
	end
	return odds
end

-- Short and long descriptions of a reward table, for labels.
function Rules.describe(reward: { [string]: any }): { Icon: string, Short: string, Long: string }
	for _, key in { "Coins", "Gems", "Power" } do
		local amount = reward[key]
		if amount then
			local currency = Rules.CurrencyByKey[key]
			return {
				Icon = currency.Icon,
				Short = Format.short(amount),
				Long = Format.short(amount) .. " " .. currency.Label,
			}
		end
	end
	if reward.Spins then
		return { Icon = "🎡", Short = "+" .. reward.Spins, Long = reward.Spins .. " tours" }
	end
	if reward.Boosts then
		local name, seconds = next(reward.Boosts)
		local boost = name and Config.Boosts[name]
		if boost then
			return {
				Icon = boost.Icon,
				Short = "x" .. Format.multiplier(boost.Multiplier),
				Long = boost.Label .. " " .. Format.duration(seconds),
			}
		end
	end
	return { Icon = "🎁", Short = "?", Long = "Surprise" }
end

return Rules
