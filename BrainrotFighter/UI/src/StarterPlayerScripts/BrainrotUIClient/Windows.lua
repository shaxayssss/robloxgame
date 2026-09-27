-- Windows: the menus (Shop, Rebirth, Index, Wheel). One open at a time.
-- Opening zooms the HUD out, dims the screen and pops the window in;
-- closing does the reverse. Close with the X, a click outside, or gamepad B.

local ContextActionService = game:GetService("ContextActionService")
local GuiService = game:GetService("GuiService")
local UserInputService = game:GetService("UserInputService")

local Widgets = require(script.Parent:WaitForChild("Widgets"))

local Theme = Widgets.Theme
local create = Widgets.create

local Windows = {}

export type Window = {
	Name: string,
	Root: Frame,
	Body: Frame,
	Scale: UIScale,
	Width: number,
	Height: number,
	DefaultSelection: GuiObject?,
	OnOpen: { () -> () },
	OnClose: { () -> () },
}

local CLOSE_ACTION = "BrainrotUICloseWindow"
local STAGGER = 0.035

local screenGui: ScreenGui? = nil
local dim: TextButton? = nil
local holder: Frame? = nil
local windows: { [string]: Window } = {}
local hudGroups: { UIScale } = {}
local current: Window? = nil
local busy = false

-- Largest scale that keeps the window on screen, capped relative to the HUD.
local function fitScale(window: Window): number
	local gui = screenGui :: ScreenGui
	local size = gui.AbsoluteSize
	if size.X <= 0 then
		return 1
	end
	local fit = math.min(
		(size.X - 30) / window.Width,
		(size.Y - 50) / (window.Height + 36),
		1.1 * math.max(Widgets.getHudScale(), 0.8)
	)
	return math.max(fit, 0.35)
end

local function hideHud()
	for index, scale in hudGroups do
		Widgets.tween(scale, 0.16, { Scale = 0 }, Enum.EasingStyle.Back, Enum.EasingDirection.In, (index - 1) * STAGGER)
	end
end

local function showHud()
	for index, scale in hudGroups do
		Widgets.tween(scale, 0.24, { Scale = 1 }, Enum.EasingStyle.Back, Enum.EasingDirection.Out, (index - 1) * STAGGER)
	end
end

local function bindClose()
	ContextActionService:BindActionAtPriority(CLOSE_ACTION, function(_, state)
		if state == Enum.UserInputState.Begin then
			Windows.close()
		end
		return Enum.ContextActionResult.Sink
	end, false, Enum.ContextActionPriority.High.Value, Enum.KeyCode.ButtonB)
end

local function usingGamepad(): boolean
	local last = UserInputService:GetLastInputType()
	return last == Enum.UserInputType.Gamepad1
		or last == Enum.UserInputType.Gamepad2
		or last == Enum.UserInputType.Gamepad3
		or last == Enum.UserInputType.Gamepad4
end

-- A HUD group that zooms out while a window is open (gets its own UIScale).
function Windows.registerHud(guiObject: GuiObject)
	local scale = create("UIScale", { Name = "HideScale", Parent = guiObject })
	table.insert(hudGroups, scale)
end

