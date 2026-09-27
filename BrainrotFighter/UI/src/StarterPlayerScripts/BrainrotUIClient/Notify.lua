-- Notify: toast messages stacked at the top of the screen.
--   Notify.show("Hello", "success")   -- kind: info | success | error | reward

local Widgets = require(script.Parent:WaitForChild("Widgets"))

local Theme = Widgets.Theme
local create = Widgets.create

local Notify = {}

local KIND_COLORS = {
	info = Theme.Blue,
	success = Theme.Green,
	error = Theme.Red,
	reward = Theme.Gold,
}
local MAX_TOASTS = 4

local container: Frame? = nil
local active: { Frame } = {}
local order = 0

local function dismiss(toast: Frame)
	local index = table.find(active, toast)
	if not index then
		return
	end
	table.remove(active, index)
	local scale = toast:FindFirstChildOfClass("UIScale")
	if scale then
		Widgets.tween(scale, 0.18, { Scale = 0 }, Enum.EasingStyle.Back, Enum.EasingDirection.In).Completed:Once(function()
			toast:Destroy()
		end)
	else
		toast:Destroy()
	end
end

function Notify.init(screenGui: ScreenGui)
	container = Widgets.frame({
		Name = "Toasts",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 6),
		Size = UDim2.fromOffset(460, 230),
		ZIndex = 80,
		Parent = screenGui,
	}, { Widgets.list(Enum.FillDirection.Vertical, 6) })
	Widgets.attachHudScale(container :: Frame)
end

function Notify.show(text: string, kind: string?, duration: number?)
	local parent = container
	if not parent then
		return
	end
	order += 1
	local color = KIND_COLORS[kind or "info"] or Theme.Blue
	local toast = create("Frame", {
		Name = "Toast",
		Size = UDim2.fromOffset(440, 46),
		BackgroundColor3 = Theme.Panel,
		BackgroundTransparency = 0.04,
		LayoutOrder = order,
		ZIndex = 80,
		Parent = parent,
	}, { Widgets.corner(14), Widgets.stroke(3) })
	create("Frame", {
		Name = "Accent",
		Size = UDim2.new(0, 12, 1, 0),
		BackgroundColor3 = color,
		ZIndex = 81,
		Parent = toast,
	}, { Widgets.corner(14) })
	Widgets.text({
		Text = text,
		TextSize = 20,
		Scaled = true,
		XAlign = Enum.TextXAlignment.Left,
		Position = UDim2.fromOffset(24, 4),
		Size = UDim2.new(1, -34, 1, -8),
		ZIndex = 82,
		Parent = toast,
	})
	local scale = create("UIScale", { Scale = 0.5, Parent = toast })
	Widgets.tween(scale, 0.25, { Scale = 1 }, Enum.EasingStyle.Back)

	table.insert(active, toast)
	while #active > MAX_TOASTS do
		dismiss(active[1])
	end
	task.delay(duration or 3, dismiss, toast)
end

return Notify
