-- Wheel: a spinning prize wheel drawn without any image.
--
-- Coloured sectors are painted with half-disks: a round frame whose UIGradient
-- makes one half transparent covers exactly 180 degrees, whatever its rotation.
-- The wheel is split into two fixed clipping halves (right and left). In each
-- half, the disk of the sector under the half's start is painted first, then
-- one disk per sector boundary inside the half, in clockwise order: each disk
-- covers from its boundary to the end of the half, so the last one painted at
-- an angle is always the sector that owns it. The clip frames are never
-- rotated (clipping ignores rotated frames); only their children are.
--
-- Angles are in degrees, clockwise from the top, like GuiObject.Rotation.

local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Rules = require(shared:WaitForChild("Rules"))
local Widgets = require(script.Parent:WaitForChild("Widgets"))

local Theme = Widgets.Theme
local create = Widgets.create

local Wheel = {}
Wheel.__index = Wheel

local LIGHT_COUNT = 16
local LIGHT_ON = Color3.fromRGB(255, 244, 170)
local LIGHT_OFF = Color3.fromRGB(150, 90, 20)

-- Transparent on the left half, opaque on the right half.
local HALF_MASK = NumberSequence.new({
	NumberSequenceKeypoint.new(0, 1),
	NumberSequenceKeypoint.new(0.499, 1),
	NumberSequenceKeypoint.new(0.501, 0),
	NumberSequenceKeypoint.new(1, 0),
})

type Half = { start: number, disks: { Frame } }

export type WheelObject = {
	Root: Frame,
	Spinning: boolean,
	SetAngle: (WheelObject, number) -> (),
	SpinTo: (WheelObject, number, number, (() -> ())?, (() -> ())?) -> (),
	SetLightsActive: (WheelObject, boolean) -> (),
}

-- Full-size transparent frame centred on the wheel: rotating it swings its
-- children around the wheel centre.
local function pivot(parent: Instance, name: string, zIndex: number): Frame
	return Widgets.frame({
		Name = name,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromScale(1, 1),
		ZIndex = zIndex,
		Parent = parent,
	})
end

