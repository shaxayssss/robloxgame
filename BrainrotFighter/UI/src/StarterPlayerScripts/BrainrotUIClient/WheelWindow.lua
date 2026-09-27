-- WheelWindow: the lucky wheel. One free spin every FreeSpinCooldown, extra
-- spins bought with Robux, odds always displayed. The server draws the prize;
-- the wheel only animates to it.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Format = require(shared:WaitForChild("Format"))
local Widgets = require(script.Parent:WaitForChild("Widgets"))
local State = require(script.Parent:WaitForChild("State"))
local Windows = require(script.Parent:WaitForChild("Windows"))
local Notify = require(script.Parent:WaitForChild("Notify"))
local Effects = require(script.Parent:WaitForChild("Effects"))
local Purchases = require(script.Parent:WaitForChild("Purchases"))
local Wheel = require(script.Parent:WaitForChild("Wheel"))

local Theme = Widgets.Theme
local Text = Config.Text
local create = Widgets.create

local WheelWindow = {}

local WIDTH, HEIGHT = 800, 500
local DIAMETER = 390
local SPIN_TIME = 4.2

local spinning = false

-- Spins the player can use right now (bought + the free one when ready).
function WheelWindow.availableSpins(): number
	local free = if State.serverNow() >= State.number("FreeSpinAt") then 1 else 0
	return State.number("Spins") + free
end

-- Replaced by build(); refreshes counters and buttons.
function WheelWindow.refresh() end

