-- BrainrotUI : range le modèle BrainrotUI.rbxmx inséré dans le Workspace.
-- Colle ce fichier dans la barre de commande (mode édition), puis Entrée.
local OVERWRITE_CONFIG = false -- true = remplace aussi ta UIConfig
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")
local SPS = game:GetService("StarterPlayer"):FindFirstChildOfClass("StarterPlayerScripts")
local pack = workspace:FindFirstChild("BrainrotUI_Install")
if not pack then
	warn("⚠️ Insère d'abord BrainrotUI.rbxmx : clic droit sur Workspace > Insérer depuis un fichier.")
	return
end
print("----- Installation de BrainrotUI -----")
local shared, server, client = pack.BrainrotUI, pack.BrainrotUIServer, pack.BrainrotUIClient
local old = RS:FindFirstChild("BrainrotUI")
if old then
	local config = old:FindFirstChild("UIConfig")
	if config and not OVERWRITE_CONFIG then
		shared.UIConfig:Destroy()
		config.Parent = shared
		print("✅ UIConfig conservée (tes réglages et tes IDs)")
	end
	old:Destroy()
end
shared.Parent = RS
for _, parent in { SSS, SPS } do
	for _, name in { "BrainrotUIServer", "BrainrotUIClient" } do
		local previous = parent:FindFirstChild(name)
		if previous then
			previous:Destroy()
		end
	end
end
server.Parent = SSS
server.Enabled = true
client.Parent = SPS
pack:Destroy()
print("✅ ReplicatedStorage.BrainrotUI, ServerScriptService.BrainrotUIServer, StarterPlayerScripts.BrainrotUIClient")
for _, service in { workspace, SSS, game:GetService("ServerStorage"), RS, game:GetService("StarterGui") } do
	for _, s in service:GetDescendants() do
		if s:IsA("Script") and not s:IsDescendantOf(server) and s.Enabled then
			local ok, source = pcall(function()
				return s.Source
			end)
			if ok and type(source) == "string" and string.find(source, "ProcessReceipt", 1, true) then
				warn("⚠️ Désactive ce script, il gère aussi les achats Robux : " .. s:GetFullName())
			end
		end
	end
end
local oldStats = SSS:FindFirstChild("leaderstats")
if oldStats and oldStats:IsA("Script") and oldStats.Enabled then
	warn("⚠️ Désactive ServerScriptService.leaderstats (ancien pack).")
end
local gui = game:GetService("StarterGui"):FindFirstChild("GUI")
if gui and gui:FindFirstChild("HUD") then
	warn("⚠️ Désactive StarterGui.GUI (ancienne interface) : Enabled = false.")
end
print("✅ BrainrotUI prête ! Enregistre la place, puis lance Play.")