-- options: Parent, Position, Diameter, Rewards (each with a Color)
function Wheel.new(options: { [string]: any })
	local self = setmetatable({}, Wheel)
	local rewards = options.Rewards
	self.count = #rewards
	self.width = 360 / self.count
	self.angle = 0
	self.Spinning = false
	self.colors = {}
	for index, reward in rewards do
		self.colors[index] = reward.Color or Theme.Blue
	end

	local diameter = options.Diameter
	local root = Widgets.frame({
		Name = "Wheel",
		Size = UDim2.fromOffset(diameter, diameter),
		Position = options.Position or UDim2.new(),
		AnchorPoint = options.AnchorPoint or Vector2.zero,
		ZIndex = 31,
		Parent = options.Parent,
	})
	self.Root = root

	-- golden rim behind the sectors
	Widgets.circle({
		Name = "Rim",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.new(1, 30, 1, 30),
		BackgroundColor3 = Color3.new(1, 1, 1),
		ZIndex = 31,
		Parent = root,
	}, { Widgets.stroke(4), Widgets.gradient({ Color3.fromRGB(255, 225, 110), Color3.fromRGB(215, 120, 20) }, 90) })

	-- sector halves
	local disksPerHalf = math.ceil(180 / self.width) + 2
	self.halves = {} :: { Half }
	for _, side in { "Right", "Left" } do
		local isRight = side == "Right"
		local clip = Widgets.frame({
			Name = side .. "Half",
			Position = UDim2.fromScale(if isRight then 0.5 else 0, 0),
			Size = UDim2.fromScale(0.5, 1),
			ClipsDescendants = true,
			ZIndex = 32,
			Parent = root,
		})
		local disks = {}
		for index = 1, disksPerHalf do
			disks[index] = create("Frame", {
				Name = "Disk" .. index,
				AnchorPoint = Vector2.new(0.5, 0.5),
				Position = UDim2.fromScale(if isRight then 0 else 1, 0.5),
				Size = UDim2.fromScale(2, 1),
				BackgroundColor3 = Color3.new(1, 1, 1),
				Visible = false,
				ZIndex = 32 + index,
				Parent = clip,
			}, { Widgets.round(), create("UIGradient", { Transparency = HALF_MASK }) })
		end
		table.insert(self.halves, { start = if isRight then 0 else 180, disks = disks })
	end

	-- soft inner shading on top of the colours
	Widgets.circle({
		Name = "Gloss",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.new(1, 1, 1),
		BackgroundTransparency = 0,
		ZIndex = 45,
		Parent = root,
	}, {
		create("UIGradient", {
			Rotation = 90,
			Transparency = NumberSequence.new({
				NumberSequenceKeypoint.new(0, 0.78),
				NumberSequenceKeypoint.new(0.45, 1),
				NumberSequenceKeypoint.new(1, 0.86),
			}),
			Color = ColorSequence.new(Color3.new(1, 1, 1), Color3.new(0, 0, 0)),
		}),
	})

	-- separators between sectors
	self.spokes = {}
	for index = 1, self.count do
		local holder = pivot(root, "Spoke" .. index, 46)
		create("Frame", {
			Name = "Line",
			AnchorPoint = Vector2.new(0.5, 0),
			Position = UDim2.fromScale(0.5, 0),
			Size = UDim2.new(0, 5, 0.5, 0),
			BackgroundColor3 = Theme.Outline,
			ZIndex = 46,
			Parent = holder,
		})
		self.spokes[index] = holder
	end

	-- reward labels, reading outwards along each sector
	self.labels = {}
	for index, reward in rewards do
		local info = Rules.describe(reward)
		local holder = pivot(root, "Label" .. index, 47)
		Widgets.text({
			Name = "Icon",
			Text = info.Icon,
			TextSize = 38,
			Stroke = false,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.5, 0.15),
			Size = UDim2.fromOffset(60, 52),
			ZIndex = 47,
			Parent = holder,
		})
		Widgets.text({
			Name = "Amount",
			Text = info.Short,
			Font = "Title",
			TextSize = 26,
			Stroke = 3,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.5, 0.29),
			Size = UDim2.fromOffset(110, 32),
			ZIndex = 47,
			Parent = holder,
		})
		self.labels[index] = holder
	end

	-- hub
	local hub = Widgets.circle({
		Name = "Hub",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromScale(0.2, 0.2),
		BackgroundColor3 = Color3.new(1, 1, 1),
		ZIndex = 50,
		Parent = root,
	}, { Widgets.stroke(4), Widgets.gradient({ Color3.fromRGB(255, 235, 130), Color3.fromRGB(230, 140, 20) }, 90) })
	Widgets.text({ Text = "⭐", TextSize = 38, Stroke = false, ZIndex = 51, Parent = hub })

	-- light bulbs on the (static) rim
	self.lights = {}
	for index = 1, LIGHT_COUNT do
		local holder = pivot(root, "Light" .. index, 52)
		holder.Rotation = (index - 1) * 360 / LIGHT_COUNT
		self.lights[index] = Widgets.circle({
			Name = "Bulb",
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.new(0.5, 0, 0, -8),
			Size = UDim2.fromOffset(13, 13),
			BackgroundColor3 = LIGHT_ON,
			ZIndex = 52,
			Parent = holder,
		}, { Widgets.stroke(2) })
	end

	-- pointer at the top (static)
	local pointer = Widgets.frame({
		Name = "Pointer",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.new(0.5, 0, 0, -12),
		Size = UDim2.fromOffset(46, 46),
		ZIndex = 55,
		Parent = root,
	})
	create("Frame", {
		Name = "Tip",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(23, 33),
		Size = UDim2.fromOffset(26, 26),
		Rotation = 45,
		BackgroundColor3 = Theme.Red,
		ZIndex = 55,
		Parent = pointer,
	}, { Widgets.corner(4), Widgets.stroke(3) })
	Widgets.circle({
		Name = "Cap",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(23, 19),
		Size = UDim2.fromOffset(38, 38),
		BackgroundColor3 = Theme.Red,
		ZIndex = 56,
		Parent = pointer,
	}, { Widgets.stroke(3), Widgets.shading() })
	Widgets.circle({
		Name = "Shine",
		Position = UDim2.fromOffset(9, 6),
		Size = UDim2.fromOffset(11, 11),
		BackgroundColor3 = Color3.new(1, 1, 1),
		BackgroundTransparency = 0.3,
		ZIndex = 57,
		Parent = pointer,
	})
	self.pointer = pointer

	self.lightsActive = false
	self.lightClock = 0
	self.lightPhase = 0
	self:SetAngle(0)
	return self