-- Builds the frame of a window. Options: Title, Width, Height, Colors.
function Windows.create(name: string, options: { [string]: any }): Window
	local width, height = options.Width, options.Height
	local root = create("Frame", {
		Name = name,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.new(0.5, 0, 0.5, 16),
		Size = UDim2.fromOffset(width, height),
		BackgroundColor3 = Color3.new(1, 1, 1),
		Active = true,
		Visible = false,
		ZIndex = 30,
		Parent = holder,
	}, {
		Widgets.corner(20),
		Widgets.stroke(4),
		Widgets.gradient({ Theme.PanelLight, Theme.Panel }, 90),
	})
	local scale = create("UIScale", { Parent = root })

	-- title ribbon across the top edge
	local banner = create("Frame", {
		Name = "Banner",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.new(0.5, 0, 0, 0),
		Size = UDim2.fromOffset(math.min(360, width - 150), 60),
		BackgroundColor3 = Color3.new(1, 1, 1),
		ZIndex = 32,
		Parent = root,
	}, { Widgets.corner(16), Widgets.stroke(4), Widgets.gradient(options.Colors, 90) })
	create("Frame", {
		Name = "Shine",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 4),
		Size = UDim2.new(1, -14, 0.4, 0),
		BackgroundColor3 = Color3.new(1, 1, 1),
		BackgroundTransparency = 0.7,
		ZIndex = 32,
		Parent = banner,
	}, { Widgets.corner(12) })
	Widgets.text({
		Name = "Title",
		Text = options.Title,
		Font = "Title",
		TextSize = 38,
		Stroke = 4,
		Position = UDim2.fromOffset(0, 4),
		ZIndex = 33,
		Parent = banner,
	})

	local body = Widgets.frame({
		Name = "Body",
		Position = UDim2.fromOffset(20, 42),
		Size = UDim2.new(1, -40, 1, -58),
		ZIndex = 31,
		Parent = root,
	})

	local window: Window = {
		Name = name,
		Root = root,
		Body = body,
		Scale = scale,
		Width = width,
		Height = height,
		DefaultSelection = nil,
		OnOpen = {},
		OnClose = {},
	}

	Widgets.button({
		Name = "Close",
		Parent = root,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.new(1, -10, 0, 10),
		Size = UDim2.fromOffset(54, 54),
		Color = Theme.Red,
		Text = "X",
		TextSize = 30,
		Radius = 14,
		ZIndex = 40,
		OnClick = function()
			Windows.close()
		end,
	})

	windows[name] = window
	return window
end

function Windows.isOpen(name: string): boolean
	local window = current
	return window ~= nil and window.Name == name
end

function Windows.open(name: string)
	local window = windows[name]
	if not window or busy or current == window then
		return
	end
	local previous = current
	if previous then
		-- switching directly from another window
		previous.Root.Visible = false
		for _, fn in previous.OnClose do
			task.spawn(fn)
		end
	else
		hideHud()
	end
	busy = true
	current = window
	local shade = dim :: TextButton
	shade.Visible = true
	Widgets.tween(shade, 0.2, { BackgroundTransparency = 0.45 })
	local fit = fitScale(window)
	window.Scale.Scale = fit * 0.6
	window.Root.Visible = true
	Widgets.playSound("Open")
	for _, fn in window.OnOpen do
		task.spawn(fn)
	end
	Widgets.tween(window.Scale, 0.3, { Scale = fit }, Enum.EasingStyle.Back).Completed:Once(function()
		busy = false
	end)
	bindClose()
	if usingGamepad() and window.DefaultSelection then
		GuiService.SelectedObject = window.DefaultSelection
	end
end

function Windows.close()
	local window = current
	if not window or busy then
		return
	end
	busy = true
	current = nil
	ContextActionService:UnbindAction(CLOSE_ACTION)
	if GuiService.SelectedObject and GuiService.SelectedObject:IsDescendantOf(window.Root) then
		GuiService.SelectedObject = nil
	end
	local shade = dim :: TextButton
	Widgets.tween(shade, 0.2, { BackgroundTransparency = 1 })
	Widgets.tween(window.Scale, 0.2, { Scale = 0 }, Enum.EasingStyle.Back, Enum.EasingDirection.In).Completed:Once(function()
		window.Root.Visible = false
		shade.Visible = false
		for _, fn in window.OnClose do
			task.spawn(fn)
		end
		showHud()
		busy = false
	end)
end

function Windows.toggle(name: string)
	if Windows.isOpen(name) then
		Windows.close()
	else
		Windows.open(name)
	end
end

function Windows.init(gui: ScreenGui)
	screenGui = gui
	local shade = create("TextButton", {
		Name = "Dim",
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 1,
		AutoButtonColor = false,
		Text = "",
		Visible = false,
		ZIndex = 20,
		Parent = gui,
	})
	shade.Activated:Connect(function()
		Windows.close()
	end)
	dim = shade
	holder = Widgets.frame({ Name = "Windows", Size = UDim2.fromScale(1, 1), ZIndex = 30, Parent = gui })
	gui:GetPropertyChangedSignal("AbsoluteSize"):Connect(function()
		local window = current
		if window and not busy then
			window.Scale.Scale = fitScale(window)
		end
	end)
end

return Windows