local function oddsPanel(parent: Instance, y: number, width: number)
	local rewards = Config.Wheel.Rewards
	local panel = Widgets.panel({
		Name = "Odds",
		Position = UDim2.fromOffset(0, y),
		Size = UDim2.fromOffset(width, 34 + #rewards * 22),
		BackgroundColor3 = Theme.Panel,
		ZIndex = 33,
		Parent = parent,
	})
	Widgets.text({ Text = Text.Odds, Font = "Title", TextSize = 18, Color = Theme.Muted, Stroke = 2, Position = UDim2.fromOffset(0, 6), Size = UDim2.new(1, 0, 0, 22), ZIndex = 34, Parent = panel })
	local odds = Rules.wheelOdds()
	for index, reward in rewards do
		local rowY = 30 + (index - 1) * 22
		Widgets.circle({
			Name = "Dot",
			Position = UDim2.fromOffset(14, rowY + 4),
			Size = UDim2.fromOffset(14, 14),
			BackgroundColor3 = reward.Color or Theme.Blue,
			ZIndex = 34,
			Parent = panel,
		}, { Widgets.stroke(2) })
		local info = Rules.describe(reward)
		Widgets.text({ Text = info.Icon .. " " .. info.Long, TextSize = 16, Stroke = 2, XAlign = Enum.TextXAlignment.Left, Position = UDim2.fromOffset(36, rowY), Size = UDim2.new(1, -100, 0, 22), ZIndex = 34, Parent = panel })
		Widgets.text({ Text = Format.percent(odds[index]), Font = "Title", TextSize = 17, Stroke = 2, XAlign = Enum.TextXAlignment.Right, Position = UDim2.new(1, -74, 0, rowY), Size = UDim2.fromOffset(60, 22), ZIndex = 34, Parent = panel })
	end
end

function WheelWindow.build(request: (string, any?) -> { [string]: any })
	local window = Windows.create("Wheel", { Title = Text.WheelTitle, Width = WIDTH, Height = HEIGHT, Colors = Theme.Windows.Wheel })
	local body = window.Body

	local wheel = Wheel.new({ Parent = body, Position = UDim2.fromOffset(28, 26), Diameter = DIAMETER, Rewards = Config.Wheel.Rewards })

	local column = Widgets.frame({ Name = "Side", Position = UDim2.fromOffset(460, 8), Size = UDim2.new(1, -460, 1, -8), ZIndex = 33, Parent = body })
	local columnWidth = WIDTH - 40 - 460
	local spinsLabel = Widgets.text({ Name = "Spins", Text = "", Font = "Title", TextSize = 34, Stroke = 3.5, Size = UDim2.new(1, 0, 0, 40), ZIndex = 33, Parent = column })
	local freeLabel = Widgets.text({ Name = "Free", Text = "", TextSize = 19, Stroke = 2, Position = UDim2.fromOffset(0, 40), Size = UDim2.new(1, 0, 0, 26), ZIndex = 33, Parent = column })

	local spinButton
	spinButton = Widgets.button({
		Name = "Spin",
		Parent = column,
		Position = UDim2.fromOffset(0, 72),
		Size = UDim2.fromOffset(columnWidth, 68),
		Color = Theme.Green,
		Text = Text.SpinAction,
		TextSize = 34,
		Depth = 6,
		ZIndex = 34,
		OnClick = function()
			if spinning then
				return
			end
			spinning = true
			WheelWindow.refresh()
			local result = request("Spin")
			if not result.ok or type(result.index) ~= "number" then
				spinning = false
				WheelWindow.refresh()
				Notify.show(result.message or Text.GenericError, "error")
				return
			end
			local reward = Config.Wheel.Rewards[result.index]
			wheel:SpinTo(result.index, SPIN_TIME, function()
				Widgets.playSound("Tick")
			end, function()
				spinning = false
				WheelWindow.refresh()
				local info = Rules.describe(reward)
				if Windows.isOpen("Wheel") then
					Effects.rewardPopup(info.Icon, Text.WheelWon, info.Long, reward.Color)
				else
					Notify.show(Text.WheelWon .. " " .. info.Long, "reward")
				end
			end)
		end,
	})
	window.DefaultSelection = spinButton.Instance

	-- Robux spin packs (hidden where paid random items are restricted)
	local packs = Widgets.frame({
		Name = "Packs",
		Position = UDim2.fromOffset(0, 160),
		Size = UDim2.new(1, 0, 0, 70),
		ZIndex = 33,
		Parent = column,
	}, { Widgets.list(Enum.FillDirection.Horizontal, 12) })
	local restrictedLabel = Widgets.text({ Name = "Restricted", Text = Text.RandomRestricted, TextSize = 17, Color = Theme.Muted, Stroke = 2, Position = UDim2.fromOffset(0, 160), Size = UDim2.new(1, 0, 0, 44), Wrapped = true, Visible = false, ZIndex = 33, Parent = column })
	local packColors = { Theme.Blue, Theme.Purple }
	for index, key in Config.Wheel.SpinProducts do
		local product = Rules.ProductByKey[key]
		if product then
			local button = Widgets.button({
				Name = key,
				Parent = packs,
				LayoutOrder = index,
				Size = UDim2.fromOffset((columnWidth - 12) / 2, 66),
				Color = packColors[index] or Theme.Blue,
				Text = Text.SpinsProduct:format(product.Grant.Spins or 0),
				TextSize = 20,
				SubText = "R$ ?",
				SubTextSize = 18,
				ZIndex = 34,
				OnClick = function()
					Purchases.prompt("Product", key)
				end,
			})
			Purchases.observePrice("Product", key, button.SetSubText)
			if product.Tag then
				local tag = create("Frame", {
					Name = "Tag",
					AnchorPoint = Vector2.new(0.5, 0.5),
					Position = UDim2.new(0.5, 0, 0, -4),
					Size = UDim2.fromOffset(118, 24),
					BackgroundColor3 = Theme.Red,
					Rotation = -4,
					ZIndex = 40,
					Parent = button.Instance,
				}, { Widgets.round(), Widgets.stroke(2.5), Widgets.shading() })
				Widgets.text({ Text = product.Tag, Font = "Title", TextSize = 15, Stroke = 2, ZIndex = 41, Position = UDim2.fromOffset(0, 1), Parent = tag })
			end
		end
	end

	oddsPanel(column, 240, columnWidth)

	function WheelWindow.refresh()
		local bought = State.number("Spins")
		local freeReady = State.serverNow() >= State.number("FreeSpinAt")
		spinsLabel.Text = Text.Spins:format(WheelWindow.availableSpins())
		if freeReady then
			freeLabel.Text = Text.FreeSpinReady
			freeLabel.TextColor3 = Color3.fromRGB(140, 255, 120)
		else
			freeLabel.Text = Text.FreeSpinIn:format(Format.clock(State.number("FreeSpinAt") - State.serverNow()))
			freeLabel.TextColor3 = Theme.Muted
		end
		spinButton.SetEnabled(not spinning and (freeReady or bought > 0))
		local restricted = State.get("PaidRandomRestricted") == true
		packs.Visible = not restricted
		restrictedLabel.Visible = restricted
	end

	State.observe("Spins", WheelWindow.refresh)
	State.observe("FreeSpinAt", WheelWindow.refresh)
	State.observe("PaidRandomRestricted", WheelWindow.refresh)
	table.insert(window.OnOpen, function()
		wheel:SetLightsActive(true)
		WheelWindow.refresh()
	end)
	table.insert(window.OnClose, function()
		wheel:SetLightsActive(false)
	end)
end

return WheelWindow
