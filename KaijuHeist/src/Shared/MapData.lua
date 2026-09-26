--!strict
-- GENERATED FILE - do not edit by hand.
-- Produced by KaijuHeist/blender/build_map.py; re-run that script to update.
--
-- Positions are studs in Roblox axes (Y up), matching kaiju_heist_map.glb
-- imported at scale 1. Plot ids are N1..N4 (north row) and S1..S4 (south row).

local MapData = {}

MapData.island = {
	min = Vector3.new(-436.00, -60.00, -215.00),
	max = Vector3.new(511.00, 0.00, 215.00),
}

MapData.street = {
	min = Vector3.new(-436.00, 0.00, -36.00),
	max = Vector3.new(308.00, 0.00, 36.00),
	width = 72.0,
}

MapData.spawnPlaza = {
	center = Vector3.new(-356.00, 0.00, 0.00),
	radius = 70.0,
}

MapData.bossAltar = {
	center = Vector3.new(403.50, 0.00, 0.00),
	radius = 40.0,
}

-- Street band where world capsules may spawn: the running lane, clear of decor.
MapData.capsuleZone = {
	min = Vector3.new(-296.00, 0.00, -20.00),
	max = Vector3.new(296.00, 0.00, 20.00),
}

-- Corridor biomes in walking order from the spawn plaza. `index` grows with
-- distance, so it doubles as a difficulty / reward tier.
MapData.zones = {
	{
		id = "green",
		label = "Zone Verte",
		index = 1,
		bounds = { min = Vector3.new(-436.00, 0.00, -215.00), max = Vector3.new(-148.00, 0.00, 215.00) },
	},
	{
		id = "lava",
		label = "Zone de Lave",
		index = 2,
		bounds = { min = Vector3.new(-148.00, 0.00, -215.00), max = Vector3.new(0.00, 0.00, 215.00) },
	},
	{
		id = "ice",
		label = "Zone de Glace",
		index = 3,
		bounds = { min = Vector3.new(0.00, 0.00, -215.00), max = Vector3.new(148.00, 0.00, 215.00) },
	},
	{
		id = "stone",
		label = "Zone de Pierre",
		index = 4,
		bounds = { min = Vector3.new(148.00, 0.00, -215.00), max = Vector3.new(308.00, 0.00, 215.00) },
	},
	{
		id = "desert",
		label = "Zone Desert",
		index = 5,
		bounds = { min = Vector3.new(308.00, 0.00, -215.00), max = Vector3.new(511.00, 0.00, 215.00) },
	},
}

-- Which biome a world position falls into (ignores height).
function MapData.GetZoneAt(position: Vector3)
	for _, zone in ipairs(MapData.zones) do
		if position.X >= zone.bounds.min.X and position.X <= zone.bounds.max.X then
			return zone
		end
	end
	return nil
end

