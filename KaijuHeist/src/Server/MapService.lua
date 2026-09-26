-- Makes the Blender map playable once kaiju_heist_map.glb has been imported into
-- Studio with the 3D Importer. At server start it:
--   1. finds every imported copy of the map through the REF_* markers baked into
--      the GLB, and moves / scales / rotates it back onto the world origin, so
--      MapData positions are right wherever the importer dropped the model;
--   2. gives each MeshPart its Roblox colour and material from the "__<key>"
--      suffix of its name (MapData.materials) and turns it into a pure visual;
--   3. builds the invisible collision volumes listed in MapColliders;
--   4. creates the lobby SpawnLocations and the portal triggers.
local Players = game:GetService("Players")
local PhysicsService = game:GetService("PhysicsService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local MapData = require(ReplicatedStorage.Shared.MapData)
local MapColliders = require(script.Parent.MapColliders)

local MapService = {}

-- Visual meshes go in this group, which collides with nothing. They keep
-- CanCollide on so the default camera still treats them as walls to avoid.
local VISUAL_GROUP = "MapVisual"
local PORTAL_COOLDOWN = 2 -- seconds between two teleports of the same player
local TELEPORT_HEIGHT = 3.5 -- studs above the ground anchor

local plotProvider = nil -- module exposing GetPlot(player), injected by Start
local lastTeleport = {} -- [Player] = os.clock() of the last teleport
local rng = Random.new()

local function hasPrefix(name, prefix)
	return string.sub(name, 1, #prefix) == prefix
end

-- "Zone2_Lave__lava_glow" -> "lava_glow"; "Plot_N1__wood__c2" -> "wood".
local function materialKey(name)
	return string.match(name, "__([%w_]-)__c%d+$") or string.match(name, "__([%w_]+)$")
end

local function toMaterial(name)
	local ok, material = pcall(function()
		return Enum.Material[name]
	end)
	return ok and material or nil
end

local function findMarker(root, prefix)
	for _, descendant in ipairs(root:GetDescendants()) do
		if descendant:IsA("BasePart") and hasPrefix(descendant.Name, prefix) then
			return descendant
		end
	end
	return nil
end

-- Every imported copy of the map (or of one of its sections): the outermost
-- Model holding a REF_Origin marker.
local function findImportedMaps()
	local maps, seen = {}, {}
	for _, descendant in ipairs(Workspace:GetDescendants()) do
		if descendant:IsA("BasePart") and hasPrefix(descendant.Name, "REF_Origin") then
			local model = descendant:FindFirstAncestorOfClass("Model")
			while model and model.Parent and model.Parent:IsA("Model") do
				model = model.Parent
			end
			if model and not seen[model] then
				seen[model] = true
				table.insert(maps, model)
			end
		end
	end
	return maps
end

local function markerPositions(model)
	local origin = findMarker(model, "REF_Origin")
	local axisX = findMarker(model, "REF_AxisX")
	local axisY = findMarker(model, "REF_AxisY")
	if not (origin and axisX and axisY) then
		return nil
	end
	return origin.Position, axisX.Position, axisY.Position
end

-- Orthonormal frame spanned by the three markers.
local function markerFrame(origin, axisXPoint, axisYPoint)
	local xAxis = (axisXPoint - origin).Unit
	local yAxis = axisYPoint - origin
	yAxis = (yAxis - xAxis * yAxis:Dot(xAxis)).Unit
	return CFrame.fromMatrix(origin, xAxis, yAxis)
end

local function alignMap(model)
	local ref = MapData.reference
	local origin, axisX, axisY = markerPositions(model)
	if not origin then
		warn(("MapService: %s lacks a REF marker, left where it is"):format(model:GetFullName()))
		return
	end

	-- Scale first: the importer may have converted units on the way in.
	local scale = (axisX - origin).Magnitude / (ref.axisX - ref.origin).Magnitude
	if math.abs(scale - 1) > 0.001 then
		model:ScaleTo(model:GetScale() / scale)
		origin, axisX, axisY = markerPositions(model)
	end

	-- Then one rigid move taking the measured marker frame onto the expected one.
	local measured = markerFrame(origin, axisX, axisY)
	local expected = markerFrame(ref.origin, ref.axisX, ref.axisY)
	model:PivotTo(expected * measured:Inverse() * model:GetPivot())

	local residual = (markerPositions(model) - ref.origin).Magnitude
	print(("MapService: aligned %s (moved %.1f studs, scale x%.3f, residual %.3f)"):format(
		model:GetFullName(),
		(origin - ref.origin).Magnitude,
		1 / scale,
		residual
	))
end

local function registerVisualGroup()
	if not PhysicsService:IsCollisionGroupRegistered(VISUAL_GROUP) then
		PhysicsService:RegisterCollisionGroup(VISUAL_GROUP)
	end
	for _, group in ipairs(PhysicsService:GetRegisteredCollisionGroups()) do
		PhysicsService:CollisionGroupSetCollidable(VISUAL_GROUP, group.name, false)
	end
end

-- Set this attribute (boolean, true) in Studio on a MeshPart, or on any Model /
-- Folder above it, to keep the Color, Material and Transparency chosen in
-- Studio instead of the Blender palette.
local KEEP_LOOK_ATTRIBUTE = "KeepStudioLook"

local function keepsStudioLook(part, model)
	local node = part
	while node do
		if node:GetAttribute(KEEP_LOOK_ATTRIBUTE) == true then
			return true
		end
		if node == model then
			return false
		end
		node = node.Parent
	end
	return false
end

local function prepareVisuals(model)
	local unknown, kept = 0, 0
	for _, part in ipairs(model:GetDescendants()) do
		if part:IsA("BasePart") then
			part.Anchored = true
			part.CanTouch = false
			part.CanCollide = true
			part.CanQuery = true
			part.CollisionGroup = VISUAL_GROUP

			local key = materialKey(part.Name)
			local look = key and MapData.materials[key]
			if key ~= "ref" and keepsStudioLook(part, model) then
				kept += 1
			elseif look then
				-- Whatever the importer built from the glTF material is replaced by the palette.
				local appearance = part:FindFirstChildOfClass("SurfaceAppearance")
				if appearance then
					appearance:Destroy()
				end
				part.Color = look.color
				part.Material = toMaterial(look.material) or Enum.Material.SmoothPlastic
				part.Transparency = look.transparency
			else
				unknown += 1
			end
			if key == "ref" then
				part.CanCollide = false
				part.CanQuery = false
				part.CastShadow = false
			end
		end
	end
	if unknown > 0 then
		warn(("MapService: %d part(s) of %s have no known material key"):format(unknown, model.Name))
	end
	if kept > 0 then
		print(("MapService: %d part(s) of %s keep their Studio look (%s)"):format(kept, model.Name, KEEP_LOOK_ATTRIBUTE))
	end
end

-- The default Studio template has a Baseplate whose top sits at Y = 0, exactly
-- where the map floor is: it would z-fight with the ground everywhere.
local function removeTemplateBaseplate()
	local baseplate = Workspace:FindFirstChild("Baseplate")
	if baseplate and baseplate:IsA("BasePart") then
		baseplate:Destroy()
		print("MapService: removed the template Baseplate")
	end
	local templateSpawn = Workspace:FindFirstChild("SpawnLocation")
	if templateSpawn and templateSpawn:IsA("SpawnLocation") then
		templateSpawn.Enabled = false
	end
end

local function buildColliders()
	local existing = Workspace:FindFirstChild("MapColliders")
	if existing then
		existing:Destroy()
	end
	local folder = Instance.new("Folder")
	folder.Name = "MapColliders"
	for _, entry in ipairs(MapColliders) do
		local part = Instance.new("Part")
		part.Name = entry.section .. "_" .. entry.kind
		part.Anchored = true
		part.CanCollide = true
		part.CanTouch = false
		part.CanQuery = entry.kind ~= "barrier"
		part.CastShadow = false
		part.Transparency = 1
		if entry.material then
			part.Material = toMaterial(entry.material) or Enum.Material.SmoothPlastic
		end
		if entry.shape == "cylinder" then
			-- A Roblox cylinder runs along its X axis: stand it up.
			part.Shape = Enum.PartType.Cylinder
			part.Size = Vector3.new(entry.size.Y, entry.size.X, entry.size.Z)
			part.CFrame = CFrame.new(entry.position) * CFrame.Angles(0, 0, math.pi / 2)
		else
			part.Size = entry.size
			part.CFrame = CFrame.new(entry.position) * CFrame.Angles(0, entry.yaw, 0)
		end
		part.Parent = folder
	end
	folder.Parent = Workspace
	return #MapColliders
end

local function buildSpawns()
	local folder = Instance.new("Folder")
	folder.Name = "LobbySpawns"
	for index, position in ipairs(MapData.lobby.spawns) do
		local spawn = Instance.new("SpawnLocation")
		spawn.Name = "LobbySpawn" .. index
		spawn.Anchored = true
		spawn.CanCollide = false
		spawn.CanQuery = false
		spawn.CanTouch = false
		spawn.Transparency = 1
		spawn.Size = Vector3.new(6, 1, 6)
		spawn.Neutral = true
		spawn.Duration = 3
		spawn.CFrame = CFrame.new(position + Vector3.new(0, 0.5, 0)) * CFrame.Angles(0, MapData.lobby.spawnYaw, 0)
		spawn.Parent = folder
	end
	folder.Parent = Workspace
	return #MapData.lobby.spawns
end

-- Where a portal target sends a player: "lobby", "base" or "zone:<id>".
local function destinationFor(player, target)
	if target == "lobby" then
		local spawns = MapData.lobby.spawns
		return spawns[rng:NextInteger(1, #spawns)], MapData.lobby.spawnYaw
	elseif target == "base" then
		local plot = plotProvider and plotProvider.GetPlot(player)
		if plot then
			return plot.spawn, plot.spawnYaw
		end
		return nil
	end
	local zoneId = string.match(target, "^zone:(.+)$")
	local zone = zoneId and MapData.GetZoneById(zoneId)
	if zone then
		return zone.spawn, zone.spawnYaw
	end
	return nil
end

function MapService.TeleportTo(player, target)
	local character = player.Character
	if not (character and character:FindFirstChild("HumanoidRootPart")) then
		return false
	end
	local position, yaw = destinationFor(player, target)
	if not position then
		return false
	end
	character:PivotTo(CFrame.new(position + Vector3.new(0, TELEPORT_HEIGHT, 0)) * CFrame.Angles(0, yaw, 0))
	return true
end

local function buildPortals()
	local folder = Instance.new("Folder")
	folder.Name = "Portals"
	for _, portal in ipairs(MapData.portals) do
		local trigger = Instance.new("Part")
		trigger.Name = portal.id
		trigger.Anchored = true
		trigger.CanCollide = false
		trigger.CanQuery = false
		trigger.CanTouch = true
		trigger.CastShadow = false
		trigger.Transparency = 1
		trigger.Size = portal.size
		trigger.CFrame = CFrame.new(portal.position) * CFrame.Angles(0, portal.yaw, 0)
		trigger:SetAttribute("Target", portal.target)
		trigger.Touched:Connect(function(hit)
			local character = hit:FindFirstAncestorOfClass("Model")
			local player = character and Players:GetPlayerFromCharacter(character)
			if not player then
				return
			end
			local now = os.clock()
			if lastTeleport[player] and now - lastTeleport[player] < PORTAL_COOLDOWN then
				return
			end
			lastTeleport[player] = now
			MapService.TeleportTo(player, portal.target)
		end)
		trigger.Parent = folder
	end
	folder.Parent = Workspace
	return #MapData.portals
end

-- plots: a module exposing GetPlot(player) (PlotService), used by the "MA BASE" portal.
function MapService.Start(plots)
	plotProvider = plots
	registerVisualGroup()

	local maps = findImportedMaps()
	if #maps == 0 then
		warn(
			"MapService: no imported map in Workspace. Import KaijuHeist/assets/map/kaiju_heist_map.glb "
				.. "with the 3D Importer (see MAPS.md). Colliders, spawns and portals are built anyway."
		)
	end
	for _, model in ipairs(maps) do
		alignMap(model)
		prepareVisuals(model)
	end

	removeTemplateBaseplate()
	local colliders = buildColliders()
	local spawns = buildSpawns()
	local portals = buildPortals()

	Players.PlayerRemoving:Connect(function(player)
		lastTeleport[player] = nil
	end)

	print(("MapService: %d map model(s), %d colliders, %d spawns, %d portals"):format(
		#maps,
		colliders,
		spawns,
		portals
	))
end

return MapService
