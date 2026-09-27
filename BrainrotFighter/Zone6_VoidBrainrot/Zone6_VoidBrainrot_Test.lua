--[[
	BRAINROT FIGHTER - Zone6_VoidBrainrot installer (standalone test map, v2: terraformed and alive)
	Paste this whole file into the Studio command bar in EDIT mode (not during Play),
	after importing Zone6_VoidBrainrot.fbx with the 3D Importer. Safe to run again as many times as needed.
	  - finds the imported map, anchors it, fixes its size, position and orientation
	  - 285 invisible walkable surfaces (plateau, hill, summit, terraces, butte, islands, bridges, stairs)
	  - spawn on the golden entrance island, facing the map
	  - neon, 96 lights, 14 particle emitters, starry sky and violet ambience
	  - 101 living objects, animated on each player's screen by the "MapLife" LocalScript
	The void surrounds the map: if you fall, you respawn at the entrance.
]]
local NAME = "Zone6_VoidBrainrot"

-- SCALE: 1 = intended size (about 600 playable studs). 0.8 = smaller, 1.2 = bigger...
local SCALE = 1
local WIDTH = 930.8 * SCALE -- full model width (floating decor included)
local ZONE_CENTER = Vector3.new(0, 0, 0)
local OFFSET = Vector3.new(-0.37, 51.44, -0.54)

-- Landmarks (original positions in studs): arena, Star, arches, spawn
local MARK_ARENA = Vector2.new(160, -172)
local MARK_STAR = Vector2.new(-178, 238)
local MARK_ARCHES = Vector2.new(150.0, 238)
local SPAWN = Vector3.new(-155, -4, 226)
local UNIQUE_MARKER = "Decor_Sky_Brain" -- object that only exists in this map

