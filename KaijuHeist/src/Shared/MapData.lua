--!strict
-- GENERATED FILE - do not edit by hand.
-- Produced by KaijuHeist/blender/build_map.py; re-run that script to update.
--
-- Positions are studs in Roblox axes (Y up), matching kaiju_heist_map.glb once
-- MapService has aligned it on the world origin. Yaws are radians around Y.

local MapData = {}

-- Alignment markers baked into the GLB (see MapService).
MapData.reference = {
	origin = Vector3.new(0.00, -30.00, 0.00),
	axisX = Vector3.new(200.00, -30.00, 0.00),
	axisY = Vector3.new(0.00, -10.00, 0.00),
	markerSize = 4.00,
}

MapData.island = {
	min = Vector3.new(-440.00, -60.00, -330.00),
	max = Vector3.new(900.00, 0.00, 330.00),
}

MapData.corridor = {
	min = Vector3.new(0.00, 0.00, -56.00),
	max = Vector3.new(900.00, 0.00, 56.00),
	width = 112.00,
}

-- The bar of the T: spawns, portals, shops, bases. `index` 0 sorts it first.
MapData.lobby = {
	id = "lobby",
	label = "Lobby",
	index = 0,
	color = Color3.fromRGB(166, 76, 255),
	bounds = {
		min = Vector3.new(-440.00, 0.00, -330.00),
		max = Vector3.new(0.00, 0.00, 330.00),
	},
	center = Vector3.new(-151.00, 0.05, 0.00),
	spawns = {
		Vector3.new(-97.41, 0.05, -22.20),
		Vector3.new(-128.80, 0.05, -53.59),
		Vector3.new(-173.20, 0.05, -53.59),
		Vector3.new(-204.59, 0.05, -22.20),
		Vector3.new(-204.59, 0.05, 22.20),
		Vector3.new(-173.20, 0.05, 53.59),
		Vector3.new(-128.80, 0.05, 53.59),
		Vector3.new(-97.41, 0.05, 22.20),
	},
	spawnYaw = -1.5708,
	leaderboard = {
		position = Vector3.new(-151.00, 21.00, 198.70),
		width = 60.00,
		height = 30.00,
		yaw = 0.0000,
	},
	tutorialBoard = {
		position = Vector3.new(-251.00, 14.00, 149.30),
		width = 34.00,
		height = 20.00,
		yaw = 0.0000,
	},
	shop = {
		position = Vector3.new(-40.00, 0.00, -95.00),
		yaw = -3.1416,
	},
	speedShop = {
		position = Vector3.new(-40.00, 0.00, 95.00),
		yaw = 0.0000,
	},
	dailyReward = Vector3.new(-51.00, 0.00, 150.00),
	statue = Vector3.new(-151.00, 13.40, 0.00),
	showcase = {
		{
			rarity = "Common",
			position = Vector3.new(-235.00, 12.00, -238.00),
		},
		{
			rarity = "Rare",
			position = Vector3.new(-193.00, 12.00, -238.00),
		},
		{
			rarity = "Epic",
			position = Vector3.new(-151.00, 12.00, -238.00),
		},
		{
			rarity = "Legendary",
			position = Vector3.new(-109.00, 12.00, -238.00),
		},
		{
			rarity = "Mythic",
			position = Vector3.new(-67.00, 12.00, -238.00),
		},
	},
}

