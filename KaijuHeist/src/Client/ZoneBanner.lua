-- Shows the name of the area the local player walks into: the lobby or one of
-- the corridor zones (MapData.GetAreaAt), in the area's colour.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local MapData = require(ReplicatedStorage.Shared.MapData)

local ZoneBanner = {}

local CHECK_INTERVAL = 0.4 -- seconds between two position checks
local VISIBLE_SECONDS = 2.5
local FADE = TweenInfo.new(0.35)

function ZoneBanner.Start()
	local player = Players.LocalPlayer

	local gui = Instance.new("ScreenGui")
	gui.Name = "ZoneBanner"
	gui.ResetOnSpawn = false
	gui.Parent = player:WaitForChild("PlayerGui")

	local label = Instance.new("TextLabel")
	label.AnchorPoint = Vector2.new(0.5, 0)
	label.Position = UDim2.new(0.5, 0, 0, 24)
	label.Size = UDim2.new(0.6, 0, 0, 56)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.TextTransparency = 1
	label.TextStrokeTransparency = 1
	label.Parent = gui

	local currentId = nil
	local showToken = 0
	local elapsed = 0

	local function show(area)
		showToken += 1
		local token = showToken
		label.Text = area.label
		label.TextColor3 = area.color
		TweenService:Create(label, FADE, { TextTransparency = 0, TextStrokeTransparency = 0 }):Play()
		task.delay(VISIBLE_SECONDS, function()
			if token == showToken then
				TweenService:Create(label, FADE, { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
			end
		end)
	end

	RunService.Heartbeat:Connect(function(dt)
		elapsed += dt
		if elapsed < CHECK_INTERVAL then
			return
		end
		elapsed = 0

		local character = player.Character
		local root = character and character:FindFirstChild("HumanoidRootPart")
		if not root then
			return
		end
		local area = MapData.GetAreaAt(root.Position)
		local id = area and area.id or nil
		if id ~= currentId then
			currentId = id
			if area then
				show(area)
			end
		end
	end)
end

return ZoneBanner
