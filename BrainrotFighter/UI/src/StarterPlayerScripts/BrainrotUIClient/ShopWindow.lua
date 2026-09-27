-- ShopWindow: game passes, boosts and coin packs, all bought with Robux.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Widgets = require(script.Parent:WaitForChild("Widgets"))
local State = require(script.Parent:WaitForChild("State"))
local Windows = require(script.Parent:WaitForChild("Windows"))
local Purchases = require(script.Parent:WaitForChild("Purchases"))

local Theme = Widgets.Theme
local Text = Config.Text
local create = Widgets.create

local ShopWindow = {}

local WIDTH, HEIGHT = 740, 480

local function sectionTitle(parent: Instance, text: string, order: number)
	Widgets.text({
		Name = "Section",
		Text = text,
		Font = "Title",
		TextSize = 26,
		Stroke = 3,
		XAlign = Enum.TextXAlignment.Left,
		Size = UDim2.new(1, -8, 0, 30),
		LayoutOrder = order,
		ZIndex = 33,
		Parent = parent,
	})
end

local function rewardChip(parent: Instance, text: string, order: number)
	local chip = create("Frame", {
		Name = "Chip",
		Size = UDim2.fromOffset(92, 28),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 0.55,
		LayoutOrder = order,
		ZIndex = 34,
		Parent = parent,
	}, { Widgets.round() })
	Widgets.text({ Text = text, TextSize = 18, Stroke = 2, ZIndex = 35, Parent = chip })
end

local function passCard(parent: Instance, pass: { [string]: any }, order: number)
	local card = create("Frame", {
		Name = pass.Key,
		Size = UDim2.new(1, -14, 0, 128),
		BackgroundColor3 = Color3.new(1, 1, 1),
		LayoutOrder = order,
		ZIndex = 33,
		Parent = parent,
	}, { Widgets.corner(16), Widgets.stroke(3), Widgets.gradient(pass.Colors, 0) })
	create("Frame", {
		Name = "Shine",
		Position = UDim2.fromOffset(6, 5),
		Size = UDim2.new(1, -12, 0.36, 0),
		BackgroundColor3 = Color3.new(1, 1, 1),
		BackgroundTransparency = 0.8,
		ZIndex = 33,
		Parent = card,
	}, { Widgets.corner(12) })
	local iconCircle = Widgets.circle({
		Name = "Icon",
		AnchorPoint = Vector2.new(0, 0.5),
		Position = UDim2.new(0, 14, 0.5, 0),
		Size = UDim2.fromOffset(96, 96),
		BackgroundColor3 = Color3.new(1, 1, 1),
		BackgroundTransparency = 0.65,
		ZIndex = 34,
		Parent = card,
	}, { Widgets.stroke(3) })
	Widgets.text({ Text = pass.Icon, TextSize = 58, Stroke = false, ZIndex = 35, Parent = iconCircle })
	Widgets.text({
		Name = "Name",
		Text = pass.Name,
		Font = "Title",
		TextSize = 30,
		Stroke = 3,
		XAlign = Enum.TextXAlignment.Left,
		Position = UDim2.fromOffset(124, 12),
		Size = UDim2.new(1, -310, 0, 34),
		ZIndex = 35,
		Parent = card,
	})
	Widgets.text({
		Name = "Description",
		Text = pass.Description,
		TextSize = 18,
		Stroke = 2,
		Wrapped = true,
		XAlign = Enum.TextXAlignment.Left,
		YAlign = Enum.TextYAlignment.Top,
		Position = UDim2.fromOffset(124, 48),
		Size = UDim2.new(1, -310, 0, 40),
		ZIndex = 35,
		Parent = card,
	})
	if pass.Rewards then
		local chips = Widgets.frame({
			Name = "Rewards",
			Position = UDim2.fromOffset(124, 88),
			Size = UDim2.new(1, -310, 0, 28),
			ZIndex = 34,
			Parent = card,
		}, { Widgets.list(Enum.FillDirection.Horizontal, 6, Enum.HorizontalAlignment.Left) })
		local chipOrder = 0
		for _, key in { "Coins", "Gems", "Power", "Spins" } do
			if pass.Rewards[key] then
				chipOrder += 1
				local info = Rules.describe({ [key] = pass.Rewards[key] })
				local amount = string.gsub(info.Short, "^%+", "")
				rewardChip(chips, info.Icon .. " " .. amount, chipOrder)
			end
		end
	end
	local buy = Widgets.button({
		Name = "Buy",
		Parent = card,
		AnchorPoint = Vector2.new(1, 0.5),
		Position = UDim2.new(1, -16, 0.5, 0),
		Size = UDim2.fromOffset(160, 60),
		Color = Theme.Green,
		Text = "R$ ?",
		TextSize = 28,
		ZIndex = 36,
		OnClick = function()
			Purchases.prompt("Pass", pass.Key)
		end,
	})
	Purchases.observePrice("Pass", pass.Key, function(price)
		if State.get("Pass_" .. pass.Key) ~= true then
			buy.SetText(price)
		end
	end)
	State.observe("Pass_" .. pass.Key, function(owned)
		if owned == true then
			buy.SetText(Text.Owned)
			buy.SetEnabled(false)
		end
	end)
	return buy
