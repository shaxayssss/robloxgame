"""Builds the two installation files from src/:

  BrainrotUI.rbxmx         model to insert in Studio (all the scripts, ~150 KB)
  BrainrotUI_Install.lua   short command for the command bar: puts each piece in place

The Studio command bar does not accept a script this large (it only kept the last few
thousand characters), hence the model file + a short command.

    python BrainrotFighter/UI/build_installer.py

src/ mirrors the Roblox tree (Rojo naming):
  ReplicatedStorage/BrainrotUI/*.lua            -> ModuleScripts in ReplicatedStorage.BrainrotUI
  ServerScriptService/BrainrotUIServer/         -> Script (init.server.lua) + child ModuleScripts
  StarterPlayerScripts/BrainrotUIClient/        -> LocalScript (init.client.lua) + child ModuleScripts
"""
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
MODEL = os.path.join(HERE, "BrainrotUI.rbxmx")
COMMAND = os.path.join(HERE, "BrainrotUI_Install.lua")
PACK_NAME = "BrainrotUI_Install"
COMMAND_LIMIT = 4000  # characters; stay well under what the command bar keeps


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class Model:
    def __init__(self):
        self.lines = []
        self.next_ref = 0

    def open(self, cls: str, name: str, source: str = None, disabled: bool = False, depth: int = 1):
        pad = "\t" * depth
        self.lines.append(f'{pad}<Item class="{cls}" referent="RBX{self.next_ref:04d}">')
        self.next_ref += 1
        self.lines.append(f"{pad}\t<Properties>")
        self.lines.append(f'{pad}\t\t<string name="Name">{escape(name)}</string>')
        if source is not None:
            assert "]]>" not in source, "a source contains ]]>"
            self.lines.append(f'{pad}\t\t<ProtectedString name="Source"><![CDATA[{source}]]></ProtectedString>')
        if disabled:
            self.lines.append(f'{pad}\t\t<bool name="Disabled">true</bool>')
        self.lines.append(f"{pad}\t</Properties>")

    def close(self, depth: int = 1):
        self.lines.append("\t" * depth + "</Item>")


def add_folder_of_scripts(model: Model, folder: str, name: str, depth: int, disabled: bool = False):
    """A folder with an init.*.lua becomes that script, otherwise a Folder; files become ModuleScripts."""
    files = sorted(os.listdir(folder))
    init = [f for f in files if f.startswith("init.")]
    if init:
        cls = "Script" if ".server." in init[0] else "LocalScript" if ".client." in init[0] else "ModuleScript"
        model.open(cls, name, read(os.path.join(folder, init[0])), disabled and cls == "Script", depth)
    else:
        model.open("Folder", name, depth=depth)
    for file in files:
        if file.endswith(".lua") and not file.startswith("init."):
            model.open("ModuleScript", file[:-4], read(os.path.join(folder, file)), depth=depth + 1)
            model.close(depth + 1)
    model.close(depth)


def build_model() -> str:
    model = Model()
    model.lines.append('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" '
                       'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                       'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">')
    model.open("Folder", PACK_NAME)
    add_folder_of_scripts(model, os.path.join(SRC, "ReplicatedStorage", "BrainrotUI"), "BrainrotUI", 2)
    # the server script stays disabled while it sits in the Workspace; the command enables it
    add_folder_of_scripts(model, os.path.join(SRC, "ServerScriptService", "BrainrotUIServer"), "BrainrotUIServer", 2, disabled=True)
    add_folder_of_scripts(model, os.path.join(SRC, "StarterPlayerScripts", "BrainrotUIClient"), "BrainrotUIClient", 2)
    model.close()
    model.lines.append("</roblox>")
    return "\n".join(model.lines) + "\n"


COMMAND_SOURCE = r'''-- BrainrotUI : range le modèle BrainrotUI.rbxmx inséré dans le Workspace.
-- Colle ce fichier dans la barre de commande (mode édition), puis Entrée.
local OVERWRITE_CONFIG = false -- true = remplace aussi ta UIConfig
local RS = game:GetService("ReplicatedStorage")
local SSS = game:GetService("ServerScriptService")
local SPS = game:GetService("StarterPlayer"):FindFirstChildOfClass("StarterPlayerScripts")
local pack = workspace:FindFirstChild("__PACK__")
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
'''


def main():
    model = build_model()
    with open(MODEL, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(model)
    command = COMMAND_SOURCE.replace("__PACK__", PACK_NAME)
    assert len(command) < COMMAND_LIMIT, f"command too long for the command bar: {len(command)}"
    with open(COMMAND, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(command)
    print(f"{os.path.relpath(MODEL)}: {len(model) // 1024} KB")
    print(f"{os.path.relpath(COMMAND)}: {len(command)} characters (limit {COMMAND_LIMIT})")


if __name__ == "__main__":
    main()
