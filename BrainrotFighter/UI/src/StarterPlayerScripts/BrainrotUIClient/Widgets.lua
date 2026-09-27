-- Widgets: factory for the cartoon style of the interface (thick outlines,
-- glossy chunky buttons, gradient text), plus sounds and screen scaling.
-- Everything is drawn with frames, strokes and gradients: no image to upload.

local TweenService = game:GetService("TweenService")
local SoundService = game:GetService("SoundService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("BrainrotUI"):WaitForChild("UIConfig"))
local Theme = Config.Theme

local Widgets = {}
Widgets.Theme = Theme

local WHITE = Color3.new(1, 1, 1)
local BLACK = Color3.new(0, 0, 0)

local sounds: { [string]: Sound } = {}
local hudScales: { UIScale } = {}
local hudScale = 1

-- Instance.new with properties and children; Parent is always set last.
function Widgets.create(className: string, props: { [string]: any }?, children: { Instance }?): any
	local instance = Instance.new(className)
	if instance:IsA("GuiObject") then
		instance.BorderSizePixel = 0
	end
	local parent = nil
	if props then
		for key, value in props do
			if key == "Parent" then
				parent = value
			else
				(instance :: any)[key] = value
			end
		end
	end
	if children then
		for _, child in children do
			child.Parent = instance
		end
	end
	if parent then
		instance.Parent = parent
	end
	return instance
end

local create = Widgets.create

function Widgets.tween(instance: Instance, seconds: number, goal: { [string]: any }, style: Enum.EasingStyle?, direction: Enum.EasingDirection?, delay: number?): Tween
	local info = TweenInfo.new(seconds, style or Enum.EasingStyle.Quad, direction or Enum.EasingDirection.Out, 0, false, delay or 0)
	local tween = TweenService:Create(instance, info, goal)
	tween:Play()
	return tween
end

-- Colours -------------------------------------------------------------------

function Widgets.shade(color: Color3, amount: number): Color3
	return color:Lerp(BLACK, amount)
end

function Widgets.tint(color: Color3, amount: number): Color3
	return color:Lerp(WHITE, amount)
end

function Widgets.sequence(colors: { Color3 }): ColorSequence
	if #colors == 1 then
		return ColorSequence.new(colors[1])
	end
	local keypoints = {}
	for index, color in colors do
		table.insert(keypoints, ColorSequenceKeypoint.new((index - 1) / (#colors - 1), color))
	end
	return ColorSequence.new(keypoints)
end

-- Decorators ----------------------------------------------------------------

function Widgets.corner(radius: number | UDim | nil): UICorner
	local value = if typeof(radius) == "UDim" then radius else UDim.new(0, (radius :: number?) or 12)
	return create("UICorner", { CornerRadius = value })
end

function Widgets.round(): UICorner
	return create("UICorner", { CornerRadius = UDim.new(0.5, 0) })
end

-- Outline around a frame.
function Widgets.stroke(thickness: number?, color: Color3?, transparency: number?): UIStroke
	return create("UIStroke", {
		Thickness = thickness or 3,
		Color = color or Theme.Outline,
		Transparency = transparency or 0,
		ApplyStrokeMode = Enum.ApplyStrokeMode.Border,
		LineJoinMode = Enum.LineJoinMode.Round,
	})
end

-- Outline around the letters of a text.
function Widgets.textStroke(thickness: number?, color: Color3?): UIStroke
	return create("UIStroke", {
		Thickness = thickness or 2.5,
		Color = color or Theme.Outline,
		ApplyStrokeMode = Enum.ApplyStrokeMode.Contextual,
		LineJoinMode = Enum.LineJoinMode.Round,
	})
end

-- Gradient; rotation 90 = top to bottom.
function Widgets.gradient(colors: { Color3 } | ColorSequence, rotation: number?): UIGradient
	local sequence = if typeof(colors) == "ColorSequence" then colors else Widgets.sequence(colors :: { Color3 })
	return create("UIGradient", { Color = sequence, Rotation = rotation or 90 })
end

-- Vertical shading that makes a flat colour look rounded.
function Widgets.shading(): UIGradient
	return Widgets.gradient({ WHITE, Color3.fromRGB(200, 200, 200) }, 90)
end

function Widgets.padding(top: number, right: number?, bottom: number?, left: number?): UIPadding
	return create("UIPadding", {
		PaddingTop = UDim.new(0, top),
		PaddingRight = UDim.new(0, right or top),
		PaddingBottom = UDim.new(0, bottom or top),
		PaddingLeft = UDim.new(0, left or right or top),
	})
end

function Widgets.list(direction: Enum.FillDirection?, padding: number?, horizontal: Enum.HorizontalAlignment?, vertical: Enum.VerticalAlignment?): UIListLayout
	return create("UIListLayout", {
		FillDirection = direction or Enum.FillDirection.Vertical,
		Padding = UDim.new(0, padding or 8),
		HorizontalAlignment = horizontal or Enum.HorizontalAlignment.Center,
		VerticalAlignment = vertical or Enum.VerticalAlignment.Top,
		SortOrder = Enum.SortOrder.LayoutOrder,
	})
end

-- Basic elements ------------------------------------------------------------

-- Uppercase that also handles French accents (the title font only has capitals
-- for them: "é" would look lowercase next to capital letters).
local ACCENTS = {
	["à"] = "À", ["â"] = "Â", ["ä"] = "Ä", ["ç"] = "Ç", ["é"] = "É", ["è"] = "È", ["ê"] = "Ê", ["ë"] = "Ë",
	["î"] = "Î", ["ï"] = "Ï", ["ô"] = "Ô", ["ö"] = "Ö", ["ù"] = "Ù", ["û"] = "Û", ["ü"] = "Ü", ["œ"] = "Œ",
}

function Widgets.upper(text: string): string
	local upper = string.upper(text)
	for lower, capital in ACCENTS do
		upper = string.gsub(upper, lower, capital)
	end
	return upper
end

function Widgets.frame(props: { [string]: any }, children: { Instance }?): Frame
	local merged = { BackgroundTransparency = 1 }
	for key, value in props do
		merged[key] = value
	end
	return create("Frame", merged, children)
end

-- Text label. Options: Text, Font ("Title" | "Body"), TextSize, Color, Stroke
-- (thickness or false), StrokeColor, XAlign, YAlign, Wrapped, Scaled, plus
-- any TextLabel property (Size, Position, AnchorPoint, Name, ZIndex...).
local TEXT_OPTIONS = {
	Font = true,
	Color = true,
	Stroke = true,
	StrokeColor = true,
	XAlign = true,
	YAlign = true,
	Wrapped = true,
	Scaled = true,
}

function Widgets.text(options: { [string]: any }): TextLabel
	local props: { [string]: any } = {
		Name = "Text",
		Size = UDim2.fromScale(1, 1),
		BackgroundTransparency = 1,
		FontFace = Font.fromEnum(if options.Font == "Title" then Theme.TitleFont else Theme.BodyFont),
		TextColor3 = options.Color or Theme.Text,
		TextSize = 24,
		TextXAlignment = options.XAlign or Enum.TextXAlignment.Center,
		TextYAlignment = options.YAlign or Enum.TextYAlignment.Center,
		TextWrapped = options.Wrapped == true,
		TextScaled = options.Scaled == true,
	}
	for key, value in options do
		if not TEXT_OPTIONS[key] then
			props[key] = value
		end
	end
	if options.Font == "Title" and type(props.Text) == "string" then
		props.Text = Widgets.upper(props.Text)
	end
	local label = create("TextLabel", props)
	if options.Scaled then
		create("UITextSizeConstraint", { MaxTextSize = options.TextSize or 24, MinTextSize = 8, Parent = label })
	end
	if options.Stroke ~= false then
		Widgets.textStroke(options.Stroke or 2.5, options.StrokeColor).Parent = label
	end
	return label
end

function Widgets.circle(props: { [string]: any }, children: { Instance }?): Frame
	local frame = create("Frame", props, children)
	Widgets.round().Parent = frame
	return frame
end

-- Dark rounded panel with an outline.
function Widgets.panel(props: { [string]: any }, children: { Instance }?): Frame
	local merged = { BackgroundColor3 = Theme.PanelLight }
	for key, value in props do
		if key ~= "Radius" then
			merged[key] = value
		end
	end
	local frame = create("Frame", merged, children)
	Widgets.corner(props.Radius or 14).Parent = frame
	Widgets.stroke(3).Parent = frame
	return frame
end

-- Chunky button ---------------------------------------------------------------

export type Button = {
	Instance: TextButton,
	Face: Frame,
	Base: Frame,
	Label: TextLabel,
	SubLabel: TextLabel?,
	SetText: (string) -> (),
	SetSubText: (string) -> (),
	SetColor: (Color3) -> (),
	SetEnabled: (boolean) -> (),
	IsEnabled: () -> boolean,
}

-- Options: Parent, Name, Size, Position, AnchorPoint, LayoutOrder, ZIndex, Color,
-- Text, TextSize, Font, SubText, SubTextSize, Radius, Depth, OnClick.
function Widgets.button(options: { [string]: any }): Button
	local depth = options.Depth or 5
	local radius = options.Radius or 12
	local color: Color3 = options.Color or Theme.Green
	local enabled = true

	local button = create("TextButton", {
		Name = options.Name or "Button",
		Size = options.Size or UDim2.fromOffset(160, 56),
		Position = options.Position or UDim2.new(),
		AnchorPoint = options.AnchorPoint or Vector2.zero,
		LayoutOrder = options.LayoutOrder or 0,
		ZIndex = options.ZIndex or 1,
		BackgroundTransparency = 1,
		AutoButtonColor = false,
		Text = "",
		Parent = options.Parent,
	})
	local scale = create("UIScale", { Parent = button })
	local base = create("Frame", {
		Name = "Base",
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = Widgets.shade(color, 0.45),
		Parent = button,
	}, { Widgets.corner(radius), Widgets.stroke(options.StrokeThickness or 3) })
	local face = create("Frame", {
		Name = "Face",
		Size = UDim2.new(1, 0, 1, -depth),
		BackgroundColor3 = color,
		Parent = base,
	}, { Widgets.corner(radius), Widgets.shading() })
	create("Frame", {
		Name = "Shine",
		AnchorPoint = Vector2.new(0.5, 0),
		Position = UDim2.new(0.5, 0, 0, 3),
		Size = UDim2.new(1, -10, 0.4, 0),
		BackgroundColor3 = WHITE,
		BackgroundTransparency = 0.72,
		Parent = face,
	}, { Widgets.corner(math.max(radius - 3, 2)) })

	local hasSub = options.SubText ~= nil
	local label = Widgets.text({
		Name = "Label",
		Text = options.Text or "",
		Font = options.Font or "Title",
		TextSize = options.TextSize or 24,
		Size = if hasSub then UDim2.new(1, -8, 0.56, 0) else UDim2.new(1, -8, 1, 0),
		Position = UDim2.fromOffset(4, if hasSub then 2 else 0),
		Parent = face,
	})
	local subLabel = nil
	if hasSub then
		subLabel = Widgets.text({
			Name = "SubLabel",
			Text = options.SubText,
			TextSize = options.SubTextSize or 18,
			Size = UDim2.new(1, -8, 0.4, 0),
			Position = UDim2.new(0, 4, 0.56, 0),
			Parent = face,
		})
	end

	local hovering, pressed = false, false
	local function refresh()
		local target = if pressed then 0.95 elseif hovering and enabled then 1.06 else 1
		Widgets.tween(scale, 0.12, { Scale = target })
		face.Position = UDim2.fromOffset(0, if pressed then depth - 2 else 0)
	end
	local function applyColor()
		local current = if enabled then color else Theme.Disabled
		face.BackgroundColor3 = current
		base.BackgroundColor3 = Widgets.shade(current, 0.45)
		label.TextTransparency = if enabled then 0 else 0.2
	end

	local function isPointer(input: InputObject): boolean
		return input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch
	end
	button.MouseEnter:Connect(function()
		hovering = true
		refresh()
	end)
	button.MouseLeave:Connect(function()
		hovering = false
		pressed = false
		refresh()
	end)
	button.SelectionGained:Connect(function()
		hovering = true
		refresh()
	end)
	button.SelectionLost:Connect(function()
		hovering = false
		refresh()
	end)
	button.InputBegan:Connect(function(input)
		if isPointer(input) then
			pressed = true
			refresh()
		end
	end)
	button.InputEnded:Connect(function(input)
		if isPointer(input) then
			pressed = false
			if input.UserInputType == Enum.UserInputType.Touch then
				hovering = false
			end
			refresh()
		end
	end)
	button.Activated:Connect(function()
		if not enabled then
			return
		end
		Widgets.playSound("Click")
		if options.OnClick then
			task.spawn(options.OnClick)
		end
	end)

	local object = {} :: Button
	object.Instance = button
	object.Face = face
	object.Base = base
	object.Label = label
	object.SubLabel = subLabel
	local titleFont = (options.Font or "Title") == "Title"
	function object.SetText(text: string)
		label.Text = if titleFont then Widgets.upper(text) else text
	end
	function object.SetSubText(text: string)
		if subLabel then
			subLabel.Text = text
		end
	end
	function object.SetColor(newColor: Color3)
		color = newColor
		applyColor()
	end
	function object.SetEnabled(value: boolean)
		enabled = value
		applyColor()
		refresh()
	end
	function object.IsEnabled(): boolean
		return enabled
	end
	return object
end

-- Red notification dot in the top-right corner of a button.
export type Badge = { Instance: Frame, Set: (string?) -> () }

function Widgets.badge(parent: GuiObject): Badge
	local dot = Widgets.circle({
		Name = "Badge",
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.new(1, -6, 0, 6),
		Size = UDim2.fromOffset(30, 30),
		BackgroundColor3 = Theme.Red,
		Visible = false,
		ZIndex = 5,
		Parent = parent,
	}, { Widgets.stroke(3), Widgets.shading() })
	local label = Widgets.text({ Text = "!", Font = "Title", TextSize = 20, ZIndex = 6, Position = UDim2.fromOffset(0, 1), Parent = dot })
	local scale = create("UIScale", { Parent = dot })
	local object = {} :: Badge
	object.Instance = dot
	function object.Set(text: string?)
		local show = text ~= nil and text ~= ""
		if show then
			label.Text = text :: string
		end
		if show and not dot.Visible then
			scale.Scale = 0.3
			Widgets.tween(scale, 0.3, { Scale = 1 }, Enum.EasingStyle.Back)
		end
		dot.Visible = show
	end
	return object
end

-- Progress bar with centred text.
export type ProgressBar = { Instance: Frame, Set: (number, string?) -> () }

function Widgets.progressBar(props: { [string]: any }): ProgressBar
	local colors = props.Colors or { Theme.Purple, Theme.Pink }
	local bar = create("Frame", {
		Name = props.Name or "ProgressBar",
		Size = props.Size,
		Position = props.Position or UDim2.new(),
		AnchorPoint = props.AnchorPoint or Vector2.zero,
		BackgroundColor3 = BLACK,
		BackgroundTransparency = 0.45,
		Parent = props.Parent,
	}, { Widgets.round(), Widgets.stroke(3) })
	local fill = create("Frame", {
		Name = "Fill",
		Size = UDim2.fromScale(0, 1),
		BackgroundColor3 = WHITE,
		Parent = bar,
	}, { Widgets.round(), Widgets.gradient(colors, 0) })
	local label = Widgets.text({ Text = "", Font = "Title", TextSize = props.TextSize or 20, ZIndex = 3, Position = UDim2.fromOffset(0, 1), Parent = bar })
	local object = {} :: ProgressBar
	object.Instance = bar
	function object.Set(ratio: number, text: string?)
		local clamped = math.clamp(ratio, 0, 1)
		fill.Visible = clamped > 0
		Widgets.tween(fill, 0.35, { Size = UDim2.fromScale(math.max(clamped, 0.06), 1) })
		if text then
			label.Text = text
		end
	end
	return object
end

-- Sounds ----------------------------------------------------------------------

function Widgets.playSound(name: string)
	local sound = sounds[name]
	if sound then
		SoundService:PlayLocalSound(sound)
	end
end

local function loadSounds()
	local folder = SoundService:FindFirstChild("BrainrotUISounds")
	if folder then
		folder:Destroy()
	end
	folder = create("Folder", { Name = "BrainrotUISounds", Parent = SoundService })
	for name, id in Config.Sounds.Ids do
		if id ~= "" then
			sounds[name] = create("Sound", { Name = name, SoundId = id, Volume = Config.Sounds.Volume, Parent = folder })
		end
	end
end

-- Screen scaling ----------------------------------------------------------------

-- The interface is designed at 1280 x 720; every HUD cluster gets a UIScale
-- that follows the real screen size (phones shrink it, big screens grow it).
local function computeHudScale(size: Vector2): number
	if size.X <= 0 or size.Y <= 0 then
		return 1
	end
	return math.clamp(math.min(size.X / 1280, size.Y / 720), 0.55, 1.35)
end

function Widgets.getHudScale(): number
	return hudScale
end

function Widgets.attachHudScale(guiObject: GuiObject): UIScale
	local scale = create("UIScale", { Name = "HudScale", Scale = hudScale, Parent = guiObject })
	table.insert(hudScales, scale)
	return scale
end

function Widgets.init(screenGui: ScreenGui)
	local function update()
		local size = screenGui.AbsoluteSize
		if size.X <= 0 then
			local camera = workspace.CurrentCamera
			size = if camera then camera.ViewportSize else Vector2.new(1280, 720)
		end
		hudScale = computeHudScale(size)
		for _, scale in hudScales do
			scale.Scale = hudScale
		end
	end
	screenGui:GetPropertyChangedSignal("AbsoluteSize"):Connect(update)
	update()
	loadSounds()
end

return Widgets