-- Corridor zones in walking order. `index` grows with the distance from the
-- lobby, so it doubles as a difficulty / reward tier.
MapData.zones = {
	{
		id = "green",
		label = "Zone Verte",
		index = 1,
		section = "Zone1_Verte",
		color = Color3.fromRGB(46, 255, 76),
		bounds = {
			min = Vector3.new(0.00, 0.00, -124.00),
			max = Vector3.new(160.00, 0.00, 124.00),
		},
		spawn = Vector3.new(30.00, 0.00, 0.00),
		spawnYaw = -1.5708,
		capsuleArea = {
			min = Vector3.new(20.00, 0.00, -32.00),
			max = Vector3.new(140.00, 0.00, 32.00),
		},
	},
	{
		id = "lava",
		label = "Zone de Lave",
		index = 2,
		section = "Zone2_Lave",
		color = Color3.fromRGB(255, 87, 33),
		bounds = {
			min = Vector3.new(160.00, 0.00, -124.00),
			max = Vector3.new(320.00, 0.00, 124.00),
		},
		spawn = Vector3.new(178.00, 0.00, 0.00),
		spawnYaw = -1.5708,
		capsuleArea = {
			min = Vector3.new(180.00, 0.00, -32.00),
			max = Vector3.new(300.00, 0.00, 32.00),
		},
	},
	{
		id = "ice",
		label = "Zone de Glace",
		index = 3,
		section = "Zone3_Glace",
		color = Color3.fromRGB(64, 217, 255),
		bounds = {
			min = Vector3.new(320.00, 0.00, -124.00),
			max = Vector3.new(480.00, 0.00, 124.00),
		},
		spawn = Vector3.new(338.00, 0.00, 0.00),
		spawnYaw = -1.5708,
		capsuleArea = {
			min = Vector3.new(340.00, 0.00, -32.00),
			max = Vector3.new(460.00, 0.00, 32.00),
		},
	},
	{
		id = "stone",
		label = "Zone de Pierre",
		index = 4,
		section = "Zone4_Pierre",
		color = Color3.fromRGB(140, 178, 242),
		bounds = {
			min = Vector3.new(480.00, 0.00, -124.00),
			max = Vector3.new(640.00, 0.00, 124.00),
		},
		spawn = Vector3.new(498.00, 0.00, 0.00),
		spawnYaw = -1.5708,
		capsuleArea = {
			min = Vector3.new(500.00, 0.00, -32.00),
			max = Vector3.new(620.00, 0.00, 32.00),
		},
	},
	{
		id = "desert",
		label = "Zone Desert",
		index = 5,
		section = "Zone5_Desert",
		color = Color3.fromRGB(255, 199, 46),
		bounds = {
			min = Vector3.new(640.00, 0.00, -124.00),
			max = Vector3.new(900.00, 0.00, 124.00),
		},
		spawn = Vector3.new(658.00, 0.00, 0.00),
		spawnYaw = -1.5708,
		capsuleArea = {
			min = Vector3.new(660.00, 0.00, -32.00),
			max = Vector3.new(723.63, 0.00, 32.00),
		},
	},
}

