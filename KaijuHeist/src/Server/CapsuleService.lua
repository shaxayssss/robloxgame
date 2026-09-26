-- Spawns collectible capsule parts around the map and grants +1 capsule to whoever
-- touches one first. Purely world/physics side; ignorant of hatching or economy.
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Debris = game:GetService("Debris")

local Constants = require(ReplicatedStorage.Shared.Constants)
local PlayerDataService = require(script.Parent.PlayerDataService)

local CapsuleService = {}

local remotes
local capsuleFolder
local liveCapsuleCount = 0

local function makeCapsulePart()
	local part = Instance.new("Part")
	part.Name = "Capsule"
	part.Shape = Enum.PartType.Ball
	part.Size = Vector3.new(2, 2, 2)
	part.Material = Enum.Material.Neon
	part.Color = Color3.fromRGB(255, 215, 0)
	part.Anchored = true
	part.CanCollide = false
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth

	local light = Instance.new("PointLight")
	light.Color = part.Color
	light.Brightness = 2
	light.Range = 8
	light.Parent = part

	return part
end

local function randomSpawnPosition()
	local radius = Constants.CAPSULE_SPAWN_RADIUS
	local angle = math.random() * math.pi * 2
	local dist = math.sqrt(math.random()) * radius
	local x = math.cos(angle) * dist
	local z = math.sin(angle) * dist
	return Vector3.new(x, 4, z)
end

local function onCapsuleTouched(part, hit)
	if not part or not part.Parent then
		return
	end
	local character = hit.Parent
	local Players = game:GetService("Players")
	local hitPlayer = Players:GetPlayerFromCharacter(character)
	if not hitPlayer then
		return
	end

	-- Debounce: destroy immediately so only the first touch counts.
	part.Parent = nil
	liveCapsuleCount = math.max(0, liveCapsuleCount - 1)

	local profile = PlayerDataService.Get(hitPlayer)
	if not profile then
		return
	end
	profile.Capsules += 1

	remotes.CapsuleCollected:FireClient(hitPlayer, { capsules = profile.Capsules })
end

local function spawnOneCapsule()
	if liveCapsuleCount >= Constants.CAPSULE_MAX_IN_WORLD then
		return
	end

	local part = makeCapsulePart()
	part.Position = randomSpawnPosition()
	part.Parent = capsuleFolder

	liveCapsuleCount += 1

	part.Touched:Connect(function(hit)
		onCapsuleTouched(part, hit)
	end)

	Debris:AddItem(part, Constants.CAPSULE_LIFETIME)
	task.delay(Constants.CAPSULE_LIFETIME, function()
		if part.Parent then
			liveCapsuleCount = math.max(0, liveCapsuleCount - 1)
		end
	end)
end

function CapsuleService.Start(remotesTable)
	remotes = remotesTable

	capsuleFolder = Workspace:FindFirstChild("Capsules")
	if not capsuleFolder then
		capsuleFolder = Instance.new("Folder")
		capsuleFolder.Name = "Capsules"
		capsuleFolder.Parent = Workspace
	end

	task.spawn(function()
		while true do
			task.wait(Constants.CAPSULE_SPAWN_INTERVAL)
			spawnOneCapsule()
		end
	end)
end

return CapsuleService
