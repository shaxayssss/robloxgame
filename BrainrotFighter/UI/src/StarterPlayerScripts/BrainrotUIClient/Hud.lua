-- Hud: what stays on screen. Left: currency counters and the menu buttons.
-- Right: the featured offer and the running boosts.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Format = require(shared:WaitForChild("Format"))
local Widgets = require(script.Parent:WaitForChild("Widgets"))
local State = require(script.Parent:WaitForChild("State"))
local Windows = require(script.Parent:WaitForChild("Windows"))
local Effects = require(script.Parent:WaitForChild("Effects"))
local Purchases = require(script.Parent:WaitForChild("Purchases"))

local Theme = Widgets.Theme
local Text = Config.Text
local create = Widgets.create

local Hud = {}

export type Tile = Widgets.Button & { Badge: Widgets.Badge }

local TILE_ORDER = { "Shop", "Wheel", "Rebirth", "Invite", "Index" }
local TILE_STEP = 100 -- tile size (86) + gap

local RAINBOW = {
	Color3.fromRGB(255, 70, 70),
	Color3.fromRGB(255, 200, 40),
	Color3.fromRGB(80, 230, 90),
	Color3.fromRGB(60, 200, 255),
	Color3.fromRGB(170, 90, 255),
	Color3.fromRGB(255, 70, 70),
}

local pills: { [string]: { Frame: Frame, Value: TextLabel, Icon: Frame } } = {}
local tiles: { [string]: Tile } = {}
local boostList: Frame? = nil
local boostChips: { [string]: { Frame: Frame, Label: TextLabel } } = {}

-- Currency counter -------------------------------------------------------------

local function makePill(parent: Frame, currency: { [string]: any }, index: number, openShop: () -> ())
	local frame = Widgets.frame({
		Name = currency.Key,
		Size = UDim2.fromOffset(206, 42),
		Position = UDim2.fromOffset(0, (index - 1) * 50),
		Parent = parent,
	})
	create("Frame", {
		Name = "Pill",
		Position = UDim2.fromOffset(18, 3),
		Size = UDim2.new(1, -18, 1, -6),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 0.45,
		Parent = frame,
	}, { Widgets.round(), Widgets.stroke(3) })
	local icon = Widgets.circle({
		Name = "Icon",
		Size = UDim2.fromOffset(42, 42),
		BackgroundColor3 = Color3.new(1, 1, 1),
		ZIndex = 2,
		Parent = frame,
	}, { Widgets.stroke(3), Widgets.gradient(currency.Colors, 90) })
	Widgets.text({ Text = currency.Icon, TextSize = 24, Stroke = false, ZIndex = 3, Parent = icon })
	local value = Widgets.text({
		Name = "Value",
		Text = "0",
		Font = "Title",
		TextSize = 26,
		Stroke = 3,
		StrokeColor = currency.Stroke,
		XAlign = Enum.TextXAlignment.Left,
		Position = UDim2.fromOffset(50, 2),
		Size = UDim2.new(1, if currency.ShopShortcut then -86 else -56, 1, 0),
		ZIndex = 2,
		Parent = frame,
	})
	Widgets.gradient(currency.Colors, 90).Parent = value
	if currency.ShopShortcut then
		Widgets.button({
			Name = "Plus",
			Parent = frame,
			AnchorPoint = Vector2.new(1, 0.5),
			Position = UDim2.new(1, -4, 0.5, 0),
			Size = UDim2.fromOffset(30, 30),
			Color = Theme.Green,
			Text = "+",
			TextSize = 24,
			Radius = 10,
			Depth = 3,
			ZIndex = 3,
			OnClick = openShop,
		})
	end
	pills[currency.Key] = { Frame = frame, Value = value, Icon = icon }

	-- animated count towards the new value
	local shown = create("NumberValue", { Name = "Shown", Parent = frame })
	shown.Changed:Connect(function(number)
		value.Text = Format.short(number)
	end)
	local last: number? = nil
	State.observe(currency.Key, function(raw)
		local target = tonumber(raw) or 0
		if last == nil then
			shown.Value = target
			value.Text = Format.short(target)
		else
			Widgets.tween(shown, 0.45, { Value = target })
			if target > last then
				Effects.pop(icon)
			end
		end
		last = target
	end)
end

-- Menu button ------------------------------------------------------------------

local function makeTile(parent: Frame, options: { [string]: any }): Tile
	local tile = Widgets.button({
		Name = options.Name,
		Parent = parent,
		Size = UDim2.fromOffset(86, 86),
		Position = options.Position,
		Color = options.Color,
		Text = "",
		Radius = 18,
		Depth = 6,
		OnClick = options.OnClick,
	}) :: Tile
	Widgets.text({
		Name = "Icon",
		Text = options.Icon,
		TextSize = 44,
		Stroke = false,
		Position = UDim2.fromOffset(0, 4),
		Size = UDim2.new(1, 0, 0, 56),
		ZIndex = 2,
		Parent = tile.Face,
	})
	Widgets.text({
		Name = "Caption",
		Text = options.Text,
		Font = "Title",
		TextSize = 19,
		Scaled = true,
		Stroke = 3,
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, 0, 1, 8),
		Size = UDim2.new(1, 12, 0, 26),
		ZIndex = 3,
		Parent = tile.Face,
	})
	tile.Badge = Widgets.badge(tile.Instance)
	tiles[options.Name] = tile
	return tile
