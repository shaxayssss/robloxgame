-- Minimal functional HUD built entirely in code (no Studio GUI design yet).
-- Replace with hand-built GuiObjects in Studio once the look is nailed down;
-- keep reading state from the same remotes so the logic doesn't need to change.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)
local remotes = Remotes.Get()

local player = Players.LocalPlayer

local state = {
	ichor = 0,
	capsules = 0,
	baseLevel = 1,
	guardLevel = 0,
}

-- === Build UI ===
local screenGui = Instance.new("ScreenGui")
screenGui.Name = "KaijuHeistHud"
screenGui.ResetOnSpawn = false
screenGui.Parent = player:WaitForChild("PlayerGui")

local function makeButton(text, position, parent)
	local button = Instance.new("TextButton")
	button.Size = UDim2.new(0, 180, 0, 40)
	button.Position = position
	button.Text = text
	button.Font = Enum.Font.GothamBold
	button.TextSize = 16
	button.BackgroundColor3 = Color3.fromRGB(45, 45, 60)
	button.TextColor3 = Color3.fromRGB(255, 255, 255)
	button.Parent = parent
	return button
end

local statsFrame = Instance.new("Frame")
statsFrame.Size = UDim2.new(0, 220, 0, 90)
statsFrame.Position = UDim2.new(0, 20, 0, 20)
statsFrame.BackgroundColor3 = Color3.fromRGB(20, 20, 30)
statsFrame.BackgroundTransparency = 0.2
statsFrame.Parent = screenGui

local ichorLabel = Instance.new("TextLabel")
ichorLabel.Size = UDim2.new(1, -10, 0, 28)
ichorLabel.Position = UDim2.new(0, 5, 0, 5)
ichorLabel.BackgroundTransparency = 1
ichorLabel.Font = Enum.Font.GothamBold
ichorLabel.TextSize = 18
ichorLabel.TextColor3 = Color3.fromRGB(255, 215, 0)
ichorLabel.TextXAlignment = Enum.TextXAlignment.Left
ichorLabel.Text = "Ichor: 0"
ichorLabel.Parent = statsFrame

local capsuleLabel = ichorLabel:Clone()
capsuleLabel.Position = UDim2.new(0, 5, 0, 33)
capsuleLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
capsuleLabel.Text = "Capsules: 0"
capsuleLabel.Parent = statsFrame

local levelsLabel = ichorLabel:Clone()
levelsLabel.Position = UDim2.new(0, 5, 0, 61)
levelsLabel.TextSize = 14
levelsLabel.TextColor3 = Color3.fromRGB(180, 180, 200)
levelsLabel.Text = "Base 1  |  Guard 0"
levelsLabel.Parent = statsFrame

local actionsFrame = Instance.new("Frame")
actionsFrame.Size = UDim2.new(0, 200, 0, 220)
actionsFrame.Position = UDim2.new(0, 20, 0, 130)
actionsFrame.BackgroundTransparency = 1
actionsFrame.Parent = screenGui

local hatchButton = makeButton("Hatch Capsule", UDim2.new(0, 0, 0, 0), actionsFrame)
local upgradeBaseButton = makeButton("Upgrade Base", UDim2.new(0, 0, 0, 50), actionsFrame)
local upgradeGuardButton = makeButton("Upgrade Guard", UDim2.new(0, 0, 0, 100), actionsFrame)
local stealButton = makeButton("Steal Targets", UDim2.new(0, 0, 0, 150), actionsFrame)

local feedbackLabel = Instance.new("TextLabel")
feedbackLabel.Size = UDim2.new(0, 400, 0, 30)
feedbackLabel.Position = UDim2.new(0, 20, 0, 360)
feedbackLabel.BackgroundTransparency = 1
feedbackLabel.Font = Enum.Font.Gotham
feedbackLabel.TextSize = 16
feedbackLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
feedbackLabel.TextXAlignment = Enum.TextXAlignment.Left
feedbackLabel.Text = ""
feedbackLabel.Parent = screenGui

local function setFeedback(text)
	feedbackLabel.Text = text
	task.delay(4, function()
		if feedbackLabel.Text == text then
			feedbackLabel.Text = ""
		end
	end)
end

local function refreshStatsUi()
	ichorLabel.Text = ("Ichor: %d"):format(math.floor(state.ichor))
	capsuleLabel.Text = ("Capsules: %d"):format(state.capsules)
	levelsLabel.Text = ("Base %d  |  Guard %d"):format(state.baseLevel, state.guardLevel)
