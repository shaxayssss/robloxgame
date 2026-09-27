-- Effects: sunbursts, reward popup, floating numbers and the purchase overlay.

local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("BrainrotUI"):WaitForChild("UIConfig"))
local Widgets = require(script.Parent:WaitForChild("Widgets"))

local Theme = Widgets.Theme
local create = Widgets.create

local Effects = {}

local screenGui: ScreenGui? = nil
local overlay: Frame? = nil
local popupOpen: GuiObject? = nil

local function spinForever(instance: GuiObject, secondsPerTurn: number)
	instance.Rotation = 0
	TweenService:Create(instance, TweenInfo.new(secondsPerTurn, Enum.EasingStyle.Linear, Enum.EasingDirection.InOut, -1), { Rotation = 360 }):Play()
end

-- Rotating rays behind a highlighted element. Options: Size, Position,
-- AnchorPoint, Color, Rays, SecondsPerTurn, ZIndex, Parent.
function Effects.sunburst(options: { [string]: any }): Frame
	local root = Widgets.frame({
		Name = "Sunburst",
		Size = options.Size,
		Position = options.Position or UDim2.fromScale(0.5, 0.5),
		AnchorPoint = options.AnchorPoint or Vector2.new(0.5, 0.5),
		ZIndex = options.ZIndex or 1,
		Parent = options.Parent,
	})
	local rays = options.Rays or 8
	local fade = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.5, 0.25),
		NumberSequenceKeypoint.new(1, 1),
	})
	for index = 1, rays do
		-- each bar is two opposite rays
		create("Frame", {
			Name = "Ray",
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.5, 0.5),
			Size = UDim2.fromScale(0.12, 1),
			Rotation = (index - 1) * 180 / rays,
			BackgroundColor3 = options.Color or Theme.Gold,
			ZIndex = options.ZIndex or 1,
			Parent = root,
		}, { create("UIGradient", { Rotation = 90, Transparency = fade }) })
	end
	spinForever(root, options.SecondsPerTurn or 12)
	return root
end