MapData.plots = {
	{
		id = "N1",
		side = "north",
		center = Vector3.new(-214.00, 0.00, -97.00),
		entrance = Vector3.new(-214.00, 0.00, -40.00),
		spawn = Vector3.new(-214.00, 0.00, -52.00),
		machine = Vector3.new(-214.00, 0.00, -62.00),
		sellStand = Vector3.new(-258.00, 0.00, -60.00),
		shopStand = Vector3.new(-170.00, 0.00, -60.00),
		conveyor = Vector3.new(-230.00, 0.00, -82.00),
		house = Vector3.new(-164.00, 0.00, -134.00),
		pens = {
			Vector3.new(-260.00, 1.80, -102.00),
			Vector3.new(-226.00, 1.80, -102.00),
			Vector3.new(-192.00, 1.80, -102.00),
			Vector3.new(-260.00, 1.80, -140.00),
			Vector3.new(-226.00, 1.80, -140.00),
			Vector3.new(-192.00, 1.80, -140.00),
		},
		bounds = { min = Vector3.new(-280.00, 0.00, -158.00), max = Vector3.new(-148.00, 40.00, -36.00) },
	},
	{
		id = "S1",
		side = "south",
		center = Vector3.new(-214.00, 0.00, 97.00),
		entrance = Vector3.new(-214.00, 0.00, 40.00),
		spawn = Vector3.new(-214.00, 0.00, 52.00),
		machine = Vector3.new(-214.00, 0.00, 62.00),
		sellStand = Vector3.new(-170.00, 0.00, 60.00),
		shopStand = Vector3.new(-258.00, 0.00, 60.00),
		conveyor = Vector3.new(-198.00, 0.00, 82.00),
		house = Vector3.new(-264.00, 0.00, 134.00),
		pens = {
			Vector3.new(-168.00, 1.80, 102.00),
			Vector3.new(-202.00, 1.80, 102.00),
			Vector3.new(-236.00, 1.80, 102.00),
			Vector3.new(-168.00, 1.80, 140.00),
			Vector3.new(-202.00, 1.80, 140.00),
			Vector3.new(-236.00, 1.80, 140.00),
		},
		bounds = { min = Vector3.new(-280.00, 0.00, 36.00), max = Vector3.new(-148.00, 40.00, 158.00) },
	},
	{
		id = "N2",
		side = "north",
		center = Vector3.new(-66.00, 0.00, -97.00),
		entrance = Vector3.new(-66.00, 0.00, -40.00),
		spawn = Vector3.new(-66.00, 0.00, -52.00),
		machine = Vector3.new(-66.00, 0.00, -62.00),
		sellStand = Vector3.new(-110.00, 0.00, -60.00),
		shopStand = Vector3.new(-22.00, 0.00, -60.00),
		conveyor = Vector3.new(-82.00, 0.00, -82.00),
		house = Vector3.new(-16.00, 0.00, -134.00),
		pens = {
			Vector3.new(-112.00, 1.80, -102.00),
			Vector3.new(-78.00, 1.80, -102.00),
			Vector3.new(-44.00, 1.80, -102.00),
			Vector3.new(-112.00, 1.80, -140.00),
			Vector3.new(-78.00, 1.80, -140.00),
			Vector3.new(-44.00, 1.80, -140.00),
		},
		bounds = { min = Vector3.new(-132.00, 0.00, -158.00), max = Vector3.new(0.00, 40.00, -36.00) },
	},
	{
		id = "S2",
		side = "south",
		center = Vector3.new(-66.00, 0.00, 97.00),
		entrance = Vector3.new(-66.00, 0.00, 40.00),
		spawn = Vector3.new(-66.00, 0.00, 52.00),
		machine = Vector3.new(-66.00, 0.00, 62.00),
		sellStand = Vector3.new(-22.00, 0.00, 60.00),
		shopStand = Vector3.new(-110.00, 0.00, 60.00),
		conveyor = Vector3.new(-50.00, 0.00, 82.00),
		house = Vector3.new(-116.00, 0.00, 134.00),
		pens = {
			Vector3.new(-20.00, 1.80, 102.00),
			Vector3.new(-54.00, 1.80, 102.00),
			Vector3.new(-88.00, 1.80, 102.00),
			Vector3.new(-20.00, 1.80, 140.00),
			Vector3.new(-54.00, 1.80, 140.00),
			Vector3.new(-88.00, 1.80, 140.00),
		},
		bounds = { min = Vector3.new(-132.00, 0.00, 36.00), max = Vector3.new(0.00, 40.00, 158.00) },
	},
	{
		id = "N3",
		side = "north",
		center = Vector3.new(82.00, 0.00, -97.00),
		entrance = Vector3.new(82.00, 0.00, -40.00),
		spawn = Vector3.new(82.00, 0.00, -52.00),
		machine = Vector3.new(82.00, 0.00, -62.00),
		sellStand = Vector3.new(38.00, 0.00, -60.00),
		shopStand = Vector3.new(126.00, 0.00, -60.00),
		conveyor = Vector3.new(66.00, 0.00, -82.00),
		house = Vector3.new(132.00, 0.00, -134.00),
		pens = {
			Vector3.new(36.00, 1.80, -102.00),
			Vector3.new(70.00, 1.80, -102.00),
			Vector3.new(104.00, 1.80, -102.00),
			Vector3.new(36.00, 1.80, -140.00),
			Vector3.new(70.00, 1.80, -140.00),
			Vector3.new(104.00, 1.80, -140.00),
		},
		bounds = { min = Vector3.new(16.00, 0.00, -158.00), max = Vector3.new(148.00, 40.00, -36.00) },
	},
	{
		id = "S3",
		side = "south",
		center = Vector3.new(82.00, 0.00, 97.00),
		entrance = Vector3.new(82.00, 0.00, 40.00),
		spawn = Vector3.new(82.00, 0.00, 52.00),
		machine = Vector3.new(82.00, 0.00, 62.00),
		sellStand = Vector3.new(126.00, 0.00, 60.00),
		shopStand = Vector3.new(38.00, 0.00, 60.00),
		conveyor = Vector3.new(98.00, 0.00, 82.00),
		house = Vector3.new(32.00, 0.00, 134.00),
		pens = {
			Vector3.new(128.00, 1.80, 102.00),
			Vector3.new(94.00, 1.80, 102.00),
			Vector3.new(60.00, 1.80, 102.00),
			Vector3.new(128.00, 1.80, 140.00),
			Vector3.new(94.00, 1.80, 140.00),
			Vector3.new(60.00, 1.80, 140.00),
		},
		bounds = { min = Vector3.new(16.00, 0.00, 36.00), max = Vector3.new(148.00, 40.00, 158.00) },
	},
	{
		id = "N4",
		side = "north",
		center = Vector3.new(230.00, 0.00, -97.00),
		entrance = Vector3.new(230.00, 0.00, -40.00),
		spawn = Vector3.new(230.00, 0.00, -52.00),
		machine = Vector3.new(230.00, 0.00, -62.00),
		sellStand = Vector3.new(186.00, 0.00, -60.00),
		shopStand = Vector3.new(274.00, 0.00, -60.00),
		conveyor = Vector3.new(214.00, 0.00, -82.00),
		house = Vector3.new(280.00, 0.00, -134.00),
		pens = {
			Vector3.new(184.00, 1.80, -102.00),
			Vector3.new(218.00, 1.80, -102.00),
			Vector3.new(252.00, 1.80, -102.00),
			Vector3.new(184.00, 1.80, -140.00),
			Vector3.new(218.00, 1.80, -140.00),
			Vector3.new(252.00, 1.80, -140.00),
		},
		bounds = { min = Vector3.new(164.00, 0.00, -158.00), max = Vector3.new(296.00, 40.00, -36.00) },
	},
	{
		id = "S4",
		side = "south",
		center = Vector3.new(230.00, 0.00, 97.00),
		entrance = Vector3.new(230.00, 0.00, 40.00),
		spawn = Vector3.new(230.00, 0.00, 52.00),
		machine = Vector3.new(230.00, 0.00, 62.00),
		sellStand = Vector3.new(274.00, 0.00, 60.00),
		shopStand = Vector3.new(186.00, 0.00, 60.00),
		conveyor = Vector3.new(246.00, 0.00, 82.00),
		house = Vector3.new(180.00, 0.00, 134.00),
		pens = {
			Vector3.new(276.00, 1.80, 102.00),
			Vector3.new(242.00, 1.80, 102.00),
			Vector3.new(208.00, 1.80, 102.00),
			Vector3.new(276.00, 1.80, 140.00),
			Vector3.new(242.00, 1.80, 140.00),
			Vector3.new(208.00, 1.80, 140.00),
		},
		bounds = { min = Vector3.new(164.00, 0.00, 36.00), max = Vector3.new(296.00, 40.00, 158.00) },
	},
}

function MapData.GetPlot(id: string)
	for _, plot in ipairs(MapData.plots) do
		if plot.id == id then
			return plot
		end
	end
	return nil
end

return MapData