-- Teleport triggers. target = "base", "lobby" or "zone:<id>".
-- position/size/yaw describe the trigger box (CFrame.Angles(0, yaw, 0)).
MapData.portals = {
	{
		id = "lobby_base",
		label = "MA BASE",
		target = "base",
		position = Vector3.new(-226.00, 9.00, -150.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = 0.0000,
	},
	{
		id = "lobby_green",
		label = "VERTE",
		target = "zone:green",
		position = Vector3.new(-196.00, 9.00, -150.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = 0.0000,
	},
	{
		id = "lobby_lava",
		label = "LAVE",
		target = "zone:lava",
		position = Vector3.new(-166.00, 9.00, -150.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = 0.0000,
	},
	{
		id = "lobby_ice",
		label = "GLACE",
		target = "zone:ice",
		position = Vector3.new(-136.00, 9.00, -150.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = 0.0000,
	},
	{
		id = "lobby_stone",
		label = "PIERRE",
		target = "zone:stone",
		position = Vector3.new(-106.00, 9.00, -150.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = 0.0000,
	},
	{
		id = "lobby_desert",
		label = "BOSS",
		target = "zone:desert",
		position = Vector3.new(-76.00, 9.00, -150.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = 0.0000,
	},
	{
		id = "return_arena",
		label = "LOBBY",
		target = "lobby",
		position = Vector3.new(868.00, 9.00, 0.00),
		size = Vector3.new(12.00, 17.00, 4.00),
		yaw = -1.5708,
	},
}

-- Legacy: the whole corridor lane. Prefer zones[i].capsuleArea.
MapData.capsuleZone = {
	min = Vector3.new(0.00, 0.00, -32.00),
	max = Vector3.new(735.63, 0.00, 32.00),
}

MapData.bossAltar = {
	center = Vector3.new(800.00, 0.00, 0.00),
	top = Vector3.new(800.00, 9.10, 0.00),
	radius = 40.00,
}

-- Player bases ("enclos") on the lobby's west side, B1 closest to the avenue.
MapData.plots = {
	{
		id = "B1",
		side = "west",
		zone = "lobby",
		center = Vector3.new(-363.00, 0.05, -74.00),
		entrance = Vector3.new(-306.00, 0.05, -74.00),
		spawn = Vector3.new(-310.00, 0.05, -74.00),
		machine = Vector3.new(-328.00, 0.00, -74.00),
		sellStand = Vector3.new(-326.00, 0.00, -30.00),
		shopStand = Vector3.new(-326.00, 0.00, -118.00),
		conveyor = Vector3.new(-348.00, 0.00, -58.00),
		house = Vector3.new(-400.00, 0.00, -124.00),
		sign = Vector3.new(-328.00, 34.00, -74.00),
		spawnYaw = 1.5708,
		pens = {
			Vector3.new(-368.00, 1.80, -28.00),
			Vector3.new(-368.00, 1.80, -62.00),
			Vector3.new(-368.00, 1.80, -96.00),
			Vector3.new(-406.00, 1.80, -28.00),
			Vector3.new(-406.00, 1.80, -62.00),
			Vector3.new(-406.00, 1.80, -96.00),
		},
		bounds = {
			min = Vector3.new(-424.00, 0.00, -140.00),
			max = Vector3.new(-302.00, 40.00, -8.00),
		},
	},
	{
		id = "B2",
		side = "west",
		zone = "lobby",
		center = Vector3.new(-363.00, 0.05, 74.00),
		entrance = Vector3.new(-306.00, 0.05, 74.00),
		spawn = Vector3.new(-310.00, 0.05, 74.00),
		machine = Vector3.new(-328.00, 0.00, 74.00),
		sellStand = Vector3.new(-326.00, 0.00, 118.00),
		shopStand = Vector3.new(-326.00, 0.00, 30.00),
		conveyor = Vector3.new(-348.00, 0.00, 90.00),
		house = Vector3.new(-400.00, 0.00, 24.00),
		sign = Vector3.new(-328.00, 34.00, 74.00),
		spawnYaw = 1.5708,
		pens = {
			Vector3.new(-368.00, 1.80, 120.00),
			Vector3.new(-368.00, 1.80, 86.00),
			Vector3.new(-368.00, 1.80, 52.00),
			Vector3.new(-406.00, 1.80, 120.00),
			Vector3.new(-406.00, 1.80, 86.00),
			Vector3.new(-406.00, 1.80, 52.00),
		},
		bounds = {
			min = Vector3.new(-424.00, 0.00, 8.00),
			max = Vector3.new(-302.00, 40.00, 140.00),
		},
	},
	{
		id = "B3",
		side = "west",
		zone = "lobby",
		center = Vector3.new(-363.00, 0.05, -222.00),
		entrance = Vector3.new(-306.00, 0.05, -222.00),
		spawn = Vector3.new(-310.00, 0.05, -222.00),
		machine = Vector3.new(-328.00, 0.00, -222.00),
		sellStand = Vector3.new(-326.00, 0.00, -178.00),
		shopStand = Vector3.new(-326.00, 0.00, -266.00),
		conveyor = Vector3.new(-348.00, 0.00, -206.00),
		house = Vector3.new(-400.00, 0.00, -272.00),
		sign = Vector3.new(-328.00, 34.00, -222.00),
		spawnYaw = 1.5708,
		pens = {
			Vector3.new(-368.00, 1.80, -176.00),
			Vector3.new(-368.00, 1.80, -210.00),
			Vector3.new(-368.00, 1.80, -244.00),
			Vector3.new(-406.00, 1.80, -176.00),
			Vector3.new(-406.00, 1.80, -210.00),
			Vector3.new(-406.00, 1.80, -244.00),
		},
		bounds = {
			min = Vector3.new(-424.00, 0.00, -288.00),
			max = Vector3.new(-302.00, 40.00, -156.00),
		},
	},
	{
		id = "B4",
		side = "west",
		zone = "lobby",
		center = Vector3.new(-363.00, 0.05, 222.00),
		entrance = Vector3.new(-306.00, 0.05, 222.00),
		spawn = Vector3.new(-310.00, 0.05, 222.00),
		machine = Vector3.new(-328.00, 0.00, 222.00),
		sellStand = Vector3.new(-326.00, 0.00, 266.00),
		shopStand = Vector3.new(-326.00, 0.00, 178.00),
		conveyor = Vector3.new(-348.00, 0.00, 238.00),
		house = Vector3.new(-400.00, 0.00, 172.00),
		sign = Vector3.new(-328.00, 34.00, 222.00),
		spawnYaw = 1.5708,
		pens = {
			Vector3.new(-368.00, 1.80, 268.00),
			Vector3.new(-368.00, 1.80, 234.00),
			Vector3.new(-368.00, 1.80, 200.00),
			Vector3.new(-406.00, 1.80, 268.00),
			Vector3.new(-406.00, 1.80, 234.00),
			Vector3.new(-406.00, 1.80, 200.00),
		},
		bounds = {
			min = Vector3.new(-424.00, 0.00, 156.00),
			max = Vector3.new(-302.00, 40.00, 288.00),
		},
	},
}

-- Roblox look per material key: MeshPart names end in "__<key>".
MapData.materials = {
	grass_a = {
		color = Color3.fromRGB(51, 168, 28),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	grass_b = {
		color = Color3.fromRGB(89, 217, 51),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	grass_rim = {
		color = Color3.fromRGB(41, 242, 31),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	dirt = {
		color = Color3.fromRGB(158, 110, 64),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	dirt_dark = {
		color = Color3.fromRGB(128, 84, 46),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	sand = {
		color = Color3.fromRGB(230, 199, 120),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	sand_dark = {
		color = Color3.fromRGB(204, 168, 97),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	stone = {
		color = Color3.fromRGB(122, 125, 135),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	stone_dark = {
		color = Color3.fromRGB(84, 87, 97),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	wood = {
		color = Color3.fromRGB(107, 66, 33),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	wood_light = {
		color = Color3.fromRGB(168, 120, 66),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	white = {
		color = Color3.fromRGB(237, 237, 237),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	red = {
		color = Color3.fromRGB(214, 33, 33),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	yellow = {
		color = Color3.fromRGB(250, 201, 28),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	blue = {
		color = Color3.fromRGB(41, 112, 219),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	metal_dark = {
		color = Color3.fromRGB(66, 71, 84),
		material = "Metal",
		transparency = 0.00,
	},
	metal_mid = {
		color = Color3.fromRGB(115, 120, 133),
		material = "Metal",
		transparency = 0.00,
	},
	glow_green = {
		color = Color3.fromRGB(46, 255, 76),
		material = "Neon",
		transparency = 0.00,
	},
	glow_cyan = {
		color = Color3.fromRGB(64, 217, 255),
		material = "Neon",
		transparency = 0.00,
	},
	glow_gold = {
		color = Color3.fromRGB(255, 199, 46),
		material = "Neon",
		transparency = 0.00,
	},
	glow_violet = {
		color = Color3.fromRGB(166, 76, 255),
		material = "Neon",
		transparency = 0.00,
	},
	glow_pink = {
		color = Color3.fromRGB(255, 92, 184),
		material = "Neon",
		transparency = 0.00,
	},
	text_decal = {
		color = Color3.fromRGB(247, 247, 255),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	roof = {
		color = Color3.fromRGB(189, 89, 56),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	house = {
		color = Color3.fromRGB(209, 184, 138),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	leaf = {
		color = Color3.fromRGB(41, 133, 46),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	leaf_light = {
		color = Color3.fromRGB(61, 168, 56),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	cactus = {
		color = Color3.fromRGB(54, 140, 66),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	flower_pink = {
		color = Color3.fromRGB(242, 115, 166),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	flower_white = {
		color = Color3.fromRGB(247, 242, 217),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	water = {
		color = Color3.fromRGB(51, 158, 230),
		material = "SmoothPlastic",
		transparency = 0.25,
	},
	lava_rock = {
		color = Color3.fromRGB(61, 38, 36),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	lava_rock_dark = {
		color = Color3.fromRGB(41, 26, 23),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	lava_glow = {
		color = Color3.fromRGB(255, 87, 33),
		material = "Neon",
		transparency = 0.00,
	},
	volcanic = {
		color = Color3.fromRGB(51, 43, 43),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	volcanic_dark = {
		color = Color3.fromRGB(31, 26, 26),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	ice = {
		color = Color3.fromRGB(130, 212, 250),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	ice_dark = {
		color = Color3.fromRGB(92, 168, 219),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	snow = {
		color = Color3.fromRGB(227, 242, 252),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	ice_crystal = {
		color = Color3.fromRGB(153, 235, 255),
		material = "Neon",
		transparency = 0.00,
	},
	rock_floor = {
		color = Color3.fromRGB(117, 117, 117),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	rock_floor_dark = {
		color = Color3.fromRGB(79, 79, 79),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	rock_wall = {
		color = Color3.fromRGB(66, 66, 66),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	cave_crystal = {
		color = Color3.fromRGB(140, 178, 242),
		material = "Neon",
		transparency = 0.00,
	},
	marble = {
		color = Color3.fromRGB(237, 232, 222),
		material = "Marble",
		transparency = 0.00,
	},
	marble_dark = {
		color = Color3.fromRGB(194, 189, 178),
		material = "Marble",
		transparency = 0.00,
	},
	gold = {
		color = Color3.fromRGB(255, 204, 64),
		material = "Metal",
		transparency = 0.00,
	},
	board = {
		color = Color3.fromRGB(33, 38, 56),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	statue = {
		color = Color3.fromRGB(76, 87, 102),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	statue_dark = {
		color = Color3.fromRGB(43, 48, 61),
		material = "SmoothPlastic",
		transparency = 0.00,
	},
	rarity_common = {
		color = Color3.fromRGB(150, 150, 150),
		material = "Neon",
		transparency = 0.00,
	},
	rarity_rare = {
		color = Color3.fromRGB(70, 140, 255),
		material = "Neon",
		transparency = 0.00,
	},
	rarity_epic = {
		color = Color3.fromRGB(170, 70, 255),
		material = "Neon",
		transparency = 0.00,
	},
	rarity_legendary = {
		color = Color3.fromRGB(255, 170, 30),
		material = "Neon",
		transparency = 0.00,
	},
	rarity_mythic = {
		color = Color3.fromRGB(255, 60, 90),
		material = "Neon",
		transparency = 0.00,
	},
	ref = {
		color = Color3.fromRGB(255, 0, 255),
		material = "SmoothPlastic",
		transparency = 1.00,
	},
}

local function inside(bounds: any, position: Vector3): boolean
	return position.X >= bounds.min.X and position.X <= bounds.max.X
		and position.Z >= bounds.min.Z and position.Z <= bounds.max.Z
end

-- Which corridor zone a world position falls into (ignores height).
function MapData.GetZoneAt(position: Vector3): any
	for _, zone in ipairs(MapData.zones) do
		if inside(zone.bounds, position) then
			return zone
		end
	end
	return nil
end

-- Lobby (bridge included) or corridor zone at a position; nil off the map.
function MapData.GetAreaAt(position: Vector3): any
	if inside(MapData.lobby.bounds, position) then
		return MapData.lobby
	end
	return MapData.GetZoneAt(position)
end

function MapData.GetZoneById(id: string): any
	for _, zone in ipairs(MapData.zones) do
		if zone.id == id then
			return zone
		end
	end
	return nil
end

function MapData.GetPlot(id: string): any
	for _, plot in ipairs(MapData.plots) do
		if plot.id == id then
			return plot
		end
	end
	return nil
end

return MapData
