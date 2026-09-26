-- Boot script: wires up remotes, player lifecycle, and starts every server service.
-- This is the only script that should live directly under ServerScriptService.Server
-- with a .server.lua extension; everything else is a plain module required from here.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local MapService = require(script.Parent.MapService)
local PlotService = require(script.Parent.PlotService)
local PlayerDataService = require(script.Parent.PlayerDataService)
local CapsuleService = require(script.Parent.CapsuleService)
local HatchService = require(script.Parent.HatchService)
local IncomeService = require(script.Parent.IncomeService)
local StealService = require(script.Parent.StealService)
local BaseService = require(script.Parent.BaseService)

local remotes = Remotes.EnsureCreated()
local remotesProxy = Remotes.Get()

-- The map comes first: colliders, spawns and portals must exist before anyone spawns.
MapService.Start(PlotService)
PlotService.Start()
CapsuleService.Start(remotesProxy)
HatchService.Start(remotesProxy)
IncomeService.Start(remotesProxy)
StealService.Start(remotesProxy)
BaseService.Start(remotesProxy)
PlayerDataService.StartAutosave()

Players.PlayerAdded:Connect(function(player)
	local profile = PlayerDataService.Load(player)
	remotesProxy.ProfileReady:FireClient(player, {
		ichor = profile.Ichor,
		capsules = profile.Capsules,
		kaijus = profile.Kaijus,
		baseLevel = profile.BaseLevel,
		guardLevel = profile.GuardLevel,
	})
end)

Players.PlayerRemoving:Connect(function(player)
	PlayerDataService.Save(player)
	PlayerDataService.Release(player)
end)

game:BindToClose(function()
	for _, player in ipairs(Players:GetPlayers()) do
		PlayerDataService.Save(player)
	end
end)
