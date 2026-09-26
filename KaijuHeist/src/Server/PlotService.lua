-- Hands one of the 8 bases ("cases", MapData.plots) to each player who joins,
-- frees it when they leave, and shows the owner's name above the base.
-- Other services ask GetPlot(player) instead of guessing positions.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace = game:GetService("Workspace")

local MapData = require(ReplicatedStorage.Shared.MapData)

local PlotService = {}

local FREE_TEXT = "Base libre"

local ownerByPlot = {} -- [plotId] = Player
local plotByPlayer = {} -- [Player] = plot entry of MapData.plots
local labels = {} -- [plotId] = TextLabel

local function makeLabel(plot, parent)
	local anchor = Instance.new("Part")
	anchor.Name = "PlotLabel_" .. plot.id
	anchor.Anchored = true
	anchor.CanCollide = false
	anchor.CanQuery = false
	anchor.CanTouch = false
	anchor.Transparency = 1
	anchor.Size = Vector3.new(1, 1, 1)
	anchor.Position = plot.sign
	anchor.Parent = parent

	local billboard = Instance.new("BillboardGui")
	billboard.Size = UDim2.fromScale(28, 6) -- scale is in studs for a BillboardGui
	billboard.LightInfluence = 0
	billboard.MaxDistance = 300
	billboard.Parent = anchor

	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
	label.BackgroundTransparency = 1
	label.Font = Enum.Font.FredokaOne
	label.TextScaled = true
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.TextStrokeTransparency = 0
	label.Text = FREE_TEXT
	label.Parent = billboard
	return label
end

function PlotService.Assign(player)
	if plotByPlayer[player] then
		return plotByPlayer[player]
	end
	-- MapData.plots is ordered N1, S1, N2, S2...: the first bases are the closest to the lobby.
	for _, plot in ipairs(MapData.plots) do
		if not ownerByPlot[plot.id] then
			ownerByPlot[plot.id] = player
			plotByPlayer[player] = plot
			player:SetAttribute("PlotId", plot.id)
			if labels[plot.id] then
				labels[plot.id].Text = ("Base de %s"):format(player.DisplayName)
			end
			return plot
		end
	end
	warn(("PlotService: no free base for %s (%d bases)"):format(player.Name, #MapData.plots))
	return nil
end

function PlotService.Release(player)
	local plot = plotByPlayer[player]
	if not plot then
		return
	end
	plotByPlayer[player] = nil
	ownerByPlot[plot.id] = nil
	if labels[plot.id] then
		labels[plot.id].Text = FREE_TEXT
	end
end

function PlotService.GetPlot(player)
	return plotByPlayer[player]
end

function PlotService.GetOwner(plotId)
	return ownerByPlot[plotId]
end

function PlotService.Start()
	local folder = Instance.new("Folder")
	folder.Name = "PlotLabels"
	for _, plot in ipairs(MapData.plots) do
		labels[plot.id] = makeLabel(plot, folder)
	end
	folder.Parent = Workspace

	Players.PlayerAdded:Connect(PlotService.Assign)
	Players.PlayerRemoving:Connect(PlotService.Release)
	-- Players who joined before this ran (Studio play solo) still get a base.
	for _, player in ipairs(Players:GetPlayers()) do
		PlotService.Assign(player)
	end
end

return PlotService
