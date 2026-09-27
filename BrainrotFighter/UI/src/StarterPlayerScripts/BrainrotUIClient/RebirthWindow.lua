-- RebirthWindow: progress towards the next rebirth, what it gives, and the
-- buttons to rebirth (server checked) or skip it with Robux.

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

local Theme = Widgets.Theme
local Text = Config.Text

local RebirthWindow = {}

-- Replaced by build(); refreshes the texts, the bar and the button state.
function RebirthWindow.refresh() end

local WIDTH, HEIGHT = 620, 440

local function statCard(parent: Instance, caption: string, x: number, valueColor: Color3): TextLabel
	local card = Widgets.panel({
		Name = caption,
		Position = UDim2.fromOffset(x, 40),
		Size = UDim2.fromOffset(210, 124),
		ZIndex = 33,
		Parent = parent,
	})
	Widgets.text({ Name = "Caption", Text = caption, Font = "Title", TextSize = 22, Color = Theme.Muted, Stroke = 2.5, Position = UDim2.fromOffset(0, 8), Size = UDim2.new(1, 0, 0, 26), ZIndex = 34, Parent = card })
	local value = Widgets.text({ Name = "Value", Text = "x1", Font = "Title", TextSize = 48, Color = valueColor, Stroke = 4, Position = UDim2.fromOffset(0, 34), Size = UDim2.new(1, 0, 0, 54), ZIndex = 34, Parent = card })
	Widgets.text({ Name = "Hint", Text = Text.PowerMultiplier, TextSize = 16, Scaled = true, Color = Theme.Muted, Stroke = 2, Position = UDim2.fromOffset(6, 90), Size = UDim2.new(1, -12, 0, 22), ZIndex = 34, Parent = card })
	return value
end

-- request(action, argument) -> result table from the server
function RebirthWindow.build(request: (string, any?) -> { [string]: any })
	local window = Windows.create("Rebirth", { Title = Text.RebirthTitle, Width = WIDTH, Height = HEIGHT, Colors = Theme.Windows.Rebirth })
	local body = window.Body
	local innerWidth = WIDTH - 40

	local subtitle = Widgets.text({ Name = "Subtitle", Text = "", TextSize = 22, Color = Theme.Muted, Stroke = 2, Position = UDim2.fromOffset(0, 6), Size = UDim2.new(1, 0, 0, 28), ZIndex = 33, Parent = body })
	local before = statCard(body, Text.Before, 40, Theme.Text)
	local after = statCard(body, Text.After, innerWidth - 250, Color3.fromRGB(140, 255, 120))
	Widgets.text({ Name = "Arrow", Text = "➡️", TextSize = 50, Stroke = false, AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 72), Size = UDim2.fromOffset(80, 60), ZIndex = 33, Parent = body })
	local reward = Widgets.text({ Name = "Reward", Text = "", TextSize = 24, Color = Color3.fromRGB(140, 235, 255), Stroke = 2.5, Position = UDim2.fromOffset(0, 176), Size = UDim2.new(1, 0, 0, 30), ZIndex = 33, Parent = body })
	local bar = Widgets.progressBar({
		Name = "Progress",
		Parent = body,
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 214),
		Size = UDim2.new(1, -60, 0, 42),
		Colors = { Color3.fromRGB(205, 110, 255), Color3.fromRGB(255, 90, 180) },
		TextSize = 22,
	})
	bar.Instance.ZIndex = 33
	Widgets.text({ Name = "Warning", Text = Text.RebirthWarning, TextSize = 18, Color = Color3.fromRGB(255, 190, 120), Stroke = 2, Position = UDim2.fromOffset(0, 264), Size = UDim2.new(1, 0, 0, 24), ZIndex = 33, Parent = body })

	local rebirthButton, skipButton
	rebirthButton = Widgets.button({
		Name = "Rebirth",
		Parent = body,
		AnchorPoint = Vector2.new(1, 1),
		Position = UDim2.new(0.5, -10, 1, -8),
		Size = UDim2.fromOffset(230, 66),
		Color = Theme.Green,
		Text = Text.RebirthAction,
		TextSize = 30,
		ZIndex = 34,
		OnClick = function()
			rebirthButton.SetEnabled(false)
			local result = request("Rebirth")
			if result.ok then
				Windows.close()
				Effects.rewardPopup("🔁", Text.RebirthDone, Text.RebirthDoneSub:format(Format.multiplier(Rules.rebirthMultiplier(result.rebirths or 0))), Theme.Purple)
			else
				Notify.show(result.message or Text.GenericError, "error")
			end
			RebirthWindow.refresh()
		end,
	})
	skipButton = Widgets.button({
		Name = "Skip",
		Parent = body,
		AnchorPoint = Vector2.new(0, 1),
		Position = UDim2.new(0.5, 10, 1, -8),
		Size = UDim2.fromOffset(230, 66),
		Color = Theme.Gold,
		Text = Text.RebirthSkip,
		TextSize = 26,
		SubText = "R$ ?",
		SubTextSize = 18,
		ZIndex = 34,
		OnClick = function()
			Purchases.prompt("Product", Config.Rebirth.SkipProduct)
		end,
	})
	Purchases.observePrice("Product", Config.Rebirth.SkipProduct, skipButton.SetSubText)
	window.DefaultSelection = rebirthButton.Instance

	function RebirthWindow.refresh()
		local rebirths = State.number("Rebirths")
		local power = State.number("Power")
		local required = Rules.rebirthRequirement(rebirths)
		subtitle.Text = Text.RebirthNumber:format(rebirths + 1)
		before.Text = "x" .. Format.multiplier(Rules.rebirthMultiplier(rebirths))
		after.Text = "x" .. Format.multiplier(Rules.rebirthMultiplier(rebirths + 1))
		reward.Text = Text.RebirthReward:format(Format.short(Rules.rebirthGems(rebirths + 1)))
		bar.Set(power / required, ("%s / %s 💪"):format(Format.short(power), Format.short(required)))
		rebirthButton.SetEnabled(power >= required)
	end

	State.observe("Power", RebirthWindow.refresh)
	State.observe("Rebirths", RebirthWindow.refresh)
end

-- True when the player has enough power to rebirth (drives the HUD badge).
function RebirthWindow.isReady(): boolean
	return State.number("Power") >= Rules.rebirthRequirement(State.number("Rebirths"))
end

return RebirthWindow