end

-- Animated rainbow outline (used on the shop button).
local function rainbowOutline(tile: Tile)
	local stroke = tile.Base:FindFirstChildOfClass("UIStroke")
	if not stroke then
		return
	end
	stroke.Color = Color3.new(1, 1, 1)
	stroke.Thickness = 4
	local gradient = Widgets.gradient(RAINBOW, 0)
	gradient.Parent = stroke
	game:GetService("TweenService")
		:Create(gradient, TweenInfo.new(2.5, Enum.EasingStyle.Linear, Enum.EasingDirection.InOut, -1), { Rotation = 360 })
		:Play()
end

-- Featured offer ------------------------------------------------------------------

local function makeOffer(parent: Frame)
	local product = Rules.ProductByKey.Offer
	if not product then
		return
	end
	local group = Widgets.frame({
		Name = "Offer",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(90, 92),
		Size = UDim2.fromOffset(180, 184),
		Parent = parent,
	})
	Windows.registerHud(group)
	Effects.sunburst({ Parent = group, Size = UDim2.fromOffset(230, 230), Position = UDim2.fromOffset(90, 84), Rays = 8, Color = Theme.Gold })
	local button = create("TextButton", {
		Name = "Button",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 8),
		Size = UDim2.fromOffset(140, 160),
		BackgroundTransparency = 1,
		AutoButtonColor = false,
		Text = "",
		ZIndex = 2,
		Parent = group,
	})
	local hover = create("UIScale", { Parent = button })
	local tag = create("Frame", {
		Name = "Tag",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.fromScale(0.5, 0),
		Size = UDim2.fromOffset(96, 28),
		BackgroundColor3 = Theme.Red,
		Rotation = -6,
		ZIndex = 4,
		Parent = button,
	}, { Widgets.round(), Widgets.stroke(3), Widgets.shading() })
	Widgets.text({ Text = Text.OfferTag, Font = "Title", TextSize = 19, Stroke = 2.5, ZIndex = 5, Position = UDim2.fromOffset(0, 2), Parent = tag })
	Widgets.text({ Name = "Icon", Text = product.Icon or "💰", TextSize = 70, Stroke = false, Position = UDim2.fromOffset(0, 22), Size = UDim2.new(1, 0, 0, 80), ZIndex = 3, Parent = button })
	local amount = Widgets.text({
		Name = "Amount",
		Text = "+" .. Rules.describe(product.Grant).Short,
		Font = "Title",
		TextSize = 32,
		Stroke = 3.5,
		StrokeColor = Color3.fromRGB(80, 45, 0),
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 96),
		Size = UDim2.fromOffset(180, 36),
		ZIndex = 4,
		Parent = button,
	})
	Widgets.gradient({ Color3.fromRGB(255, 250, 170), Theme.Gold }, 90).Parent = amount
	local price = create("Frame", {
		Name = "Price",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 132),
		Size = UDim2.fromOffset(104, 30),
		BackgroundColor3 = Theme.Green,
		ZIndex = 4,
		Parent = button,
	}, { Widgets.round(), Widgets.stroke(3), Widgets.shading() })
	local priceLabel = Widgets.text({ Text = "", Font = "Title", TextSize = 20, ZIndex = 5, Position = UDim2.fromOffset(0, 2), Parent = price })
	Purchases.observePrice("Product", "Offer", function(text)
		priceLabel.Text = text
	end)

	-- gentle floating
	game:GetService("TweenService")
		:Create(button, TweenInfo.new(1.4, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), { Position = UDim2.new(0.5, 0, 0, 2) })
		:Play()
	button.MouseEnter:Connect(function()
		Widgets.tween(hover, 0.12, { Scale = 1.07 })
	end)
	button.MouseLeave:Connect(function()
		Widgets.tween(hover, 0.12, { Scale = 1 })
	end)
	button.Activated:Connect(function()
		Widgets.playSound("Click")
		Purchases.prompt("Product", "Offer")
	end)
end

-- Running boosts -------------------------------------------------------------------

