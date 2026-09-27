-- Installation test: the BrainrotUI.rbxmx content is inserted in the Workspace, then
-- the short command puts every piece in place. Done twice: nothing is duplicated,
-- the server script ends enabled, and an edited UIConfig is kept.

local sps = Instance.new("StarterPlayerScripts")
sps.Name = "StarterPlayerScripts"
sps.Parent = game:GetService("StarterPlayer")
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")

local function insertModel()
	local pack = Instance.new("Folder")
	pack.Name = "BrainrotUI_Install"
	mountTree(pack, TREE.shared, "pack")
	local server = mountTree(pack, TREE.server, "pack")
	server.Enabled = false
	mountTree(pack, TREE.client, "pack")
	pack.Parent = workspace
end

local command = assert(loadstring(COMMAND, "=command"))
insertModel()
command()
assert(workspace:FindFirstChild("BrainrotUI_Install") == nil, "pack removed")
local shared = RS:FindFirstChild("BrainrotUI")
assert(shared and shared:FindFirstChild("UIConfig") and shared:FindFirstChild("Rules") and shared:FindFirstChild("Format"), "shared modules")
local server = SSS:FindFirstChild("BrainrotUIServer")
assert(server and server.ClassName == "Script" and server.Enabled == true and #server:GetChildren() == 4, "server")
local client = sps:FindFirstChild("BrainrotUIClient")
assert(client and client.ClassName == "LocalScript" and #client:GetChildren() == 13, "client")

-- the user edits the config, then installs again
local edited = shared.UIConfig
edited:SetAttribute("Edited", true)
insertModel()
command()
shared = RS:FindFirstChild("BrainrotUI")
assert(shared.UIConfig:GetAttribute("Edited") == true, "config kept")
assert(#shared:GetChildren() == 3, "no duplicate shared module")
assert(#SSS:GetChildren() == 1 and SSS.BrainrotUIServer.Enabled, "one enabled server script")
assert(#sps:GetChildren() == 1, "no duplicate client")

-- without the model, the command explains what to do and changes nothing
command()
assert(#SSS:GetChildren() == 1, "nothing changed without the model")
print("INSTALLER OK")
