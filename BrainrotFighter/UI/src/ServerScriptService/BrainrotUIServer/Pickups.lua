-- Pickups: collectible coins and power orbs in the world.
--
-- Every BasePart tagged Config.Pickups.Tag is collectible:
--   Kind   = "Coins" or "Power" (attribute, default "Power")
--   Rarity = "Common" | "Rare" | "Epic" | "Legendary" (power orbs)
--   Amount = optional base amount (else CoinAmount / the rarity OrbPower)
-- Each power orb also reveals a brainrot of its rarity in the Index.
-- With AutoSpawn, test pickups are scattered around the SpawnLocation.

local Players = game:GetService("Players")
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local PlayerData = require(script.Parent:WaitForChild("PlayerData"))
local Economy = require(script.Parent:WaitForChild("Economy"))

local Settings = Config.Pickups

local Pickups = {}

local rng = Random.new()
local COIN_COLOR = Color3.fromRGB(255, 200, 40)
local MAX_TOUCH_DISTANCE = 14

local function setVisible(part: BasePart, visible: boolean)
	part.Transparency = if visible then (tonumber(part:GetAttribute("BaseTransparency")) or 0) else 1
	part.CanTouch = visible
	for _, child in part:GetChildren() do
		if child:IsA("Light") or child:IsA("ParticleEmitter") then
			child.Enabled = visible
		end
	end
end

local function collect(player: Player, part: BasePart)
	local kind = part:GetAttribute("Kind")
	if kind == "Coins" then
		local gained = Economy.Earn(player, "Coins", part:GetAttribute("Amount") or Settings.CoinAmount)
		Economy.Reward(player, { Stat = "Coins", Amount = gained })
		return
	end
	local rarity = Rules.RarityByKey[part:GetAttribute("Rarity") or ""] or Config.Rarities[1]
	local gained = Economy.Earn(player, "Power", part:GetAttribute("Amount") or rarity.OrbPower)
	local items = Rules.ItemsByRarity[rarity.Key]
	local payload: { [string]: any } = { Stat = "Power", Amount = gained }
	if #items > 0 then
		local item = items[rng:NextInteger(1, #items)]
		payload.Item = item.Id
		payload.New = Economy.Discover(player, item.Id)
	end
	Economy.Reward(player, payload)
end

local function setup(instance: Instance)
	if not instance:IsA("BasePart") or instance:GetAttribute("BrainrotUIReady") then
		return
	end
	local part = instance :: BasePart
	part:SetAttribute("BrainrotUIReady", true)
	if part:GetAttribute("BaseTransparency") == nil then
		part:SetAttribute("BaseTransparency", part.Transparency)
	end
	part.CanTouch = true
	local busy = false
	part.Touched:Connect(function(hit)
		if busy then
			return
		end
		local character = hit:FindFirstAncestorOfClass("Model")
		local player = if character then Players:GetPlayerFromCharacter(character) else nil
		if not player or not character or not PlayerData.Get(player) then
			return
		end
		local humanoid = character:FindFirstChildOfClass("Humanoid")
		local root = character:FindFirstChild("HumanoidRootPart")
		if not humanoid or humanoid.Health <= 0 or not root or not root:IsA("BasePart") then
			return
		end
		-- the touch is reported by the player's machine: check it is plausible
		if (root.Position - part.Position).Magnitude > MAX_TOUCH_DISTANCE + part.Size.Magnitude then
			return
		end
		busy = true
		setVisible(part, false)
		collect(player, part)
		task.delay(Settings.RespawnTime, function()
			if part.Parent then
				setVisible(part, true)
			end
			busy = false
		end)
	end)
end

local function pickRarity(): { [string]: any }
	return Config.Rarities[Rules.pickWeighted(Config.Rarities, rng)]
end

local function makePickup(folder: Folder, position: Vector3, isCoin: boolean)
	local part = Instance.new("Part")
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CastShadow = false
	local color
	if isCoin then
		part.Name = "Coin"
		part.Shape = Enum.PartType.Cylinder
		part.Size = Vector3.new(0.6, 2.8, 2.8)
		part.Material = Enum.Material.SmoothPlastic
		color = COIN_COLOR
		part:SetAttribute("Kind", "Coins")
	else
		local rarity = pickRarity()
		part.Name = "PowerOrb_" .. rarity.Key
		part.Shape = Enum.PartType.Ball
		part.Size = Vector3.new(2.4, 2.4, 2.4)
		part.Material = Enum.Material.Neon
		color = rarity.Color
		part:SetAttribute("Kind", "Power")
		part:SetAttribute("Rarity", rarity.Key)
		if rarity.Order >= 3 then
			local sparkles = Instance.new("ParticleEmitter")
			sparkles.Color = ColorSequence.new(rarity.Color)
			sparkles.LightEmission = 1
			sparkles.Rate = 6
			sparkles.Lifetime = NumberRange.new(0.6, 1)
			sparkles.Speed = NumberRange.new(1.5, 3)
			sparkles.SpreadAngle = Vector2.new(180, 180)
			sparkles.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(1, 0) })
			sparkles.Parent = part
		end
	end
	part.Color = color
	part.CFrame = CFrame.new(position)
	local light = Instance.new("PointLight")
	light.Color = color
	light.Range = 8
	light.Brightness = 1.2
	light.Parent = part
	CollectionService:AddTag(part, Settings.Tag)
	part.Parent = folder
end

local function findSpawnPosition(): Vector3
	local spawnLocation = workspace:FindFirstChildWhichIsA("SpawnLocation", true)
	if spawnLocation then
		return spawnLocation.Position
	end
	return Vector3.new(0, 5, 0)
end

local function spawnTestPickups()
	local old = workspace:FindFirstChild("BrainrotUIPickups")
	if old then
		old:Destroy()
	end
	local folder = Instance.new("Folder")
	folder.Name = "BrainrotUIPickups"
	folder.Parent = workspace

	local origin = findSpawnPosition()
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { folder }
	params.IgnoreWater = false
	params.RespectCanCollide = true -- land on walkable ground, not on decor (palm leaves, clouds...)

	local placed, tries = 0, 0
	while placed < Settings.Count and tries < Settings.Count * 8 do
		tries += 1
		local angle = rng:NextNumber(0, math.pi * 2)
		local radius = rng:NextNumber(Settings.MinRadius, Settings.MaxRadius)
		local x = origin.X + math.cos(angle) * radius
		local z = origin.Z + math.sin(angle) * radius
		local hit = workspace:Raycast(Vector3.new(x, origin.Y + 80, z), Vector3.new(0, -300, 0), params)
		-- flat, dry ground, roughly at the spawn height (not on a roof or a mountain)
		if hit and hit.Normal.Y > 0.7 and hit.Material ~= Enum.Material.Water and math.abs(hit.Position.Y - origin.Y) < 40 then
			makePickup(folder, hit.Position + Vector3.new(0, 2.6, 0), rng:NextNumber() < Settings.CoinChance)
			placed += 1
		end
	end
	if placed < Settings.Count then
		warn(("[BrainrotUI] Only %d test pickups found room around the spawn"):format(placed))
	end
end

function Pickups.Start()
	CollectionService:GetInstanceAddedSignal(Settings.Tag):Connect(setup)
	for _, instance in CollectionService:GetTagged(Settings.Tag) do
		setup(instance)
	end
	if Settings.AutoSpawn then
		task.defer(spawnTestPickups)
	end
end

return Pickups