-- If the map is grey after the import: import Zone6_VoidBrainrot_Palette.png (Asset Manager),
-- paste its ID here (rbxassetid://...) and run the script again.
local TEXTURE_ID = ""

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local ServerStorage = game:GetService("ServerStorage")
local StarterPlayer = game:GetService("StarterPlayer")
print("----- Installation de " .. NAME .. " -----")

-- 0. Find the imported map ------------------------------------------------------------
local function isThisMap(obj)
	return obj:FindFirstChild("Sol_Arene", true) ~= nil and obj:FindFirstChild(UNIQUE_MARKER, true) ~= nil
end
local found = {}
for _, obj in workspace:GetChildren() do
	if not obj:IsA("BasePart") and not obj:IsA("Terrain") and isThisMap(obj) then
		table.insert(found, obj)
	end
end
local m = found[1]
if not m and workspace:FindFirstChild(UNIQUE_MARKER) then
	m = Instance.new("Model")
	m.Parent = workspace
	for _, obj in workspace:GetChildren() do
		local n = obj.Name
		if n:match("^Sol_") or n:match("^Decor_") or n:match("^Neon_") or n:match("^Star_") then
			obj.Parent = m
		end
	end
end
assert(m, "❌ Map introuvable : as-tu bien importé " .. NAME .. ".fbx dans le Workspace ?")
for i = 2, #found do
	found[i].Parent = ServerStorage
	print("⚠️ Copie en trop rangée dans ServerStorage")
end
if not m:IsA("Model") then
	local model = Instance.new("Model")
	model.Parent = workspace
	for _, child in m:GetChildren() do
		child.Parent = model
	end
	m:Destroy()
	m = model
end
m.Name = NAME

-- What a previous run created is rebuilt below
for _, name in { "Collisions", "Lights", "Particles" } do
	local old = m:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end
for _, d in m:GetDescendants() do
	if d.Name == "MapLight" or d.Name == "MapFx" then
		d:Destroy()
	end
end

for _, p in m:GetDescendants() do
	if p:IsA("BasePart") then
		p.Anchored = true
	end
end
print("✅ Tout est ancré")

-- Other test maps already here: move 1500 studs aside
local others = {}
for _, obj in workspace:GetChildren() do
	if obj ~= m and obj:IsA("Model") and obj:FindFirstChild("Sol_Arene", true) then
		table.insert(others, (obj:GetBoundingBox()).Position)
	end
end
local moved = true
while moved do
	moved = false
	for _, pos in others do
		if (pos * Vector3.new(1, 0, 1) - ZONE_CENTER).Magnitude < 1200 then
			ZONE_CENTER += Vector3.new(1500, 0, 0)
			moved = true
		end
	end
end
if ZONE_CENTER.X ~= 0 then
	print("ℹ️ D'autres maps sont déjà là : " .. NAME .. " est placée à X = " .. math.floor(ZONE_CENTER.X))
end

-- 1. Size and position ------------------------------------------------------------------
local cf, size = m:GetBoundingBox()
for _, p in m:GetDescendants() do
	if p:IsA("MeshPart") and math.max(p.Size.X, p.Size.Y, p.Size.Z) >= 2040 then
		warn("⚠️ Import beaucoup trop grand : réimporte le FBX en changeant l'unité d'échelle.")
		break
	end
end
local currentWidth = math.max(size.X, size.Z)
if math.abs(currentWidth - WIDTH) > 5 then
	m:ScaleTo(m:GetScale() * WIDTH / currentWidth)
	cf, size = m:GetBoundingBox()
end
m:PivotTo(CFrame.new(ZONE_CENTER + OFFSET * SCALE - cf.Position) * m:GetPivot())
print("✅ Taille : " .. math.floor(size.X) .. " x " .. math.floor(size.Z) .. " studs")

-- 2. Real orientation (from the landmarks) ------------------------------------------------
local function centerOf(name)
	local obj = m:FindFirstChild(name, true)
	if not obj then
		return nil
	end
	if obj:IsA("BasePart") then
		return obj.Position
	end
	return (obj:GetBoundingBox()).Position
end
local function v2(v)
	return Vector2.new(v.X, v.Z)
end
local function cross(a, b)
	return a.X * b.Y - a.Y * b.X
end
local Aw, Fw, Bw = centerOf("Sol_Arene"), centerOf("Star_Socle"), centerOf("Neon_arche")
local transform
local k = SCALE
if Aw and Fw then
	local a2, f2 = v2(Aw), v2(Fw)
	local ue, uw = (MARK_STAR - MARK_ARENA).Unit, (f2 - a2).Unit
	local ne, nw = Vector2.new(-ue.Y, ue.X), Vector2.new(-uw.Y, uw.X)
	k = (f2 - a2).Magnitude / (MARK_STAR - MARK_ARENA).Magnitude
	local mirror = 1
	if Bw then
		mirror = math.sign(cross(ue, MARK_ARCHES - MARK_ARENA)) * math.sign(cross(uw, v2(Bw) - a2))
		if mirror == 0 then
			mirror = 1
		end
	end
	local kk = k
	transform = function(ex, ey, ez)
		local d = Vector2.new(ex, ez) - MARK_ARENA
		local w = a2 + uw * (d:Dot(ue) * kk) + nw * (d:Dot(ne) * kk * mirror)
		return Vector3.new(w.X, ZONE_CENTER.Y + ey * kk, w.Y)
	end
	print("✅ Orientation détectée" .. (mirror < 0 and " (map inversée par l'import, corrigé)" or ""))
else
	warn("⚠️ Repères introuvables : orientation supposée standard")
	transform = function(ex, ey, ez)
		return ZONE_CENTER + Vector3.new(ex, ey, ez) * SCALE
	end
end
local function worldDir(d)
	local v = transform(d[1], d[2], d[3]) - transform(0, 0, 0)
	return if v.Magnitude > 1e-6 then v.Unit else Vector3.yAxis
end
local mapRotation = CFrame.fromMatrix(Vector3.zero, worldDir({ 1, 0, 0 }), Vector3.yAxis) -- boxes follow the map

-- 3. Invisible walkable surfaces (every level) ---------------------------------------------
local COLLISIONS = {
	{-94.0, 0.0, 179.0, 56.0, 0.0, 179.0, 6.3, 4.0},
	{-142.0, 0.0, 173.0, 122.0, 0.0, 173.0, 6.3, 4.0},
	{-184.0, 0.0, 167.0, 152.0, 0.0, 167.0, 6.3, 4.0},
	{-208.0, 0.0, 161.0, 176.0, 0.0, 161.0, 6.3, 4.0},
	{-232.0, 0.0, 155.0, 188.0, 0.0, 155.0, 6.3, 4.0},
	{-250.0, 0.0, 149.0, 194.0, 0.0, 149.0, 6.3, 4.0},
	{-250.0, 0.0, 143.0, 200.0, 0.0, 143.0, 6.3, 4.0},
	{-250.0, 0.0, 137.0, 206.0, 0.0, 137.0, 6.3, 4.0},
	{-256.0, 0.0, 131.0, 212.0, 0.0, 131.0, 6.3, 4.0},
	{-256.0, 0.0, 125.0, 218.0, 0.0, 125.0, 6.3, 4.0},
	{-256.0, 0.0, 119.0, 224.0, 0.0, 119.0, 6.3, 4.0},
	{-256.0, 0.0, 113.0, 230.0, 0.0, 113.0, 6.3, 4.0},
	{-256.0, 0.0, 107.0, 230.0, 0.0, 107.0, 6.3, 4.0},
	{-256.0, 0.0, 101.0, 236.0, 0.0, 101.0, 6.3, 4.0},
	{-256.0, 0.0, 95.0, 236.0, 0.0, 95.0, 6.3, 4.0},
	{-262.0, 0.0, 89.0, 236.0, 0.0, 89.0, 6.3, 4.0},
	{-262.0, 0.0, 83.0, 236.0, 0.0, 83.0, 6.3, 4.0},
	{-262.0, 0.0, 77.0, 242.0, 0.0, 77.0, 6.3, 4.0},
	{-262.0, 0.0, 71.0, 242.0, 0.0, 71.0, 6.3, 4.0},
	{-262.0, 0.0, 65.0, 242.0, 0.0, 65.0, 6.3, 4.0},
	{-262.0, 0.0, 59.0, 242.0, 0.0, 59.0, 6.3, 4.0},
	{-262.0, 0.0, 53.0, 248.0, 0.0, 53.0, 6.3, 4.0},
	{-262.0, 0.0, 47.0, 248.0, 0.0, 47.0, 6.3, 4.0},
	{-262.0, 0.0, 41.0, 248.0, 0.0, 41.0, 6.3, 4.0},
	{-262.0, 0.0, 35.0, 248.0, 0.0, 35.0, 6.3, 4.0},
	{-262.0, 0.0, 29.0, 248.0, 0.0, 29.0, 6.3, 4.0},
	{-262.0, 0.0, 23.0, 248.0, 0.0, 23.0, 6.3, 4.0},
	{-262.0, 0.0, 17.0, 248.0, 0.0, 17.0, 6.3, 4.0},
	{-262.0, 0.0, 11.0, 248.0, 0.0, 11.0, 6.3, 4.0},
	{-262.0, 0.0, 5.0, 248.0, 0.0, 5.0, 6.3, 4.0},
	{-262.0, 0.0, -1.0, 248.0, 0.0, -1.0, 6.3, 4.0},
	{-262.0, 0.0, -7.0, 248.0, 0.0, -7.0, 6.3, 4.0},
	{-262.0, 0.0, -13.0, 248.0, 0.0, -13.0, 6.3, 4.0},
	{-262.0, 0.0, -19.0, 248.0, 0.0, -19.0, 6.3, 4.0},
	{-262.0, 0.0, -25.0, 254.0, 0.0, -25.0, 6.3, 4.0},
	{-262.0, 0.0, -31.0, 254.0, 0.0, -31.0, 6.3, 4.0},
	{-262.0, 0.0, -37.0, 254.0, 0.0, -37.0, 6.3, 4.0},
	{-262.0, 0.0, -43.0, 254.0, 0.0, -43.0, 6.3, 4.0},
	{-262.0, 0.0, -49.0, 254.0, 0.0, -49.0, 6.3, 4.0},
	{-262.0, 0.0, -55.0, 248.0, 0.0, -55.0, 6.3, 4.0},
	{-262.0, 0.0, -61.0, 248.0, 0.0, -61.0, 6.3, 4.0},
	{-262.0, 0.0, -67.0, 248.0, 0.0, -67.0, 6.3, 4.0},
	{-262.0, 0.0, -73.0, 248.0, 0.0, -73.0, 6.3, 4.0},
	{-262.0, 0.0, -79.0, 248.0, 0.0, -79.0, 6.3, 4.0},
	{-262.0, 0.0, -85.0, 248.0, 0.0, -85.0, 6.3, 4.0},
	{-262.0, 0.0, -91.0, 248.0, 0.0, -91.0, 6.3, 4.0},
	{-256.0, 0.0, -97.0, 134.0, 0.0, -97.0, 6.3, 4.0},
	{188.0, 0.0, -97.0, 248.0, 0.0, -97.0, 6.3, 4.0},
	{-256.0, 0.0, -103.0, 122.0, 0.0, -103.0, 6.3, 4.0},
	{200.0, 0.0, -103.0, 248.0, 0.0, -103.0, 6.3, 4.0},
	{-256.0, 0.0, -109.0, 110.0, 0.0, -109.0, 6.3, 4.0},
	{206.0, 0.0, -109.0, 242.0, 0.0, -109.0, 6.3, 4.0},
	{-256.0, 0.0, -115.0, 104.0, 0.0, -115.0, 6.3, 4.0},
	{218.0, 0.0, -115.0, 242.0, 0.0, -115.0, 6.3, 4.0},
	{-256.0, 0.0, -121.0, 98.0, 0.0, -121.0, 6.3, 4.0},
	{224.0, 0.0, -121.0, 242.0, 0.0, -121.0, 6.3, 4.0},
	{-256.0, 0.0, -127.0, 92.0, 0.0, -127.0, 6.3, 4.0},
	{224.0, 0.0, -127.0, 242.0, 0.0, -127.0, 6.3, 4.0},
	{-256.0, 0.0, -133.0, 92.0, 0.0, -133.0, 6.3, 4.0},
	{230.0, 0.0, -133.0, 236.0, 0.0, -133.0, 6.3, 4.0},
	{-256.0, 0.0, -139.0, 86.0, 0.0, -139.0, 6.3, 4.0},
	{230.0, 0.0, -139.0, 236.0, 0.0, -139.0, 6.3, 4.0},
	{-256.0, 0.0, -145.0, 86.0, 0.0, -145.0, 6.3, 4.0},
	{-250.0, 0.0, -151.0, 86.0, 0.0, -151.0, 6.3, 4.0},
	{-250.0, 0.0, -157.0, 80.0, 0.0, -157.0, 6.3, 4.0},
	{-250.0, 0.0, -163.0, 80.0, 0.0, -163.0, 6.3, 4.0},
	{-244.0, 0.0, -169.0, 80.0, 0.0, -169.0, 6.3, 4.0},
	{-244.0, 0.0, -175.0, 80.0, 0.0, -175.0, 6.3, 4.0},
	{-244.0, 0.0, -181.0, 80.0, 0.0, -181.0, 6.3, 4.0},
	{-238.0, 0.0, -187.0, 80.0, 0.0, -187.0, 6.3, 4.0},
	{-238.0, 0.0, -193.0, 86.0, 0.0, -193.0, 6.3, 4.0},
	{-238.0, 0.0, -199.0, 86.0, 0.0, -199.0, 6.3, 4.0},
	{-238.0, 0.0, -205.0, 86.0, 0.0, -205.0, 6.3, 4.0},
	{-226.0, 0.0, -211.0, 92.0, 0.0, -211.0, 6.3, 4.0},
	{-214.0, 0.0, -217.0, 92.0, 0.0, -217.0, 6.3, 4.0},
	{-208.0, 0.0, -223.0, 98.0, 0.0, -223.0, 6.3, 4.0},
	{-196.0, 0.0, -229.0, 104.0, 0.0, -229.0, 6.3, 4.0},
	{-190.0, 0.0, -235.0, 110.0, 0.0, -235.0, 6.3, 4.0},
	{-172.0, 0.0, -241.0, 122.0, 0.0, -241.0, 6.3, 4.0},
	{-124.0, 0.0, -247.0, 134.0, 0.0, -247.0, 6.3, 4.0},
	{-40.0, 0.0, -253.0, 2.0, 0.0, -253.0, 6.3, 4.0},
	{-17.0, 16.0, 30.5, 13.0, 16.0, 30.5, 6.3, 16.0},
	{-29.0, 16.0, 24.5, 25.0, 16.0, 24.5, 6.3, 16.0},
	{-65.0, 16.0, 18.5, 37.0, 16.0, 18.5, 6.3, 16.0},
	{-83.0, 16.0, 12.5, 49.0, 16.0, 12.5, 6.3, 16.0},
	{-89.0, 16.0, 6.5, 55.0, 16.0, 6.5, 6.3, 16.0},
	{-89.0, 16.0, 0.5, 55.0, 16.0, 0.5, 6.3, 16.0},
	{-95.0, 16.0, -5.5, 55.0, 16.0, -5.5, 6.3, 16.0},
	{-95.0, 16.0, -11.5, 55.0, 16.0, -11.5, 6.3, 16.0},
	{-95.0, 16.0, -17.5, 55.0, 16.0, -17.5, 6.3, 16.0},
	{-101.0, 16.0, -23.5, 55.0, 16.0, -23.5, 6.3, 16.0},
	{-101.0, 16.0, -29.5, 55.0, 16.0, -29.5, 6.3, 16.0},
	{-107.0, 16.0, -35.5, 49.0, 16.0, -35.5, 6.3, 16.0},
	{-107.0, 16.0, -41.5, 49.0, 16.0, -41.5, 6.3, 16.0},
	{-107.0, 16.0, -47.5, 49.0, 16.0, -47.5, 6.3, 16.0},
	{-107.0, 16.0, -53.5, 55.0, 16.0, -53.5, 6.3, 16.0},
	{-101.0, 16.0, -59.5, 55.0, 16.0, -59.5, 6.3, 16.0},
	{-101.0, 16.0, -65.5, 55.0, 16.0, -65.5, 6.3, 16.0},
	{-95.0, 16.0, -71.5, 55.0, 16.0, -71.5, 6.3, 16.0},
	{-89.0, 16.0, -77.5, 55.0, 16.0, -77.5, 6.3, 16.0},
	{-89.0, 16.0, -83.5, 55.0, 16.0, -83.5, 6.3, 16.0},
	{-89.0, 16.0, -89.5, 49.0, 16.0, -89.5, 6.3, 16.0},
	{-83.0, 16.0, -95.5, 49.0, 16.0, -95.5, 6.3, 16.0},
	{-71.0, 16.0, -101.5, 37.0, 16.0, -101.5, 6.3, 16.0},
	{-29.0, 16.0, -107.5, 31.0, 16.0, -107.5, 6.3, 16.0},
	{-17.0, 16.0, -113.5, 25.0, 16.0, -113.5, 6.3, 16.0},
	{-51.9, 30.0, -30.7, -27.9, 30.0, -30.7, 6.3, 14.0},
	{-57.9, 30.0, -36.7, -3.9, 30.0, -36.7, 6.3, 14.0},
	{-63.9, 30.0, -42.7, 2.1, 30.0, -42.7, 6.3, 14.0},
	{-63.9, 30.0, -48.7, 8.1, 30.0, -48.7, 6.3, 14.0},
	{-63.9, 30.0, -54.7, 8.1, 30.0, -54.7, 6.3, 14.0},
	{-63.9, 30.0, -60.7, 2.1, 30.0, -60.7, 6.3, 14.0},
	{-57.9, 30.0, -66.7, 2.1, 30.0, -66.7, 6.3, 14.0},
	{-57.9, 30.0, -72.7, -3.9, 30.0, -72.7, 6.3, 14.0},
	{-57.9, 30.0, -78.7, -15.9, 30.0, -78.7, 6.3, 14.0},
	{-39.9, 30.0, -84.7, -27.9, 30.0, -84.7, 6.3, 14.0},
	{164.8, 8.0, 78.3, 182.8, 8.0, 78.3, 6.3, 8.0},
	{146.8, 8.0, 72.3, 212.8, 8.0, 72.3, 6.3, 8.0},
	{140.8, 8.0, 66.3, 230.8, 8.0, 66.3, 6.3, 8.0},
	{134.8, 8.0, 60.3, 236.8, 8.0, 60.3, 6.3, 8.0},
	{134.8, 8.0, 54.3, 236.8, 8.0, 54.3, 6.3, 8.0},
	{134.8, 8.0, 48.3, 236.8, 8.0, 48.3, 6.3, 8.0},
	{134.8, 8.0, 42.3, 236.8, 8.0, 42.3, 6.3, 8.0},
	{134.8, 8.0, 36.3, 242.8, 8.0, 36.3, 6.3, 8.0},
	{134.8, 8.0, 30.3, 242.8, 8.0, 30.3, 6.3, 8.0},
	{134.8, 8.0, 24.3, 242.8, 8.0, 24.3, 6.3, 8.0},
	{140.8, 8.0, 18.3, 242.8, 8.0, 18.3, 6.3, 8.0},
	{140.8, 8.0, 12.3, 242.8, 8.0, 12.3, 6.3, 8.0},
	{140.8, 8.0, 6.3, 242.8, 8.0, 6.3, 6.3, 8.0},
	{140.8, 8.0, 0.3, 242.8, 8.0, 0.3, 6.3, 8.0},
	{140.8, 8.0, -5.7, 242.8, 8.0, -5.7, 6.3, 8.0},
	{140.8, 8.0, -11.7, 236.8, 8.0, -11.7, 6.3, 8.0},
	{140.8, 8.0, -17.7, 236.8, 8.0, -17.7, 6.3, 8.0},
	{140.8, 8.0, -23.7, 236.8, 8.0, -23.7, 6.3, 8.0},
	{140.8, 8.0, -29.7, 236.8, 8.0, -29.7, 6.3, 8.0},
	{140.8, 8.0, -35.7, 230.8, 8.0, -35.7, 6.3, 8.0},
	{146.8, 8.0, -41.7, 224.8, 8.0, -41.7, 6.3, 8.0},
	{146.8, 8.0, -47.7, 218.8, 8.0, -47.7, 6.3, 8.0},
	{158.8, 8.0, -53.7, 188.8, 8.0, -53.7, 6.3, 8.0},
	{-184.9, 10.0, -123.3, -160.9, 10.0, -123.3, 6.3, 10.0},
	{-220.9, 10.0, -129.3, -130.9, 10.0, -129.3, 6.3, 10.0},
	{-232.9, 10.0, -135.3, -112.9, 10.0, -135.3, 6.3, 10.0},
	{-232.9, 10.0, -141.3, -106.9, 10.0, -141.3, 6.3, 10.0},
	{-232.9, 10.0, -147.3, -100.9, 10.0, -147.3, 6.3, 10.0},
	{-232.9, 10.0, -153.3, -100.9, 10.0, -153.3, 6.3, 10.0},
	{-232.9, 10.0, -159.3, -100.9, 10.0, -159.3, 6.3, 10.0},
	{-226.9, 10.0, -165.3, -100.9, 10.0, -165.3, 6.3, 10.0},
	{-232.9, 10.0, -171.3, -100.9, 10.0, -171.3, 6.3, 10.0},
	{-232.9, 10.0, -177.3, -100.9, 10.0, -177.3, 6.3, 10.0},
	{-232.9, 10.0, -183.3, -100.9, 10.0, -183.3, 6.3, 10.0},
	{-232.9, 10.0, -189.3, -94.9, 10.0, -189.3, 6.3, 10.0},
	{-232.9, 10.0, -195.3, -100.9, 10.0, -195.3, 6.3, 10.0},
	{-232.9, 10.0, -201.3, -100.9, 10.0, -201.3, 6.3, 10.0},
	{-232.9, 10.0, -207.3, -106.9, 10.0, -207.3, 6.3, 10.0},
	{-226.9, 10.0, -213.3, -112.9, 10.0, -213.3, 6.3, 10.0},
	{-226.9, 10.0, -219.3, -118.9, 10.0, -219.3, 6.3, 10.0},
	{-220.9, 10.0, -225.3, -136.9, 10.0, -225.3, 6.3, 10.0},
	{-202.1, 12.0, 105.4, -166.1, 12.0, 105.4, 6.3, 12.0},
	{-208.1, 12.0, 99.4, -160.1, 12.0, 99.4, 6.3, 12.0},
	{-208.1, 12.0, 93.4, -148.1, 12.0, 93.4, 6.3, 12.0},
	{-208.1, 12.0, 87.4, -142.1, 12.0, 87.4, 6.3, 12.0},
	{-214.1, 12.0, 81.4, -142.1, 12.0, 81.4, 6.3, 12.0},
	{-214.1, 12.0, 75.4, -142.1, 12.0, 75.4, 6.3, 12.0},
	{-214.1, 12.0, 69.4, -142.1, 12.0, 69.4, 6.3, 12.0},
	{-214.1, 12.0, 63.4, -142.1, 12.0, 63.4, 6.3, 12.0},
	{-208.1, 12.0, 57.4, -148.1, 12.0, 57.4, 6.3, 12.0},
	{-184.1, 12.0, 51.4, -172.1, 12.0, 51.4, 6.3, 12.0},
	{144.0, -6.0, -117.0, 180.0, -6.0, -117.0, 6.3, 4.0},
	{132.0, -6.0, -123.0, 192.0, -6.0, -123.0, 6.3, 4.0},
	{120.0, -6.0, -129.0, 198.0, -6.0, -129.0, 6.3, 4.0},
	{114.0, -6.0, -135.0, 204.0, -6.0, -135.0, 6.3, 4.0},
	{114.0, -6.0, -141.0, 210.0, -6.0, -141.0, 6.3, 4.0},
	{108.0, -6.0, -147.0, 210.0, -6.0, -147.0, 6.3, 4.0},
	{108.0, -6.0, -153.0, 216.0, -6.0, -153.0, 6.3, 4.0},
	{102.0, -6.0, -159.0, 216.0, -6.0, -159.0, 6.3, 4.0},
	{102.0, -6.0, -165.0, 216.0, -6.0, -165.0, 6.3, 4.0},
	{102.0, -6.0, -171.0, 216.0, -6.0, -171.0, 6.3, 4.0},
	{102.0, -6.0, -177.0, 216.0, -6.0, -177.0, 6.3, 4.0},
	{102.0, -6.0, -183.0, 216.0, -6.0, -183.0, 6.3, 4.0},
	{102.0, -6.0, -189.0, 216.0, -6.0, -189.0, 6.3, 4.0},
	{108.0, -6.0, -195.0, 216.0, -6.0, -195.0, 6.3, 4.0},
	{108.0, -6.0, -201.0, 210.0, -6.0, -201.0, 6.3, 4.0},
	{114.0, -6.0, -207.0, 204.0, -6.0, -207.0, 6.3, 4.0},
	{120.0, -6.0, -213.0, 204.0, -6.0, -213.0, 6.3, 4.0},
	{126.0, -6.0, -219.0, 192.0, -6.0, -219.0, 6.3, 4.0},
	{138.0, -6.0, -225.0, 186.0, -6.0, -225.0, 6.3, 4.0},
	{-182.6, -4.0, 275.0, -170.6, -4.0, 275.0, 6.3, 4.0},
	{-194.6, -4.0, 269.0, -164.6, -4.0, 269.0, 6.3, 4.0},
	{-206.6, -4.0, 263.0, -152.6, -4.0, 263.0, 6.3, 4.0},
	{-212.6, -4.0, 257.0, -140.6, -4.0, 257.0, 6.3, 4.0},
	{-212.6, -4.0, 251.0, -140.6, -4.0, 251.0, 6.3, 4.0},
	{-212.6, -4.0, 245.0, -140.6, -4.0, 245.0, 6.3, 4.0},
	{-212.6, -4.0, 239.0, -140.6, -4.0, 239.0, 6.3, 4.0},
	{-212.6, -4.0, 233.0, -140.6, -4.0, 233.0, 6.3, 4.0},
	{-212.6, -4.0, 227.0, -140.6, -4.0, 227.0, 6.3, 4.0},
	{-212.6, -4.0, 221.0, -140.6, -4.0, 221.0, 6.3, 4.0},
	{-206.6, -4.0, 215.0, -146.6, -4.0, 215.0, 6.3, 4.0},
	{-194.6, -4.0, 209.0, -158.6, -4.0, 209.0, 6.3, 4.0},
	{-188.6, -4.0, 203.0, -170.6, -4.0, 203.0, 6.3, 4.0},
	{113.3, -10.0, 282.1, 143.3, -10.0, 282.1, 6.3, 4.0},
	{101.3, -10.0, 276.1, 197.3, -10.0, 276.1, 6.3, 4.0},
	{95.3, -10.0, 270.1, 203.3, -10.0, 270.1, 6.3, 4.0},
	{89.3, -10.0, 264.1, 203.3, -10.0, 264.1, 6.3, 4.0},
	{89.3, -10.0, 258.1, 209.3, -10.0, 258.1, 6.3, 4.0},
	{89.3, -10.0, 252.1, 209.3, -10.0, 252.1, 6.3, 4.0},
	{95.3, -10.0, 246.1, 209.3, -10.0, 246.1, 6.3, 4.0},
	{95.3, -10.0, 240.1, 209.3, -10.0, 240.1, 6.3, 4.0},
	{95.3, -10.0, 234.1, 209.3, -10.0, 234.1, 6.3, 4.0},
	{95.3, -10.0, 228.1, 203.3, -10.0, 228.1, 6.3, 4.0},
	{95.3, -10.0, 222.1, 197.3, -10.0, 222.1, 6.3, 4.0},
	{95.3, -10.0, 216.1, 197.3, -10.0, 216.1, 6.3, 4.0},
	{101.3, -10.0, 210.1, 197.3, -10.0, 210.1, 6.3, 4.0},
	{107.3, -10.0, 204.1, 191.3, -10.0, 204.1, 6.3, 4.0},
	{119.3, -10.0, 198.1, 167.3, -10.0, 198.1, 6.3, 4.0},
	{137.3, -10.0, 192.1, 155.3, -10.0, 192.1, 6.3, 4.0},
	{2.0, -14.0, 277.0, 14.0, -14.0, 277.0, 6.3, 4.0},
	{-4.0, -14.0, 271.0, 26.0, -14.0, 271.0, 6.3, 4.0},
	{-16.0, -14.0, 265.0, 38.0, -14.0, 265.0, 6.3, 4.0},
	{-16.0, -14.0, 259.0, 38.0, -14.0, 259.0, 6.3, 4.0},
	{-16.0, -14.0, 253.0, 38.0, -14.0, 253.0, 6.3, 4.0},
	{-16.0, -14.0, 247.0, 38.0, -14.0, 247.0, 6.3, 4.0},
	{-16.0, -14.0, 241.0, 38.0, -14.0, 241.0, 6.3, 4.0},
	{-16.0, -14.0, 235.0, 38.0, -14.0, 235.0, 6.3, 4.0},
	{-4.0, -14.0, 229.0, 26.0, -14.0, 229.0, 6.3, 4.0},
	{2.0, -14.0, 223.0, 14.0, -14.0, 223.0, 6.3, 4.0},
	{-262.0, -14.0, 292.1, -238.0, -14.0, 292.1, 6.3, 4.0},
	{-268.0, -14.0, 286.1, -238.0, -14.0, 286.1, 6.3, 4.0},
	{-274.0, -14.0, 280.1, -232.0, -14.0, 280.1, 6.3, 4.0},
	{-274.0, -14.0, 274.1, -232.0, -14.0, 274.1, 6.3, 4.0},
	{-268.0, -14.0, 268.1, -232.0, -14.0, 268.1, 6.3, 4.0},
	{-268.0, -14.0, 262.1, -238.0, -14.0, 262.1, 6.3, 4.0},
	{-160.0, -4.0, 207.0, -150.0, 0.0, 168.0, 11.0, 4.0},
	{150.0, 0.0, 166.0, 150.0, -10.0, 198.0, 11.0, 4.0},
	{10.0, 0.0, 178.0, 10.0, -14.0, 222.0, 9.0, 4.0},
	{-214.0, -4.0, 258.0, -236.0, -14.0, 268.0, 7.0, 4.0},
	{-20.0, 0.0, 74.0, -20.0, 16.0, 30.0, 12.0, 4.0},
	{42.0, 16.0, -48.0, 0.0, 30.0, -56.0, 11.0, 4.0},
	{52.0, 16.0, -18.0, 134.0, 8.0, -4.0, 10.0, 4.0},
	{-78.0, 16.0, -88.0, -122.0, 10.0, -134.0, 10.0, 4.0},
	{40.0, 16.0, -92.0, 112.0, -6.0, -140.0, 12.0, 4.0},
	{202.0, 0.0, -100.0, 190.0, -6.0, -124.0, 10.0, 4.0},
	{-108.0, 0.0, 80.0, -146.0, 12.0, 78.0, 11.0, 4.0},
	{-122.0, 0.0, -42.0, -96.0, 16.0, -42.0, 12.0, 4.0},
	{-30.0, 16.0, -8.0, -30.0, 30.0, -33.0, 10.0, 4.0},
	{188.0, 0.0, 104.0, 188.0, 8.0, 78.0, 14.0, 4.0},
	{-168.0, 0.0, -96.0, -168.0, 10.0, -124.0, 14.0, 4.0},
	{-179.5, 11.3, -190.0, -168.5, 11.3, -190.0, 4.8, 1.2},
	{-180.1, 12.6, -193.6, -169.8, 12.6, -197.4, 4.8, 1.2},
	{-182.0, 13.9, -196.7, -173.5, 13.9, -203.8, 4.8, 1.2},
	{-184.8, 15.2, -199.1, -179.2, 15.2, -208.6, 4.8, 1.2},
	{-188.2, 16.5, -200.3, -186.3, 16.5, -211.2, 4.8, 1.2},
	{-191.8, 17.8, -200.3, -193.7, 17.8, -211.2, 4.8, 1.2},
	{-195.2, 19.1, -199.1, -200.8, 19.1, -208.6, 4.8, 1.2},
	{-198.0, 20.4, -196.7, -206.5, 20.4, -203.8, 4.8, 1.2},
	{-199.9, 21.7, -193.6, -210.2, 21.7, -197.4, 4.8, 1.2},
	{-200.5, 23.0, -190.0, -211.5, 23.0, -190.0, 4.8, 1.2},
	{-199.9, 24.3, -186.4, -210.2, 24.3, -182.6, 4.8, 1.2},
	{-198.0, 25.6, -183.3, -206.5, 25.6, -176.2, 4.8, 1.2},
	{-195.2, 26.9, -180.9, -200.8, 26.9, -171.4, 4.8, 1.2},
	{-191.8, 28.2, -179.7, -193.7, 28.2, -168.8, 4.8, 1.2},
	{-188.2, 29.5, -179.7, -186.3, 29.5, -168.8, 4.8, 1.2},
	{-184.8, 30.8, -180.9, -179.2, 30.8, -171.4, 4.8, 1.2},
	{-182.0, 32.1, -183.3, -173.5, 32.1, -176.2, 4.8, 1.2},
	{-180.1, 33.4, -186.4, -169.8, 33.4, -182.6, 4.8, 1.2},
	{-179.5, 34.7, -190.0, -168.5, 34.7, -190.0, 4.8, 1.2},
	{-180.1, 36.0, -193.6, -169.8, 36.0, -197.4, 4.8, 1.2},
	{-182.0, 37.3, -196.7, -173.5, 37.3, -203.8, 4.8, 1.2},
	{-184.8, 38.6, -199.1, -179.2, 38.6, -208.6, 4.8, 1.2},
	{-188.2, 39.9, -200.3, -186.3, 39.9, -211.2, 4.8, 1.2},
	{-191.8, 41.2, -200.3, -193.7, 41.2, -211.2, 4.8, 1.2},
	{-195.2, 42.5, -199.1, -200.8, 42.5, -208.6, 4.8, 1.2},
	{-198.0, 43.8, -196.7, -206.5, 43.8, -203.8, 4.8, 1.2},
	{-199.9, 45.1, -193.6, -210.2, 45.1, -197.4, 4.8, 1.2},
	{-200.5, 46.4, -190.0, -211.5, 46.4, -190.0, 4.8, 1.2},
	{-199.9, 47.7, -186.4, -210.2, 47.7, -182.6, 4.8, 1.2},
	{-198.0, 49.0, -183.3, -206.5, 49.0, -176.2, 4.8, 1.2},
	{-195.2, 50.3, -180.9, -200.8, 50.3, -171.4, 4.8, 1.2},
	{-191.8, 51.6, -179.7, -193.7, 51.6, -168.8, 4.8, 1.2},
	{-188.2, 52.9, -179.7, -186.3, 52.9, -168.8, 4.8, 1.2},
	{-184.8, 54.2, -180.9, -179.2, 54.2, -171.4, 4.8, 1.2},
	{-182.0, 55.5, -183.3, -173.5, 55.5, -176.2, 4.8, 1.2},
	{-180.1, 56.8, -186.4, -169.8, 56.8, -182.6, 4.8, 1.2},
	{-170.0, 58.1, -183.5, -158.0, 58.1, -183.5, 6.3, 3.0},
	{-176.0, 58.1, -189.5, -152.0, 58.1, -189.5, 6.3, 3.0},
	{-170.0, 58.1, -195.5, -158.0, 58.1, -195.5, 6.3, 3.0},
}
local collisionFolder = Instance.new("Folder")
collisionFolder.Name = "Collisions"
collisionFolder.Parent = m
for i, c in COLLISIONS do
	local a = transform(c[1], c[2], c[3])
	local b = transform(c[4], c[5], c[6])
	local width, thickness = c[7] * k, c[8] * k
	local length = (b - a).Magnitude
	if length > 0.05 then
		local p = Instance.new("Part")
		p.Name = "Sol_" .. i
		p.Anchored = true
		p.Transparency = 1
		p.CanCollide = true
		p.CastShadow = false
		p.Size = Vector3.new(width, thickness, length)
		p.CFrame = CFrame.lookAt((a + b) / 2, b) * CFrame.new(0, -thickness / 2, 0)
		p.Parent = collisionFolder
	end
end
print("✅ " .. #COLLISIONS .. " surfaces de collision créées")

-- Spawn on the golden island, facing the middle of the map
local spawn = m:FindFirstChild("SpawnVoid") or Instance.new("SpawnLocation")
spawn.Name = "SpawnVoid"
spawn.Anchored = true
spawn.Transparency = 1
spawn.CanCollide = false
spawn.Neutral = true
spawn.Duration = 0
spawn.Enabled = true
spawn.Size = Vector3.new(10, 1, 10)
local spawnPos = transform(SPAWN.X, SPAWN.Y, SPAWN.Z) + Vector3.new(0, 0.6, 0)
local lookAt = transform(0, SPAWN.Y, 0)
spawn.CFrame = CFrame.lookAt(spawnPos, Vector3.new(lookAt.X, spawnPos.Y, lookAt.Z))
spawn.Parent = m
for _, s in workspace:GetDescendants() do
	if s:IsA("SpawnLocation") and s ~= spawn then
		s.Enabled = false
	end
end
local baseplate = workspace:FindFirstChild("Baseplate")
if baseplate and (baseplate.Position - ZONE_CENTER).Magnitude < 800 then
	baseplate:Destroy()
end

-- 4. Parts: neon, texture, collisions -------------------------------------------------------
local NEON = {
	Neon_arche = Color3.fromRGB(206, 150, 255),
	Neon_cyan = Color3.fromRGB(60, 230, 255),
	Neon_magenta = Color3.fromRGB(255, 60, 200),
	Neon_pink = Color3.fromRGB(255, 120, 200),
	Neon_vein = Color3.fromRGB(120, 255, 110),
	Neon_bridge = Color3.fromRGB(196, 120, 255),
	Neon_water = Color3.fromRGB(96, 240, 255),
	Neon_mushroom = Color3.fromRGB(150, 232, 214),
	Neon_star = Color3.fromRGB(255, 255, 255),
	Neon_gold = Color3.fromRGB(255, 208, 60),
	Neon_amethyst = Color3.fromRGB(190, 110, 255),
	Star_Socle = Color3.fromRGB(255, 208, 60),
}
local NO_COLLISION = { "^Sol_", "^Decor_Sky", "^Decor_Hole" } -- floors (handled above) and far decor
local function noCollision(name)
	for _, pattern in NO_COLLISION do
		if name:match(pattern) then
			return true
		end
	end
	return false
end
for _, p in m:GetDescendants() do
	if p:IsA("BasePart") and p.Parent ~= collisionFolder and p ~= spawn then
		local prefix = p.Name:match("^(Neon_%a+)") or p.Name
		if NEON[prefix] then
			pcall(function()
				p.TextureID = ""
			end)
			p.Color = NEON[prefix]
			p.Material = Enum.Material.Neon
			p.CastShadow = false
			p.CanCollide = (prefix == "Star_Socle")
		else
			if TEXTURE_ID ~= "" and p:IsA("MeshPart") then
				p.TextureID = TEXTURE_ID
			end
			if noCollision(p.Name) then
				p.CanCollide = false
			else
				-- mountains, rocks, crystals: nobody walks through them
				pcall(function()
					p.CollisionFidelity = Enum.CollisionFidelity.PreciseConvexDecomposition
				end)
				p.CanCollide = true
			end
		end
	end
end

-- 5. Ambience: violet night, starry sky --------------------------------------------------------
for _, e in Lighting:GetChildren() do
	if e:IsA("Atmosphere") or e:IsA("Sky") or e:IsA("PostEffect") then
		e:Destroy()
	end
end
pcall(function()
	Lighting.Technology = Enum.Technology.Future
end)
Lighting.ClockTime = 0
Lighting.Brightness = 1.2
Lighting.Ambient = Color3.fromRGB(64, 36, 110)
Lighting.OutdoorAmbient = Color3.fromRGB(96, 64, 150)
Lighting.ColorShift_Top = Color3.fromRGB(190, 140, 255)
Lighting.EnvironmentDiffuseScale = 0.5
Lighting.EnvironmentSpecularScale = 0.6
local sky = Instance.new("Sky")
sky.Name = "VoidSky"
sky.StarCount = 6000
sky.CelestialBodiesShown = false
sky.Parent = Lighting
local atmosphere = Instance.new("Atmosphere")
atmosphere.Name = "VoidAtmosphere"
atmosphere.Density = 0.3
atmosphere.Offset = 0.05
atmosphere.Color = Color3.fromRGB(120, 70, 200)
atmosphere.Decay = Color3.fromRGB(40, 12, 90)
atmosphere.Glare = 0.4
atmosphere.Haze = 1.2
atmosphere.Parent = Lighting
local colors = Instance.new("ColorCorrectionEffect")
colors.Name = "VoidColors"
colors.Saturation = 0.25
colors.Contrast = 0.12
colors.TintColor = Color3.fromRGB(236, 220, 255)
colors.Parent = Lighting
local bloom = Instance.new("BloomEffect")
bloom.Name = "VoidBloom"
bloom.Intensity = 1
bloom.Size = 32
bloom.Threshold = 0.85
bloom.Parent = Lighting

-- 6. Lights (positions exported from Blender) ------------------------------------------------
-- {x, y, z, r, g, b, power, object carrying the light (moves with it) or "", pulse}
local LIGHTS = {
	{-20.0, 24.0, -42.0, 114, 255, 114, 7000, "", 0.35},
	{-75.0, 24.0, -60.0, 114, 255, 114, 7000, "", 0.35},
	{22.0, 24.0, -18.0, 114, 255, 114, 7000, "", 0.35},
	{-10.0, 24.0, -95.0, 114, 255, 114, 7000, "", 0.35},
	{-30.1, 47.0, -55.9, 102, 255, 153, 14000, "Decor_Sky_GemSummit", 0.00},
	{-68.0, 37.6, -70.0, 183, 102, 255, 4000, "", 0.00},
	{22.0, 34.0, -88.0, 183, 102, 255, 4000, "", 0.00},
	{-72.0, 31.6, -20.0, 183, 102, 255, 4000, "", 0.00},
	{-177.9, 18.0, 78.1, 102, 224, 255, 6000, "", 0.50},
	{160.0, -45.0, -172.0, 255, 102, 204, 20000, "", 0.40},
	{160.0, 19.0, -172.0, 183, 102, 255, 30000, "", 0.00},
	{130.0, 6.0, -147.0, 255, 102, 204, 8000, "", 0.00},
	{-279.2, 87.7, -60.9, 102, 224, 255, 7000, "", 0.00},
	{-281.3, 79.2, 70.3, 183, 102, 255, 7000, "", 0.00},
	{-289.0, 63.6, -127.9, 102, 224, 255, 7000, "", 0.00},
	{-321.9, 39.5, 57.1, 183, 102, 255, 3500, "", 0.50},
	{-279.8, 46.2, 55.4, 183, 102, 255, 3500, "", 0.50},
	{-280.7, 117.7, -235.8, 255, 89, 178, 7000, "", 0.00},
	{-252.4, 66.2, -265.8, 183, 102, 255, 7000, "", 0.00},
	{-261.9, 57.0, -259.1, 183, 102, 255, 3500, "", 0.50},
	{-282.6, 65.8, -274.3, 183, 102, 255, 3500, "", 0.50},
	{-218.4, 90.0, -289.6, 255, 89, 178, 7000, "", 0.00},
	{33.0, 81.7, -292.6, 183, 102, 255, 7000, "", 0.00},
	{-152.0, 69.8, -296.4, 183, 102, 255, 7000, "", 0.00},
	{-87.2, 28.1, -292.1, 183, 102, 255, 3500, "", 0.50},
	{44.2, 33.1, -325.1, 183, 102, 255, 3500, "", 0.50},
	{281.3, 77.0, 65.6, 102, 255, 153, 7000, "", 0.00},
	{282.8, 78.1, -56.6, 102, 255, 153, 7000, "", 0.00},
	{293.2, 68.2, 4.7, 102, 255, 153, 7000, "", 0.00},
	{327.0, 42.9, 74.8, 102, 255, 153, 3500, "", 0.50},
	{307.1, 37.2, 32.5, 102, 255, 153, 3500, "", 0.50},
	{-178.0, 4.0, 238.0, 255, 209, 89, 20000, "", 0.00},
	{-178.0, 17.0, 238.0, 255, 209, 89, 5000, "Neon_gold_star", 0.00},
	{-163.0, -1.0, 228.0, 255, 209, 89, 6000, "", 0.00},
	{122.0, -2.0, 238.0, 183, 102, 255, 5000, "", 0.00},
	{150.0, -2.0, 238.0, 183, 102, 255, 5000, "", 0.00},
	{178.0, -2.0, 238.0, 183, 102, 255, 5000, "", 0.00},
	{110.0, -4.0, 225.0, 102, 255, 216, 2500, "", 0.40},
	{195.0, -4.0, 225.0, 102, 255, 216, 2500, "", 0.40},
	{150.0, -4.0, 265.0, 102, 255, 216, 2500, "", 0.40},
	{10.0, -6.0, 250.0, 76, 229, 255, 7000, "", 0.00},
	{-252.0, -9.0, 276.0, 76, 229, 255, 3000, "", 0.00},
	{-155.0, 2.0, 187.5, 183, 102, 255, 1500, "", 0.00},
	{150.0, -1.0, 182.0, 183, 102, 255, 1500, "", 0.00},
	{10.0, -3.0, 200.0, 183, 102, 255, 1500, "", 0.00},
	{-225.0, -5.0, 263.0, 183, 102, 255, 1500, "", 0.00},
	{-20.0, 12.0, 52.0, 183, 102, 255, 1500, "", 0.00},
	{21.0, 27.0, -52.0, 183, 102, 255, 1500, "", 0.00},
	{93.0, 16.0, -11.0, 183, 102, 255, 1500, "", 0.00},
	{-100.0, 17.0, -111.0, 183, 102, 255, 1500, "", 0.00},
	{76.0, 9.0, -116.0, 183, 102, 255, 1500, "", 0.00},
	{196.0, 1.0, -112.0, 183, 102, 255, 1500, "", 0.00},
	{-127.0, 10.0, 79.0, 183, 102, 255, 1500, "", 0.00},
	{-190.0, 40.0, -190.0, 183, 102, 255, 6000, "", 0.00},
	{-165.0, 69.2, -190.0, 255, 209, 89, 6000, "Decor_Sky_GemBelvedere", 0.00},
	{-214.0, 5.0, 8.0, 183, 102, 255, 2500, "", 0.50},
	{-52.0, 5.0, -222.0, 183, 102, 255, 2500, "", 0.50},
	{222.0, 5.0, 104.0, 102, 224, 255, 2500, "", 0.50},
	{-108.0, 29.2, 140.0, 102, 224, 255, 3000, "", 0.00},
	{80.0, 29.2, 112.0, 183, 102, 255, 3000, "", 0.00},
	{-228.0, 18.2, 120.0, 183, 102, 255, 3000, "", 0.00},
	{-222.0, 21.0, -60.0, 102, 224, 255, 3000, "", 0.00},
	{-215.0, 14.0, -120.0, 183, 102, 255, 3000, "", 0.00},
	{220.0, 16.8, 140.0, 102, 255, 153, 3000, "", 0.00},
	{225.0, 19.6, -80.0, 183, 102, 255, 3000, "", 0.00},
	{-120.0, 11.2, 150.0, 183, 102, 255, 3000, "", 0.00},
	{90.0, 12.6, 150.0, 102, 224, 255, 3000, "", 0.00},
	{70.0, 16.8, -200.0, 255, 89, 178, 3000, "", 0.00},
	{-60.0, 15.4, -210.0, 183, 102, 255, 3000, "", 0.00},
	{120.0, 11.2, -100.0, 183, 102, 255, 3000, "", 0.00},
	{190.0, 20.0, 10.0, 183, 102, 255, 4000, "", 0.00},
	{-165.0, 22.0, -150.0, 183, 102, 255, 4000, "", 0.00},
	{-230.0, 33.1, -40.0, 255, 102, 204, 1200, "Neon_magenta_glitch_1", 0.00},
	{-150.0, 72.4, -280.0, 76, 229, 255, 1200, "Neon_magenta_glitch_2", 0.00},
	{290.0, 43.0, -150.0, 76, 229, 255, 1200, "Neon_magenta_glitch_3", 0.00},
	{270.0, 93.4, -260.0, 76, 229, 255, 1200, "Neon_magenta_glitch_4", 0.00},
	{-120.0, 23.6, 290.0, 255, 102, 204, 1200, "Neon_magenta_glitch_5", 0.00},
	{60.0, 53.4, -290.0, 76, 229, 255, 1200, "Neon_magenta_glitch_6", 0.00},
	{-200.0, 14.9, 300.0, 76, 229, 255, 1200, "Neon_magenta_glitch_7", 0.00},
	{290.0, 27.8, 240.0, 76, 229, 255, 1200, "Neon_magenta_glitch_8", 0.00},
	{-300.0, 177.8, -252.0, 183, 102, 255, 12000, "Decor_Sky_GemPeak", 0.00},
	{-298.0, 122.2, -65.0, 102, 224, 255, 12000, "Decor_Sky_GemLeft", 0.00},
	{-230.0, 137.4, -305.0, 255, 89, 178, 12000, "Decor_Sky_GemBack", 0.00},
	{300.0, 115.3, 70.0, 102, 255, 153, 12000, "Decor_Sky_GemRight", 0.00},
	{-385.0, 80.0, 60.0, 102, 224, 255, 3500, "Decor_Sky_Island_1", 0.00},
	{-362.0, 120.0, -170.0, 183, 102, 255, 3500, "Decor_Sky_Island_2", 0.00},
	{-200.0, 140.0, -382.0, 255, 89, 178, 3500, "Decor_Sky_Island_3", 0.00},
	{40.0, 128.0, -386.0, 183, 102, 255, 3500, "Decor_Sky_Island_4", 0.00},
	{305.0, 45.0, -232.0, 183, 102, 255, 3500, "Decor_Sky_Island_5", 0.00},
	{238.0, 82.0, -338.0, 255, 89, 178, 3500, "Decor_Sky_Island_6", 0.00},
	{382.0, 70.0, 120.0, 102, 255, 153, 3500, "Decor_Sky_Island_7", 0.00},
	{332.0, 40.0, 270.0, 102, 224, 255, 3500, "Decor_Sky_Island_8", 0.00},
	{-332.0, 45.0, 272.0, 183, 102, 255, 3500, "Decor_Sky_Island_9", 0.00},
	{122.0, 22.0, 332.0, 255, 209, 89, 3500, "Decor_Sky_Island_10", 0.00},
	{185.0, 118.0, -212.0, 183, 102, 255, 60000, "Decor_Sky_Brain", 0.00},
	{185.0, 64.0, -212.0, 255, 102, 204, 20000, "Decor_Sky_Brain", 0.00},
}
local lightFolder = Instance.new("Folder")
lightFolder.Name = "Lights"
lightFolder.Parent = m
for i, L in LIGHTS do
	local pos = transform(L[1], L[2], L[3])
	local host = if L[8] ~= "" then m:FindFirstChild(L[8], true) else nil
	local holder: Instance
	if host and host:IsA("BasePart") then
		-- carried by a moving object: the light follows it
		local attachment = Instance.new("Attachment")
		attachment.Name = "MapLight"
		attachment.Position = host.CFrame:PointToObjectSpace(pos)
		attachment.Parent = host
		holder = attachment
	else
		local support = Instance.new("Part")
		support.Name = "Light_" .. i
		support.Size = Vector3.new(0.5, 0.5, 0.5)
		support.Transparency = 1
		support.Anchored = true
		support.CanCollide = false
		support.CanQuery = false
		support.CanTouch = false
		support.Position = pos
		support.Parent = lightFolder
		if L[9] > 0 then
			support:SetAttribute("LifePulse", L[9])
			support:SetAttribute("LifePeriod", 2.5 + (i % 7) * 0.45)
			support:SetAttribute("LifePhase", (i * 0.37) % 1)
			CollectionService:AddTag(support, "MapLife")
		end
		holder = support
	end
	local pl = Instance.new("PointLight")
	pl.Color = Color3.fromRGB(L[4], L[5], L[6])
	pl.Brightness = math.clamp(L[7] / 2500, 0.8, 6)
	pl.Range = math.clamp(math.sqrt(L[7]) / 2 * k, 8, 60)
	pl.Shadows = L[7] >= 15000
	pl.Parent = holder
end
print("✅ " .. #LIGHTS .. " lumières")

-- 7. Living objects (animated by the MapLife LocalScript) ---------------------------------------
local LIFE = {
	{ name = "Neon_vein_hill", period = 3.50, phase = 0.184, pulse = 0.50 },
	{ name = "Decor_Sky_GemSummit", period = 5.46, phase = 0.235, bob = 1.50, spin = 0.6000, axis = {0.000, 1.000, -0.000}, pivot = {-30.15, 45.00, -55.94}, pulse = 0.45 },
	{ name = "Neon_magenta_hole", period = 2.80, phase = 0.230, spin = 0.2200, axis = {0.000, 1.000, -0.000}, pivot = {160.00, -58.00, -172.00}, pulse = 0.35 },
	{ name = "Neon_cyan_hole", period = 3.60, phase = 0.318, spin = -0.3800, axis = {0.000, 1.000, -0.000}, pivot = {160.00, -58.00, -172.00}, pulse = 0.35 },
	{ name = "Neon_pink_hole", period = 1.80, phase = 0.078, pulse = 0.60 },
	{ name = "Decor_Sky_HoleShards", period = 6.00, phase = 0.636, spin = 0.1600, axis = {0.000, 1.000, -0.000}, pivot = {160.00, -30.00, -172.00} },
	{ name = "Neon_pink_arena", period = 4.00, phase = 0.597, spin = 0.0500, axis = {0.000, 1.000, -0.000}, pivot = {160.00, -3.00, -172.00}, pulse = 0.30 },
	{ name = "Neon_cyan_arena", period = 4.00, phase = 0.614, spin = -0.0400, axis = {0.000, 1.000, -0.000}, pivot = {160.00, -3.00, -172.00}, pulse = 0.30 },
	{ name = "Neon_cyan_MassifLeft", period = 3.31, phase = 0.645, pulse = 0.55 },
	{ name = "Neon_magenta_MassifCorner", period = 3.93, phase = 0.499, pulse = 0.55 },
	{ name = "Neon_amethyst_MassifBack", period = 3.03, phase = 0.783, pulse = 0.55 },
	{ name = "Neon_vein_MassifRight", period = 3.73, phase = 0.783, pulse = 0.55 },
	{ name = "Neon_gold_star", period = 3.20, phase = 0.766, bob = 0.60, spin = 0.8000, axis = {0.000, 1.000, -0.000}, pivot = {-178.00, 17.00, 238.00}, pulse = 0.30 },
	{ name = "Neon_mushroom", period = 4.50, phase = 0.436, pulse = 0.45 },
	{ name = "Neon_water", period = 2.60, phase = 0.168, pulse = 0.35 },
	{ name = "Neon_bridge", period = 4.00, phase = 0.021, pulse = 0.25 },
	{ name = "Decor_Sky_OrbitTower", period = 6.00, phase = 0.573, bob = 0.80, spin = 0.3000, axis = {0.000, 1.000, -0.000}, pivot = {-190.00, 68.00, -190.00} },
	{ name = "Decor_Sky_GemBelvedere", period = 8.00, phase = 0.533, bob = 1.50, spin = 0.9000, axis = {0.000, 1.000, -0.000}, pivot = {-165.00, 68.10, -190.00}, pulse = 0.45 },
	{ name = "Neon_cyan_circuit", period = 5.00, phase = 0.077, pulse = 0.30 },
	{ name = "Neon_amethyst_fissure", period = 3.20, phase = 0.356, pulse = 0.55 },
	{ name = "Neon_cyan_fissure", period = 2.90, phase = 0.182, pulse = 0.55 },
	{ name = "Decor_Sky_Eye_1", period = 6.69, phase = 0.586, bob = 1.73, pivot = {-150.00, 60.00, -110.00}, look = {0.000, -0.159, 0.987} },
	{ name = "Decor_Sky_Eye_2", period = 7.71, phase = 0.217, bob = 1.15, pivot = {-95.00, 75.00, -160.00}, look = {-0.149, -0.176, 0.973} },
	{ name = "Decor_Sky_Eye_3", period = 5.76, phase = 0.564, bob = 1.34, pivot = {-215.00, 50.00, -160.00}, look = {0.177, -0.109, 0.978} },
	{ name = "Decor_Sky_Eye_4", period = 5.87, phase = 0.102, bob = 1.54, pivot = {240.00, 45.00, -180.00}, look = {-0.715, -0.064, 0.696} },
	{ name = "Decor_Sky_Eye_5", period = 7.74, phase = 0.140, bob = 0.96, pivot = {-40.00, 90.00, -140.00}, look = {-0.300, -0.218, 0.928} },
	{ name = "Decor_Sky_Eye_6", period = 6.21, phase = 0.990, bob = 1.15, pivot = {60.00, 70.00, 40.00}, look = {-0.776, -0.222, 0.591} },
	{ name = "Decor_Sky_Eye_7", period = 5.45, phase = 0.760, bob = 1.34, pivot = {262.00, 60.00, 20.00}, look = {-0.911, -0.111, 0.398} },
	{ name = "Decor_Sky_Eye_8", period = 6.97, phase = 0.727, bob = 1.15, pivot = {-270.00, 40.00, 150.00}, look = {0.899, -0.225, 0.375} },
	{ name = "Decor_Sky_Lips_1", period = 5.70, phase = 0.562, bob = 1.50, pivot = {-190.00, 45.00, -60.00}, sway = 0.120 },
	{ name = "Decor_Sky_Lips_2", period = 4.35, phase = 0.480, bob = 1.50, pivot = {90.00, 60.00, -170.00}, sway = 0.120 },
	{ name = "Decor_Sky_Lips_3", period = 4.08, phase = 0.995, bob = 1.50, pivot = {250.00, 35.00, 80.00}, sway = 0.120 },
	{ name = "Decor_Sky_Lips_4", period = 5.06, phase = 0.108, bob = 1.50, pivot = {-60.00, 55.00, 120.00}, sway = 0.120 },
	{ name = "Decor_Sky_Planet_1", period = 11.42, phase = 0.274, bob = 2.00, spin = 0.1000, axis = {0.241, 0.966, -0.097}, pivot = {-110.00, 95.00, -260.00} },
	{ name = "Decor_Sky_Planet_2", period = 11.80, phase = 0.539, bob = 2.00, spin = 0.1000, axis = {0.241, 0.966, -0.097}, pivot = {40.00, 120.00, -240.00} },
	{ name = "Decor_Sky_Planet_3", period = 10.44, phase = 0.329, bob = 2.00, spin = 0.1000, axis = {0.241, 0.966, -0.097}, pivot = {280.00, 90.00, -120.00} },
	{ name = "Decor_Sky_Planet_4", period = 10.21, phase = 0.332, bob = 2.00, spin = 0.1000, axis = {0.241, 0.966, -0.097}, pivot = {-250.00, 110.00, -230.00} },
	{ name = "Decor_Sky_Ring_1", period = 8.80, phase = 0.238, bob = 1.50, spin = 0.4876, axis = {-0.579, 0.369, -0.727}, pivot = {-140.00, 80.00, -190.00} },
	{ name = "Decor_Sky_Ring_2", period = 7.33, phase = 0.722, bob = 1.50, spin = 0.4334, axis = {-0.496, 0.500, 0.710}, pivot = {-70.00, 55.00, -150.00} },
	{ name = "Decor_Sky_Ring_3", period = 8.05, phase = 0.863, bob = 1.50, spin = 0.4988, axis = {0.588, 0.636, -0.499}, pivot = {60.00, 45.00, -150.00} },
	{ name = "Decor_Sky_Ring_4", period = 7.79, phase = 0.866, bob = 1.50, spin = 0.4673, axis = {-0.019, 0.939, 0.343}, pivot = {-200.00, 60.00, 60.00} },
	{ name = "Decor_Sky_Ring_5", period = 8.33, phase = 0.189, bob = 1.50, spin = 0.3719, axis = {-0.609, 0.557, 0.565}, pivot = {240.00, 60.00, 180.00} },
	{ name = "Decor_Sky_Cube_1", period = 6.25, phase = 0.052, bob = 1.68, spin = 0.7109, axis = {-0.204, 0.644, -0.737}, pivot = {-10.79, 44.89, -167.90} },
	{ name = "Decor_Sky_Cube_2", period = 7.22, phase = 0.205, bob = 1.74, spin = 0.6989, axis = {-0.516, 0.518, -0.682}, pivot = {142.65, 92.25, -17.76} },
	{ name = "Decor_Sky_Cube_3", period = 7.01, phase = 0.888, bob = 2.30, spin = 0.6738, axis = {0.075, 0.684, -0.725}, pivot = {59.23, 97.37, -0.58} },
	{ name = "Decor_Sky_Cube_4", period = 6.96, phase = 0.830, bob = 2.43, spin = 0.4847, axis = {0.528, 0.732, 0.431}, pivot = {-241.13, 62.49, -85.17} },
	{ name = "Neon_cyan_cube_5", period = 8.13, phase = 0.470, bob = 1.54, spin = 0.5314, axis = {0.246, 0.670, -0.700}, pivot = {12.23, 84.28, -226.89} },
	{ name = "Decor_Sky_Cube_6", period = 5.08, phase = 0.057, bob = 1.42, spin = 0.7781, axis = {-0.838, 0.486, -0.248}, pivot = {147.71, 57.65, 216.65} },
	{ name = "Decor_Sky_Cube_7", period = 6.41, phase = 0.111, bob = 1.70, spin = 0.8121, axis = {0.833, 0.104, -0.543}, pivot = {-152.64, 92.27, -153.19} },
	{ name = "Decor_Sky_Cube_8", period = 6.47, phase = 0.455, bob = 1.40, spin = 0.8437, axis = {-0.725, -0.385, -0.571}, pivot = {59.73, 44.34, 66.59} },
	{ name = "Neon_cyan_cube_9", period = 7.41, phase = 0.200, bob = 1.33, spin = 0.6156, axis = {0.295, 0.696, 0.654}, pivot = {-163.73, 73.91, -67.55} },
	{ name = "Decor_Sky_Cube_10", period = 5.75, phase = 0.167, bob = 1.26, spin = 0.8091, axis = {0.145, -0.571, -0.808}, pivot = {-121.56, 55.80, 53.72} },
	{ name = "Decor_Sky_Cube_11", period = 8.63, phase = 0.318, bob = 1.29, spin = 0.6716, axis = {0.781, 0.554, 0.290}, pivot = {-248.45, 76.91, -188.76} },
	{ name = "Neon_cyan_cube_12", period = 7.68, phase = 0.705, bob = 1.92, spin = 0.7735, axis = {0.629, 0.771, 0.098}, pivot = {-161.35, 33.63, 220.58} },
	{ name = "Neon_cyan_cube_13", period = 8.44, phase = 0.068, bob = 1.39, spin = 0.8395, axis = {0.844, 0.536, -0.003}, pivot = {25.84, 95.29, -55.08} },
	{ name = "Decor_Sky_Cube_14", period = 7.04, phase = 0.743, bob = 1.76, spin = 0.4802, axis = {0.376, -0.071, -0.924}, pivot = {133.04, 94.98, 44.89} },
	{ name = "Decor_Sky_Cube_15", period = 8.94, phase = 0.754, bob = 1.25, spin = 0.6494, axis = {0.368, -0.148, -0.918}, pivot = {-138.79, 76.52, 20.49} },
	{ name = "Neon_cyan_cube_16", period = 8.02, phase = 0.957, bob = 1.24, spin = 0.8192, axis = {-0.088, 0.771, 0.631}, pivot = {257.90, 38.99, 182.93} },
	{ name = "Decor_Sky_Cube_17", period = 5.47, phase = 0.945, bob = 2.39, spin = 0.8055, axis = {0.196, 0.811, -0.552}, pivot = {129.44, 52.67, 253.59} },
	{ name = "Decor_Sky_Cube_18", period = 6.55, phase = 0.252, bob = 2.20, spin = 0.7926, axis = {0.841, 0.346, 0.416}, pivot = {278.51, 47.34, -11.29} },
	{ name = "Neon_magenta_glitch_1", period = 3.42, phase = 0.566, bob = 0.50, pivot = {-230.00, 30.00, -40.00}, glitch = true },
	{ name = "Neon_cyan_glitch_1", period = 2.78, phase = 0.469, bob = 0.50, pivot = {-230.00, 30.00, -40.00}, glitch = true },
	{ name = "Neon_magenta_glitch_2", period = 3.98, phase = 0.856, bob = 0.50, pivot = {-150.00, 70.00, -280.00}, glitch = true },
	{ name = "Neon_cyan_glitch_2", period = 3.91, phase = 0.509, bob = 0.50, pivot = {-150.00, 70.00, -280.00}, glitch = true },
	{ name = "Neon_magenta_glitch_3", period = 3.12, phase = 0.253, bob = 0.50, pivot = {290.00, 40.00, -150.00}, glitch = true },
	{ name = "Neon_cyan_glitch_3", period = 3.80, phase = 0.641, bob = 0.50, pivot = {290.00, 40.00, -150.00}, glitch = true },
	{ name = "Neon_magenta_glitch_4", period = 2.73, phase = 0.294, bob = 0.50, pivot = {270.00, 90.00, -260.00}, glitch = true },
	{ name = "Neon_cyan_glitch_4", period = 3.36, phase = 0.762, bob = 0.50, pivot = {270.00, 90.00, -260.00}, glitch = true },
	{ name = "Neon_magenta_glitch_5", period = 2.69, phase = 0.600, bob = 0.50, pivot = {-120.00, 20.00, 290.00}, glitch = true },
	{ name = "Neon_cyan_glitch_5", period = 2.83, phase = 0.575, bob = 0.50, pivot = {-120.00, 20.00, 290.00}, glitch = true },
	{ name = "Neon_magenta_glitch_6", period = 3.40, phase = 0.816, bob = 0.50, pivot = {60.00, 50.00, -290.00}, glitch = true },
	{ name = "Neon_cyan_glitch_6", period = 3.28, phase = 0.452, bob = 0.50, pivot = {60.00, 50.00, -290.00}, glitch = true },
	{ name = "Neon_magenta_glitch_7", period = 2.08, phase = 0.525, bob = 0.50, pivot = {-200.00, 12.00, 300.00}, glitch = true },
	{ name = "Neon_cyan_glitch_7", period = 3.32, phase = 0.883, bob = 0.50, pivot = {-200.00, 12.00, 300.00}, glitch = true },
	{ name = "Neon_magenta_glitch_8", period = 3.75, phase = 0.591, bob = 0.50, pivot = {290.00, 25.00, 240.00}, glitch = true },
	{ name = "Neon_cyan_glitch_8", period = 3.74, phase = 0.141, bob = 0.50, pivot = {290.00, 25.00, 240.00}, glitch = true },
	{ name = "Decor_Sky_GemPeak", period = 7.01, phase = 0.846, bob = 2.50, spin = 0.3500, axis = {0.000, 1.000, -0.000}, pivot = {-300.00, 174.46, -252.00}, pulse = 0.45 },
	{ name = "Decor_Sky_OrbitPeak", period = 6.00, phase = 0.686, bob = 0.80, spin = -0.2000, axis = {0.000, 1.000, -0.000}, pivot = {-300.00, 174.46, -252.00} },
	{ name = "Decor_Sky_GemLeft", period = 5.01, phase = 0.808, bob = 2.50, spin = 0.3500, axis = {0.000, 1.000, -0.000}, pivot = {-298.00, 120.15, -65.00}, pulse = 0.45 },
	{ name = "Decor_Sky_GemBack", period = 7.97, phase = 0.045, bob = 2.50, spin = 0.3500, axis = {0.000, 1.000, -0.000}, pivot = {-230.00, 135.05, -305.00}, pulse = 0.45 },
	{ name = "Decor_Sky_GemRight", period = 6.77, phase = 0.959, bob = 2.50, spin = 0.3500, axis = {0.000, 1.000, -0.000}, pivot = {300.00, 113.24, 70.00}, pulse = 0.45 },
	{ name = "Decor_Sky_Island_1", period = 10.96, phase = 0.537, bob = 3.77, pivot = {-385.00, 70.00, 60.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_2", period = 9.92, phase = 0.274, bob = 2.61, pivot = {-362.00, 110.00, -170.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_3", period = 10.25, phase = 0.594, bob = 2.95, pivot = {-200.00, 130.00, -382.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_4", period = 13.68, phase = 0.356, bob = 2.96, pivot = {40.00, 118.00, -386.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_5", period = 9.62, phase = 0.481, bob = 3.94, pivot = {305.00, 35.00, -232.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_6", period = 11.96, phase = 0.006, bob = 3.69, pivot = {238.00, 72.00, -338.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_7", period = 9.80, phase = 0.929, bob = 3.08, pivot = {382.00, 60.00, 120.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_8", period = 13.46, phase = 0.459, bob = 3.49, pivot = {332.00, 30.00, 270.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_9", period = 12.16, phase = 0.856, bob = 3.40, pivot = {-332.00, 35.00, 272.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Island_10", period = 11.12, phase = 0.203, bob = 3.05, pivot = {122.00, 12.00, 332.00}, sway = 0.025, pulse = 0.30 },
	{ name = "Decor_Sky_Brain", period = 9.00, phase = 0.000, bob = 3.00, pivot = {185.00, 118.00, -212.00} },
	{ name = "Neon_pink_brain", period = 9.00, phase = 0.000, bob = 3.00, spin = 0.1200, axis = {0.000, 1.000, -0.000}, pivot = {185.00, 118.00, -212.00}, pulse = 0.30 },
	{ name = "Neon_cyan_brain", period = 9.00, phase = 0.000, bob = 3.00, spin = -0.0900, axis = {0.000, 1.000, -0.000}, pivot = {185.00, 118.00, -212.00}, pulse = 0.30 },
	{ name = "Neon_magenta_brain", period = 9.00, phase = 0.000, bob = 3.00, spin = 0.0700, axis = {0.000, 1.000, -0.000}, pivot = {185.00, 118.00, -212.00}, pulse = 0.30 },
	{ name = "Decor_Sky_Shards_1", period = 6.00, phase = 0.658, spin = 0.0180, axis = {0.000, 1.000, -0.000}, pivot = {0.00, -30.00, 0.00} },
	{ name = "Decor_Sky_Shards_2", period = 6.00, phase = 0.063, spin = -0.0130, axis = {0.000, 1.000, -0.000}, pivot = {0.00, 50.00, 0.00} },
	{ name = "Decor_Sky_Shards_3", period = 6.00, phase = 0.918, spin = 0.0100, axis = {0.000, 1.000, -0.000}, pivot = {0.00, 130.00, 0.00} },
	{ name = "Neon_star_1", period = 2.40, phase = 0.000, pulse = 0.80 },
	{ name = "Neon_star_2", period = 3.50, phase = 0.333, pulse = 0.80 },
	{ name = "Neon_star_3", period = 4.60, phase = 0.667, pulse = 0.80 },
}
local living = 0
for _, e in LIFE do
	local p = m:FindFirstChild(e.name, true)
	if p and p:IsA("BasePart") then
		p:SetAttribute("LifeBob", (e.bob or 0) * k)
		p:SetAttribute("LifePeriod", e.period or 6)
		p:SetAttribute("LifePhase", e.phase or 0)
		p:SetAttribute("LifeSpin", e.spin or 0)
		p:SetAttribute("LifeSway", e.sway or 0)
		p:SetAttribute("LifePulse", e.pulse or 0)
		p:SetAttribute("LifeGlitch", e.glitch == true)
		p:SetAttribute("LifeAxis", worldDir(e.axis or { 0, 1, 0 }))
		p:SetAttribute("LifePivot", if e.pivot then transform(e.pivot[1], e.pivot[2], e.pivot[3]) else nil)
		p:SetAttribute("LifeLook", if e.look then worldDir(e.look) else nil)
		if e.bob or e.spin or e.sway or e.look or e.glitch then
			-- moving decor is purely visual
			p.CanCollide = false
			p.CanTouch = false
			p.CanQuery = false
		end
		CollectionService:AddTag(p, "MapLife")
		living += 1
	else
		warn("⚠️ Objet animé introuvable : " .. e.name)
	end
end
print("✅ " .. living .. " objets vivants")

-- 8. Particles ---------------------------------------------------------------------------------
-- {kind, x, y, z, size x, size y, size z, object carrying the emitter or "", r, g, b}
local PARTICLES = {
	{"vein", -20.0, 17.0, -42.0, 140.0, 2.0, 130.0, "", 114, 255, 114},
	{"sparkle", -30.1, 45.0, -55.9, 13.0, 13.0, 13.0, "Decor_Sky_GemSummit", 102, 255, 153},
	{"sparkle", -177.9, 18.0, 78.1, 10.0, 8.0, 10.0, "", 102, 224, 255},
	{"rise", 160.0, -52.0, -172.0, 130.0, 2.0, 130.0, "", 255, 89, 216},
	{"gold", -178.0, 8.0, 238.0, 18.0, 10.0, 18.0, "", 255, 209, 89},
	{"portal", 122.0, -1.0, 238.0, 12.0, 16.0, 2.0, "", 204, 153, 255},
	{"portal", 150.0, -1.0, 238.0, 12.0, 16.0, 2.0, "", 204, 153, 255},
	{"portal", 178.0, -1.0, 238.0, 12.0, 16.0, 2.0, "", 204, 153, 255},
	{"sparkle", -165.0, 68.1, -190.0, 7.0, 7.0, 7.0, "Decor_Sky_GemBelvedere", 255, 209, 89},
	{"dust", 0.0, 10.0, -20.0, 470.0, 16.0, 420.0, "", 191, 140, 255},
	{"sparkle", -300.0, 174.5, -252.0, 22.0, 22.0, 22.0, "Decor_Sky_GemPeak", 183, 102, 255},
	{"sparkle", -298.0, 120.1, -65.0, 14.0, 14.0, 14.0, "Decor_Sky_GemLeft", 102, 224, 255},
	{"sparkle", -230.0, 135.0, -305.0, 16.0, 16.0, 16.0, "Decor_Sky_GemBack", 255, 89, 178},
	{"sparkle", 300.0, 113.2, 70.0, 14.0, 14.0, 14.0, "Decor_Sky_GemRight", 102, 255, 153},
}
local function fade(peak)
	return NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.15, peak),
		NumberSequenceKeypoint.new(0.75, peak + 0.2),
		NumberSequenceKeypoint.new(1, 1),
	})
end
local FX = {
	dust = { rate = 10, life = NumberRange.new(8, 14), speed = NumberRange.new(0.3, 1.2), size = NumberSequence.new(0.35, 0.05),
		spread = Vector2.new(180, 180), accel = Vector3.new(0, 0.3, 0), shape = Enum.ParticleEmitterShape.Box, peak = 0.25 },
	rise = { rate = 14, life = NumberRange.new(4, 7), speed = NumberRange.new(5, 10), size = NumberSequence.new(0.9, 0.1),
		spread = Vector2.new(8, 8), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Cylinder, peak = 0.1 },
	portal = { rate = 6, life = NumberRange.new(1.5, 3), speed = NumberRange.new(0.5, 2), size = NumberSequence.new(0.5, 0),
		spread = Vector2.new(30, 30), accel = Vector3.new(0, 1, 0), shape = Enum.ParticleEmitterShape.Box, peak = 0 },
	gold = { rate = 6, life = NumberRange.new(2, 3), speed = NumberRange.new(2, 4), size = NumberSequence.new(0.6, 0),
		spread = Vector2.new(25, 25), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Box, peak = 0 },
	vein = { rate = 6, life = NumberRange.new(2, 4), speed = NumberRange.new(1, 2.5), size = NumberSequence.new(0.5, 0),
		spread = Vector2.new(15, 15), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Box, peak = 0.1 },
	sparkle = { rate = 5, life = NumberRange.new(0.8, 1.8), speed = NumberRange.new(0.5, 2), size = NumberSequence.new(0.7, 0),
		spread = Vector2.new(180, 180), accel = Vector3.zero, shape = Enum.ParticleEmitterShape.Box, peak = 0 },
}
local particleFolder = Instance.new("Folder")
particleFolder.Name = "Particles"
particleFolder.Parent = m
for i, P in PARTICLES do
	local spec = FX[P[1]]
	local pos = transform(P[2], P[3], P[4])
	local host = if P[8] ~= "" then m:FindFirstChild(P[8], true) else nil
	local e = Instance.new("ParticleEmitter")
	e.Name = "MapFx"
	e.Texture = "rbxasset://textures/particles/sparkles_main.dds"
	e.Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.fromRGB(P[9], P[10], P[11]))
	e.LightEmission = 1
	e.LightInfluence = 0
	e.Size = spec.size
	e.Transparency = fade(spec.peak)
	e.Lifetime = spec.life
	e.Rate = spec.rate
	e.Speed = spec.speed
	e.SpreadAngle = spec.spread
	e.Acceleration = spec.accel
	e.Rotation = NumberRange.new(0, 360)
	e.RotSpeed = NumberRange.new(-60, 60)
	e.EmissionDirection = Enum.NormalId.Top
	e.Shape = spec.shape
	e.ShapeStyle = Enum.ParticleEmitterShapeStyle.Volume
	if host and host:IsA("BasePart") then
		e.ShapeStyle = Enum.ParticleEmitterShapeStyle.Surface
		e.Parent = host
	else
		local support = Instance.new("Part")
		support.Name = "Fx_" .. i
		support.Size = Vector3.new(P[5], P[6], P[7]) * k
		support.Transparency = 1
		support.Anchored = true
		support.CanCollide = false
		support.CanQuery = false
		support.CanTouch = false
		support.CastShadow = false
		support.CFrame = CFrame.new(pos) * mapRotation
		support.Parent = particleFolder
		e.Parent = support
	end
end
print("✅ " .. #PARTICLES .. " émetteurs de particules")

-- 9. Client animation script ---------------------------------------------------------------------
local SOURCE = [==[
-- MapLife: client-side ambient animation for the Brainrot Fighter maps.
-- Animates every BasePart tagged "MapLife" on this player's screen only (nothing replicates, the
-- server never pays for it). The map installers create this LocalScript and set these attributes:
--   LifeBob (studs)   LifePeriod (s)   LifePhase (0-1)   LifeSpin (rad/s)   LifeAxis (Vector3)
--   LifePivot (Vector3)   LifeSway (rad)   LifeLook (Vector3: resting gaze, the part follows the player)
--   LifeGlitch (bool)   LifePulse (0-1: neon colour and light brightness breathing)
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local TAG = "MapLife"
local MAX_DISTANCE = 900 -- parts farther than this from the camera are left alone
local PULSE_INTERVAL = 1 / 20 -- colours and lights are refreshed 20 times per second at most
local GAZE_SPEED = 3

local movers = {}
local pulsers = {}
local clock = 0
local pulseClock = 0
local parts = {}
local frames = {}

local function rotationBetween(a, b)
	local axis = a:Cross(b)
	local dot = math.clamp(a:Dot(b), -1, 1)
	if axis.Magnitude < 1e-5 then
		if dot > 0 then
			return CFrame.identity
		end
		local other = if math.abs(a.Y) < 0.9 then Vector3.yAxis else Vector3.xAxis
		return CFrame.fromAxisAngle(a:Cross(other).Unit, math.pi)
	end
	return CFrame.fromAxisAngle(axis.Unit, math.acos(dot))
end

local function register(inst)
	if not inst:IsA("BasePart") or movers[inst] or pulsers[inst] then
		return
	end
	local period = inst:GetAttribute("LifePeriod") or 6
	local axis = inst:GetAttribute("LifeAxis") or Vector3.yAxis
	local state = {
		rest = inst.CFrame,
		pivot = inst:GetAttribute("LifePivot") or inst.Position,
		bob = inst:GetAttribute("LifeBob") or 0,
		omega = 2 * math.pi / math.max(period, 0.5),
		phase = (inst:GetAttribute("LifePhase") or 0) * 2 * math.pi,
		spin = inst:GetAttribute("LifeSpin") or 0,
		axis = if axis.Magnitude > 1e-6 then axis.Unit else Vector3.yAxis,
		sway = inst:GetAttribute("LifeSway") or 0,
		look = inst:GetAttribute("LifeLook"),
		glitch = inst:GetAttribute("LifeGlitch") == true,
		pulse = inst:GetAttribute("LifePulse") or 0,
		color = inst.Color,
		transparency = inst.Transparency,
		gaze = CFrame.identity,
		jitter = Vector3.zero,
		nextGlitch = 0,
		lights = {},
	}
	for _, d in inst:GetDescendants() do
		if d:IsA("Light") then
			table.insert(state.lights, { light = d, brightness = d.Brightness })
		end
	end
	if state.bob ~= 0 or state.spin ~= 0 or state.sway ~= 0 or state.look or state.glitch then
		movers[inst] = state
	end
	if state.pulse > 0 then
		pulsers[inst] = state
	end
end

local function unregister(inst)
	movers[inst] = nil
	pulsers[inst] = nil
end

local function focusPoint(camera)
	local character = Players.LocalPlayer.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if root then
		return root.Position + Vector3.new(0, 1.5, 0)
	end
	return camera.CFrame.Position
end

local function step(dt)
	clock += dt
	local camera = workspace.CurrentCamera
	if not camera then
		return
	end
	local eye = camera.CFrame.Position
	local target = focusPoint(camera)
	table.clear(parts)
	table.clear(frames)
	for part, s in movers do
		if (s.pivot - eye).Magnitude < MAX_DISTANCE then
			local w = clock * s.omega + s.phase
			local rot = CFrame.identity
			if s.spin ~= 0 then
				rot = CFrame.fromAxisAngle(s.axis, clock * s.spin)
			end
			if s.sway ~= 0 then
				rot = CFrame.Angles(math.sin(w * 0.8) * s.sway, 0, math.cos(w * 0.6) * s.sway) * rot
			end
			if s.look then
				local toTarget = target - s.pivot
				if toTarget.Magnitude > 1 then
					local want = rotationBetween(s.look, toTarget.Unit)
					s.gaze = s.gaze:Lerp(want, math.min(1, dt * GAZE_SPEED))
				end
				rot = s.gaze * rot
			end
			local offset = Vector3.new(0, math.sin(w) * s.bob, 0)
			if s.glitch then
				if clock >= s.nextGlitch then
					s.nextGlitch = clock + 0.05 + math.random() * 0.6
					if math.random() < 0.55 then
						s.jitter = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 3
					else
						s.jitter = Vector3.zero
					end
					part.Transparency = if math.random() < 0.2 then 1 else s.transparency
				end
				offset += s.jitter
			end
			table.insert(parts, part)
			table.insert(frames, CFrame.new(s.pivot + offset) * rot * CFrame.new(-s.pivot) * s.rest)
		end
	end
	if #parts > 0 then
		workspace:BulkMoveTo(parts, frames, Enum.BulkMoveMode.FireCFrameChanged)
	end

	pulseClock += dt
	if pulseClock < PULSE_INTERVAL then
		return
	end
	pulseClock = 0
	for part, s in pulsers do
		if (s.pivot - eye).Magnitude < MAX_DISTANCE then
			local f = 1 + s.pulse * 0.45 * math.sin(clock * s.omega + s.phase)
			if part.Material == Enum.Material.Neon then
				local c = s.color
				part.Color = Color3.new(math.min(1, c.R * f), math.min(1, c.G * f), math.min(1, c.B * f))
			end
			for _, entry in s.lights do
				entry.light.Brightness = entry.brightness * f
			end
		end
	end
end

for _, inst in CollectionService:GetTagged(TAG) do
	register(inst)
end
CollectionService:GetInstanceAddedSignal(TAG):Connect(register)
CollectionService:GetInstanceRemovedSignal(TAG):Connect(unregister)
RunService.Heartbeat:Connect(step)
]==]
local playerScripts = StarterPlayer:FindFirstChildOfClass("StarterPlayerScripts")
if playerScripts then
	local old = playerScripts:FindFirstChild("MapLife")
	if old then
		old:Destroy()
	end
	local ls = Instance.new("LocalScript")
	ls.Name = "MapLife"
	local ok = pcall(function()
		ls.Source = SOURCE
	end)
	if ok then
		ls.Parent = playerScripts
		print("✅ Script d'animation MapLife installé dans StarterPlayerScripts")
	else
		ls:Destroy()
		warn("⚠️ Impossible d'écrire le script : crée un LocalScript \"MapLife\" dans StarterPlayerScripts et colle MapLife.client.lua dedans.")
	end
else
	warn("⚠️ StarterPlayerScripts introuvable : le décor ne sera pas animé.")
end

print("✅ " .. NAME .. " prête ! Lance Play : tu apparais sur l'île dorée de l'entrée.")