end

-- Steal target list panel
local stealFrame = Instance.new("Frame")
stealFrame.Size = UDim2.new(0, 260, 0, 260)
stealFrame.Position = UDim2.new(0, 240, 0, 130)
stealFrame.BackgroundColor3 = Color3.fromRGB(20, 20, 30)
stealFrame.BackgroundTransparency = 0.2
stealFrame.Visible = false
stealFrame.Parent = screenGui

local stealLayout = Instance.new("UIListLayout")
stealLayout.Padding = UDim.new(0, 4)
stealLayout.Parent = stealFrame

local function clearStealList()
	for _, child in ipairs(stealFrame:GetChildren()) do
		if child:IsA("TextButton") then
			child:Destroy()
		end
	end
end

local function populateStealList()
	clearStealList()
	local targets = remotes.GetNearbyTargets:InvokeServer()
	for _, target in ipairs(targets) do
		local entryButton = Instance.new("TextButton")
		entryButton.Size = UDim2.new(1, -10, 0, 32)
		entryButton.BackgroundColor3 = Color3.fromRGB(45, 45, 60)
		entryButton.TextColor3 = Color3.fromRGB(255, 255, 255)
		entryButton.Font = Enum.Font.Gotham
		entryButton.TextSize = 14
		entryButton.Text = ("%s  [%s]"):format(target.name, target.tier)
		entryButton.Parent = stealFrame

		entryButton.MouseButton1Click:Connect(function()
			local result = remotes.RequestSteal:InvokeServer(target.userId)
			if not result.ok then
				setFeedback(result.reason or "Steal failed.")
			end
		end)
	end
end

-- === Wire buttons ===
hatchButton.MouseButton1Click:Connect(function()
	local result = remotes.RequestHatch:InvokeServer()
	if result.ok then
		setFeedback(("Hatched a %s (%s)!"):format(result.kaijuName, result.rarity))
		state.capsules = result.remainingCapsules
		refreshStatsUi()
	else
		setFeedback(result.reason)
	end
end)

upgradeBaseButton.MouseButton1Click:Connect(function()
	local result = remotes.RequestUpgrade:InvokeServer("Base")
	if result.ok then
		state.baseLevel = result.newLevel
		state.ichor = result.ichor
		refreshStatsUi()
		setFeedback(("Base upgraded to level %d!"):format(result.newLevel))
	else
		setFeedback(result.reason)
	end
end)

upgradeGuardButton.MouseButton1Click:Connect(function()
	local result = remotes.RequestUpgrade:InvokeServer("Guard")
	if result.ok then
		state.guardLevel = result.newLevel
		state.ichor = result.ichor
		refreshStatsUi()
		setFeedback(("Guard upgraded to level %d!"):format(result.newLevel))
	else
		setFeedback(result.reason)
	end
end)

stealButton.MouseButton1Click:Connect(function()
	stealFrame.Visible = not stealFrame.Visible
	if stealFrame.Visible then
		populateStealList()
	end
end)

-- === Wire remote events ===
remotes.ProfileReady.OnClientEvent:Connect(function(payload)
	state.ichor = payload.ichor
	state.capsules = payload.capsules
	state.baseLevel = payload.baseLevel
	state.guardLevel = payload.guardLevel
	refreshStatsUi()
end)

remotes.CapsuleCollected.OnClientEvent:Connect(function(payload)
	state.capsules = payload.capsules
	refreshStatsUi()
	setFeedback("Capsule collected!")
end)

remotes.IncomeUpdated.OnClientEvent:Connect(function(payload)
	state.ichor = payload.ichor
	refreshStatsUi()
end)

remotes.StealResult.OnClientEvent:Connect(function(payload)
	if payload.wasVictim then
		if payload.success then
			state.ichor = math.max(0, state.ichor - payload.amount)
			refreshStatsUi()
			setFeedback(("%s stole %d Ichor from you!"):format(payload.attackerName, math.floor(payload.amount)))
		else
			setFeedback(("%s tried to steal from you and failed!"):format(payload.attackerName))
		end
	else
		if payload.success then
			state.ichor += payload.amount
			refreshStatsUi()
			setFeedback(("Stole %d Ichor from %s!"):format(math.floor(payload.amount), payload.targetName))
		else
			setFeedback(("Failed to steal from %s."):format(payload.targetName))
		end
	end
end)

refreshStatsUi()