end

function Wheel:paintDisk(disk: Frame, screenAngle: number, sector: number)
	disk.Rotation = screenAngle
	disk.BackgroundColor3 = self.colors[sector]
	disk.Visible = true
end

function Wheel:paintHalf(half: Half)
	local width = self.width
	-- wheel-space angle found at the start of this half
	local startInWheel = (half.start - self.angle) % 360
	local sector = math.floor(startInWheel / width) % self.count + 1
	local used = 1
	self:paintDisk(half.disks[1], half.start, sector)
	-- distance from the half start to the next sector boundary
	local distance = sector * width - startInWheel
	while distance < 180 - 1e-6 and used < #half.disks do
		sector = sector % self.count + 1
		used += 1
		self:paintDisk(half.disks[used], half.start + distance, sector)
		distance += width
	end
	for index = used + 1, #half.disks do
		half.disks[index].Visible = false
	end
end

function Wheel:SetAngle(angle: number)
	self.angle = angle % 360
	for _, half in self.halves do
		self:paintHalf(half)
	end
	local width = self.width
	for index, holder in self.labels do
		holder.Rotation = (index - 1) * width + width / 2 + self.angle
	end
	for index, holder in self.spokes do
		holder.Rotation = (index - 1) * width + self.angle
	end
end

-- Sector (1..count) under the pointer.
function Wheel:SectorAtPointer(): number
	return math.floor(((-self.angle) % 360) / self.width) % self.count + 1
end

function Wheel:stepLights(dt: number)
	self.lightClock += dt
	local period = if self.Spinning then 0.08 else 0.35
	if self.lightClock < period then
		return
	end
	self.lightClock = 0
	self.lightPhase += 1
	for index, bulb in self.lights do
		local on = if self.Spinning then index % 4 == self.lightPhase % 4 else (index + self.lightPhase) % 2 == 0
		bulb.BackgroundColor3 = if on then LIGHT_ON else LIGHT_OFF
	end
end

-- Blinking bulbs, only while the wheel is on screen.
function Wheel:SetLightsActive(active: boolean)
	if active == self.lightsActive then
		return
	end
	self.lightsActive = active
	if active then
		self.lightConnection = RunService.RenderStepped:Connect(function(dt)
			self:stepLights(dt)
		end)
	elseif self.lightConnection then
		self.lightConnection:Disconnect()
		self.lightConnection = nil
	end
end

-- Spins at least 5 turns and stops on `sector` (random spot inside it).
function Wheel:SpinTo(sector: number, duration: number, onTick: (() -> ())?, onDone: (() -> ())?)
	local width = self.width
	local target = (sector - 1) * width + width / 2 + (math.random() - 0.5) * width * 0.6
	local start = self.angle
	local final = (-target) % 360
	local delta = (final - start) % 360 + 360 * 5
	local startClock = os.clock()
	local lastSector = self:SectorAtPointer()
	self.Spinning = true
	local connection
	connection = RunService.RenderStepped:Connect(function()
		local t = math.clamp((os.clock() - startClock) / duration, 0, 1)
		local eased = 1 - (1 - t) ^ 4
		self:SetAngle(start + delta * eased)
		local current = self:SectorAtPointer()
		if current ~= lastSector then
			lastSector = current
			self.pointer.Rotation = -14
			Widgets.tween(self.pointer, 0.12, { Rotation = 0 })
			if onTick then
				onTick()
			end
		end
		if t >= 1 then
			connection:Disconnect()
			self.Spinning = false
			if onDone then
				onDone()
			end
		end
	end)
end

return Wheel
