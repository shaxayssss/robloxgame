-- Runs the generated installer twice in the mock: everything lands in the right
-- place, nothing is duplicated, and an edited UIConfig is kept.

local sp = game:GetService("StarterPlayer")
local sps = Instance.new("StarterPlayerScripts")
sps.Name = "StarterPlayerScripts"
sps.Parent = sp
local fn = assert(loadstring(INSTALLER, "=installer"))
fn()
local rs = game:GetService("ReplicatedStorage")
local shared = rs:FindFirstChild("BrainrotUI")
assert(shared and shared:FindFirstChild("UIConfig") and shared:FindFirstChild("Rules") and shared:FindFirstChild("Format"), "shared modules")
local server = game:GetService("ServerScriptService"):FindFirstChild("BrainrotUIServer")
assert(server and server.ClassName == "Script" and #server:GetChildren() == 4, "server")
local client = sps:FindFirstChild("BrainrotUIClient")
assert(client and client.ClassName == "LocalScript" and #client:GetChildren() == 13, "client " .. #client:GetChildren())
-- user edits the config, reinstall keeps it
shared.UIConfig.Source = "-- edited"
fn()
assert(shared.UIConfig.Source == "-- edited", "config kept")
assert(#game:GetService("ServerScriptService"):GetChildren() == 1, "no duplicate server")
assert(#sps:GetChildren() == 1, "no duplicate client")
print("INSTALLER OK")