local function refreshBoosts()
	local list = boostList
	if not list then
		return
	end
	local now = State.serverNow()
	for name, boost in Config.Boosts do
		local remaining = State.number("Boost_" .. name) - now
		local chip = boostChips[name]
		if remaining > 0 then
			if not chip then
				local frame = create("Frame", {
					Name = name,
					Size = UDim2.fromOffset(176, 34),
					BackgroundColor3 = Theme.Panel,
					BackgroundTransparency = 0.1,
					Parent = list,
				}, { Widgets.round(), Widgets.stroke(3) })
				local label = Widgets.text({
					Text = "",
					TextSize = 18,
					Scaled = true,
					XAlign = Enum.TextXAlignment.Left,
					Position = UDim2.fromOffset(12, 3),
					Size = UDim2.new(1, -20, 1, -6),
					Parent = frame,
				})
				chip = { Frame = frame, Label = label }
				boostChips[name] = chip
			end
			(chip :: any).Label.Text = ("%s %s  %s"):format(boost.Icon, boost.Label, Format.clock(remaining))
		elseif chip then
			chip.Frame:Destroy()
			boostChips[name] = nil
		end
	end
end

-- Public -----------------------------------------------------------------------------

function Hud.getTile(name: string): Tile?
	return tiles[name]
end

-- Floating "+N" next to a counter after a gain.
function Hud.showGain(stat: string, amount: number)
	local pill = pills[stat]
	local currency = Rules.CurrencyByKey[stat]
	if pill and currency and amount > 0 then
		Effects.floatText(pill.Frame, "+" .. Format.short(amount), currency.Colors, currency.Stroke)
	end
end

-- Called once per second by the client loop.
function Hud.tick()
	refreshBoosts()
end

-- callbacks: OpenShop, OpenRebirth, OpenIndex, OpenWheel, Invite
function Hud.build(screenGui: ScreenGui, callbacks: { [string]: () -> () })
	local left = Widgets.frame({
		Name = "HudLeft",
		AnchorPoint = Vector2.new(0, 0.5),
		Position = UDim2.new(0, 12, 0.54, 0),
		Size = UDim2.fromOffset(206, 460),
		Parent = screenGui,
	})
	Widgets.attachHudScale(left)

	local currencies = Widgets.frame({
		Name = "Currencies",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(103, 71),
		Size = UDim2.fromOffset(206, 142),
		Parent = left,
	})
	Windows.registerHud(currencies)
	for index, currency in Config.Currencies do
		makePill(currencies, currency, index, callbacks.OpenShop)
	end

	local buttons = Widgets.frame({
		Name = "Buttons",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Parent = left,
	})
	Windows.registerHud(buttons)
	local shop = makeTile(buttons, { Name = "Shop", Text = Text.ShopButton, Icon = "🛒", Color = Theme.Gold, OnClick = callbacks.OpenShop })
	makeTile(buttons, { Name = "Wheel", Text = Text.WheelButton, Icon = "🎡", Color = Theme.Pink, OnClick = callbacks.OpenWheel })
	makeTile(buttons, { Name = "Rebirth", Text = Text.RebirthButton, Icon = "🔁", Color = Theme.Purple, OnClick = callbacks.OpenRebirth })
	makeTile(buttons, { Name = "Invite", Text = Text.InviteButton, Icon = "💌", Color = Theme.Green, OnClick = callbacks.Invite })
	makeTile(buttons, { Name = "Index", Text = Text.IndexButton, Icon = "📖", Color = Theme.Cyan, OnClick = callbacks.OpenIndex })

	-- 2 columns on tall screens, 3 on short ones (phones in landscape) so the
	-- buttons stay clear of the thumbstick area
	local function arrange()
		local compact = screenGui.AbsoluteSize.Y > 0 and screenGui.AbsoluteSize.Y < 500
		local columns = if compact then 3 else 2
		local rows = math.ceil(#TILE_ORDER / columns)
		for index, name in TILE_ORDER do
			local column = (index - 1) % columns
			local row = math.floor((index - 1) / columns)
			tiles[name].Instance.Position = UDim2.fromOffset(column * TILE_STEP, row * TILE_STEP)
		end
		local width, height = columns * TILE_STEP - 14, rows * TILE_STEP - 14
		buttons.Size = UDim2.fromOffset(width, height)
		buttons.Position = UDim2.fromOffset(width / 2, 170 + height / 2)
		left.Size = UDim2.fromOffset(math.max(206, width), 170 + height)
		left.Position = UDim2.new(0, 12, if compact then 0.5 else 0.54, 0)
	end
	arrange()
	screenGui:GetPropertyChangedSignal("AbsoluteSize"):Connect(arrange)
	rainbowOutline(shop)

	local right = Widgets.frame({
		Name = "HudRight",
		AnchorPoint = Vector2.new(1, 0.5),
		Position = UDim2.new(1, -12, 0.5, 0),
		Size = UDim2.fromOffset(180, 330),
		Parent = screenGui,
	})
	Widgets.attachHudScale(right)
	makeOffer(right)
	local boosts = Widgets.frame({
		Name = "Boosts",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.fromOffset(90, 196),
		Size = UDim2.fromOffset(180, 130),
		Parent = right,
	}, { Widgets.list(Enum.FillDirection.Vertical, 6) })
	Windows.registerHud(boosts)
	boostList = boosts
	refreshBoosts()
end

return Hud