end

local function productCard(parent: Instance, product: { [string]: any }, order: number)
	local card = Widgets.panel({
		Name = product.Key,
		LayoutOrder = order,
		ZIndex = 33,
		Parent = parent,
	})
	Widgets.text({ Name = "Icon", Text = product.Icon, TextSize = 54, Stroke = false, Position = UDim2.fromOffset(0, 8), Size = UDim2.new(1, 0, 0, 64), ZIndex = 34, Parent = card })
	Widgets.text({ Name = "Name", Text = product.Name, Font = "Title", TextSize = 24, Stroke = 3, Position = UDim2.fromOffset(6, 74), Size = UDim2.new(1, -12, 0, 28), ZIndex = 34, Parent = card })
	Widgets.text({
		Name = "Description",
		Text = product.Description or "",
		TextSize = 17,
		Stroke = 2,
		Color = Theme.Muted,
		Position = UDim2.fromOffset(6, 102),
		Size = UDim2.new(1, -12, 0, 22),
		ZIndex = 34,
		Parent = card,
	})
	local buy = Widgets.button({
		Name = "Buy",
		Parent = card,
		AnchorPoint = Vector2.new(0.5, 1),
		Position = UDim2.new(0.5, 0, 1, -12),
		Size = UDim2.new(1, -28, 0, 50),
		Color = Theme.Green,
		Text = "R$ ?",
		TextSize = 24,
		ZIndex = 35,
		OnClick = function()
			Purchases.prompt("Product", product.Key)
		end,
	})
	Purchases.observePrice("Product", product.Key, buy.SetText)
	return buy
end

local function productRow(parent: Instance, section: string, order: number): GuiObject?
	local row = Widgets.frame({
		Name = section,
		Size = UDim2.new(1, -14, 0, 196),
		LayoutOrder = order,
		ZIndex = 33,
		Parent = parent,
	}, {
		create("UIGridLayout", {
			CellSize = UDim2.new(1 / 3, -8, 0, 190),
			CellPadding = UDim2.fromOffset(12, 0),
			HorizontalAlignment = Enum.HorizontalAlignment.Center,
			SortOrder = Enum.SortOrder.LayoutOrder,
		}),
	})
	local first = nil
	local count = 0
	for _, product in Config.Products do
		if product.Section == section then
			count += 1
			local buy = productCard(row, product, count)
			first = first or buy.Instance
		end
	end
	return first
end

function ShopWindow.build()
	local window = Windows.create("Shop", { Title = Text.ShopTitle, Width = WIDTH, Height = HEIGHT, Colors = Theme.Windows.Shop })
	local list = create("ScrollingFrame", {
		Name = "List",
		Size = UDim2.fromScale(1, 1),
		BackgroundTransparency = 1,
		ScrollBarThickness = 6,
		ScrollBarImageColor3 = Theme.Muted,
		ScrollingDirection = Enum.ScrollingDirection.Y,
		CanvasSize = UDim2.new(),
		AutomaticCanvasSize = Enum.AutomaticSize.Y,
		ZIndex = 32,
		Parent = window.Body,
	}, {
		Widgets.list(Enum.FillDirection.Vertical, 10),
		Widgets.padding(12, 4, 12, 4),
	})

	local order = 0
	local function nextOrder(): number
		order += 1
		return order
	end

	sectionTitle(list, Text.SectionPasses, nextOrder())
	local firstButton = nil
	for _, pass in Config.GamePasses do
		local buy = passCard(list, pass, nextOrder())
		firstButton = firstButton or buy.Instance
	end
	sectionTitle(list, Text.SectionBoosts, nextOrder())
	productRow(list, "Boosts", nextOrder())
	sectionTitle(list, Text.SectionCoins, nextOrder())
	productRow(list, "Coins", nextOrder())

	window.DefaultSelection = firstButton
	window.OnOpen[#window.OnOpen + 1] = function()
		list.CanvasPosition = Vector2.zero
	end
end

return ShopWindow