-- "+25" rising from a HUD element and fading away.
function Effects.floatText(anchor: GuiObject, text: string, colors: { Color3 }, strokeColor: Color3?)
	local label = Widgets.text({
		Name = "Float",
		Text = text,
		Font = "Title",
		TextSize = 26,
		Stroke = 3,
		StrokeColor = strokeColor,
		XAlign = Enum.TextXAlignment.Left,
		AnchorPoint = Vector2.new(0, 0.5),
		Position = UDim2.new(1, 8, 0.5, 0),
		Size = UDim2.fromOffset(140, 30),
		ZIndex = 10,
		Parent = anchor,
	})
	Widgets.gradient(colors, 90).Parent = label
	local stroke = label:FindFirstChildOfClass("UIStroke")
	Widgets.tween(label, 0.9, { Position = UDim2.new(1, 8, 0.5, -34), TextTransparency = 1 }, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	if stroke then
		Widgets.tween(stroke, 0.9, { Transparency = 1 })
	end
	task.delay(0.95, function()
		label:Destroy()
	end)
end

-- Short scale "pop" on an element (for example a counter that just went up).
function Effects.pop(guiObject: GuiObject)
	local scale = guiObject:FindFirstChild("PopScale")
	if not scale then
		scale = create("UIScale", { Name = "PopScale", Parent = guiObject })
	end
	(scale :: UIScale).Scale = 1.18
	Widgets.tween(scale :: UIScale, 0.3, { Scale = 1 }, Enum.EasingStyle.Back)
end

-- Big centred popup for a reward: icon, title, subtitle, rotating rays.
function Effects.rewardPopup(icon: string, title: string, subtitle: string?, color: Color3?)
	local gui = screenGui
	if not gui then
		return
	end
	if popupOpen then
		popupOpen:Destroy()
	end
	Widgets.playSound("Reward")
	local root = create("TextButton", {
		Name = "RewardPopup",
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 1,
		AutoButtonColor = false,
		Text = "",
		ZIndex = 90,
		Parent = gui,
	})
	popupOpen = root
	local card = Widgets.frame({
		Name = "Card",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.46),
		Size = UDim2.fromOffset(360, 330),
		ZIndex = 90,
		Parent = root,
	})
	Widgets.attachHudScale(card)
	local holder = Widgets.frame({ Name = "Pop", Size = UDim2.fromScale(1, 1), ZIndex = 90, Parent = card })
	local pop = create("UIScale", { Scale = 0, Parent = holder })
	Effects.sunburst({
		Parent = holder,
		Size = UDim2.fromOffset(420, 420),
		Position = UDim2.fromOffset(180, 120),
		Color = color or Theme.Gold,
		Rays = 10,
		SecondsPerTurn = 8,
		ZIndex = 90,
	})
	Widgets.text({ Name = "Icon", Text = icon, TextSize = 96, Stroke = false, Position = UDim2.fromOffset(0, 60), Size = UDim2.new(1, 0, 0, 120), ZIndex = 91, Parent = holder })
	local titleLabel = Widgets.text({
		Name = "Title",
		Text = title,
		Font = "Title",
		TextSize = 46,
		Stroke = 4,
		Position = UDim2.fromOffset(-40, 196),
		Size = UDim2.new(1, 80, 0, 56),
		ZIndex = 92,
		Parent = holder,
	})
	Widgets.gradient({ Color3.fromRGB(255, 250, 190), color or Theme.Gold }, 90).Parent = titleLabel
	if subtitle then
		Widgets.text({ Name = "Subtitle", Text = subtitle, TextSize = 24, Position = UDim2.fromOffset(-40, 252), Size = UDim2.new(1, 80, 0, 30), ZIndex = 92, Parent = holder })
	end

	Widgets.tween(root, 0.2, { BackgroundTransparency = 0.5 })
	Widgets.tween(pop, 0.4, { Scale = 1 }, Enum.EasingStyle.Back)
	local closed = false
	local function close()
		if closed then
			return
		end
		closed = true
		Widgets.tween(root, 0.2, { BackgroundTransparency = 1 })
		Widgets.tween(pop, 0.2, { Scale = 0 }, Enum.EasingStyle.Back, Enum.EasingDirection.In).Completed:Once(function()
			root:Destroy()
			if popupOpen == root then
				popupOpen = nil
			end
		end)
	end
	root.Activated:Connect(close)
	task.delay(2.4, close)
end

-- Dims the screen while a Roblox purchase prompt is open.
function Effects.purchaseOverlay(visible: boolean)
	local frame = overlay
	if frame then
		frame.Visible = visible
	end
end

local function buildOverlay(gui: ScreenGui)
	local frame = create("Frame", {
		Name = "PurchaseOverlay",
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 0.45,
		Active = true,
		Visible = false,
		ZIndex = 95,
		Parent = gui,
	})
	local card = Widgets.panel({
		Name = "Card",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromOffset(300, 84),
		BackgroundColor3 = Theme.Panel,
		ZIndex = 96,
		Parent = frame,
	})
	Widgets.attachHudScale(card)
	local spinner = Widgets.circle({
		Name = "Spinner",
		AnchorPoint = Vector2.new(0, 0.5),
		Position = UDim2.new(0, 22, 0.5, 0),
		Size = UDim2.fromOffset(40, 40),
		BackgroundTransparency = 1,
		ZIndex = 97,
		Parent = card,
	})
	local ring = create("UIStroke", { Thickness = 6, Color = Theme.Gold, Parent = spinner })
	create("UIGradient", {
		Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0), NumberSequenceKeypoint.new(0.6, 0.1), NumberSequenceKeypoint.new(1, 1) }),
		Parent = ring,
	})
	spinForever(spinner, 0.9)
	Widgets.text({
		Text = Config.Text.Buying,
		TextSize = 24,
		XAlign = Enum.TextXAlignment.Left,
		Position = UDim2.fromOffset(80, 0),
		Size = UDim2.new(1, -90, 1, 0),
		ZIndex = 97,
		Parent = card,
	})
	overlay = frame
end

function Effects.init(gui: ScreenGui)
	screenGui = gui
	buildOverlay(gui)
end

return Effects
