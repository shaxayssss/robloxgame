"""Packs src/ into BrainrotUI_Install.lua, a script to paste into the Roblox Studio command bar.

    python BrainrotFighter/UI/build_installer.py

src/ mirrors the Roblox tree (Rojo naming):
  ReplicatedStorage/BrainrotUI/*.lua            -> ModuleScripts in ReplicatedStorage.BrainrotUI
  ServerScriptService/BrainrotUIServer/         -> Script (init.server.lua) + child ModuleScripts
  StarterPlayerScripts/BrainrotUIClient/        -> LocalScript (init.client.lua) + child ModuleScripts
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
OUT = os.path.join(HERE, "BrainrotUI_Install.lua")


def long_string(text: str) -> str:
    level = 1
    while ("]" + "=" * level + "]") in text or ("[" + "=" * level + "[") in text:
        level += 1
    eq = "=" * level
    return f"[{eq}[\n{text}]{eq}]"


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def scripts_in(folder: str):
    """(name, class, source) for a folder: its init script first, then its modules."""
    files = sorted(os.listdir(folder))
    entries = []
    for name in files:
        if name.startswith("init."):
            cls = "Script" if ".server." in name else "LocalScript" if ".client." in name else "ModuleScript"
            entries.insert(0, ("", cls, read(os.path.join(folder, name))))
    for name in files:
        if name.endswith(".lua") and not name.startswith("init."):
            entries.append((name[:-4], "ModuleScript", read(os.path.join(folder, name))))
    return entries


def table(entries) -> str:
    rows = []
    for name, cls, source in entries:
        rows.append(f'\t{{ Name = "{name}", Class = "{cls}", Source = {long_string(source)} }},')
    return "{\n" + "\n".join(rows) + "\n}"


shared = scripts_in(os.path.join(SRC, "ReplicatedStorage", "BrainrotUI"))
server = scripts_in(os.path.join(SRC, "ServerScriptService", "BrainrotUIServer"))
client = scripts_in(os.path.join(SRC, "StarterPlayerScripts", "BrainrotUIClient"))

INSTALLER = r'''-- ============================================================================
-- BrainrotUI : installation dans Roblox Studio
-- 1. Mode édition (pas en Play).  2. Affichage > Barre de commande.
-- 3. Colle TOUT ce fichier dans la barre de commande, puis Entrée.
-- Relançable sans risque : les scripts sont remplacés, ta config est gardée.
--
-- Généré par build_installer.py depuis src/ : ne pas modifier à la main.
-- ============================================================================

-- true = remplace aussi UIConfig (tu perds tes IDs de produits et tes réglages)
local OVERWRITE_CONFIG = false

local SHARED = __SHARED__
local SERVER = __SERVER__
local CLIENT = __CLIENT__

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local StarterPlayer = game:GetService("StarterPlayer")
local StarterGui = game:GetService("StarterGui")
local ChangeHistoryService = game:GetService("ChangeHistoryService")

print("----- Installation de BrainrotUI -----")
local recording = nil
pcall(function()
	recording = ChangeHistoryService:TryBeginRecording("Install BrainrotUI")
end)

local function makeScript(entry, parent, fallbackName)
	local instance = Instance.new(entry.Class)
	instance.Name = if entry.Name ~= "" then entry.Name else fallbackName
	instance.Source = entry.Source
	instance.Parent = parent
	return instance
end

-- shared modules (config kept unless OVERWRITE_CONFIG)
local sharedFolder = ReplicatedStorage:FindFirstChild("BrainrotUI")
if not sharedFolder then
	sharedFolder = Instance.new("Folder")
	sharedFolder.Name = "BrainrotUI"
	sharedFolder.Parent = ReplicatedStorage
end
local keptConfig = false
for _, entry in SHARED do
	local existing = sharedFolder:FindFirstChild(entry.Name)
	if entry.Name == "UIConfig" and existing and not OVERWRITE_CONFIG then
		keptConfig = true
	else
		if existing then
			existing:Destroy()
		end
		makeScript(entry, sharedFolder, entry.Name)
	end
end
print(if keptConfig then "✅ UIConfig conservée (tes réglages et tes IDs)" else "✅ UIConfig installée dans ReplicatedStorage.BrainrotUI")

-- server
local oldServer = ServerScriptService:FindFirstChild("BrainrotUIServer")
if oldServer then
	oldServer:Destroy()
end
local serverScript = makeScript(SERVER[1], ServerScriptService, "BrainrotUIServer")
for index = 2, #SERVER do
	makeScript(SERVER[index], serverScript, "")
end
print("✅ Script serveur installé : ServerScriptService.BrainrotUIServer (" .. (#SERVER - 1) .. " modules)")

-- client
local playerScripts = StarterPlayer:FindFirstChild("StarterPlayerScripts")
local oldClient = playerScripts:FindFirstChild("BrainrotUIClient")
if oldClient then
	oldClient:Destroy()
end
local clientScript = makeScript(CLIENT[1], playerScripts, "BrainrotUIClient")
for index = 2, #CLIENT do
	makeScript(CLIENT[index], clientScript, "")
end
print("✅ Interface installée : StarterPlayerScripts.BrainrotUIClient (" .. (#CLIENT - 1) .. " modules)")

-- conflicts ------------------------------------------------------------------
local ours = { sharedFolder, serverScript, clientScript }
local function isOurs(instance)
	for _, root in ours do
		if instance == root or instance:IsDescendantOf(root) then
			return true
		end
	end
	return false
end
local receiptScripts = {}
local searched = {}
for _, serviceName in { "Workspace", "ServerScriptService", "ServerStorage", "ReplicatedStorage", "ReplicatedFirst", "StarterGui", "StarterPlayer", "StarterPack" } do
	local ok, service = pcall(game.GetService, game, serviceName)
	if ok and service then
		for _, instance in service:GetDescendants() do
			table.insert(searched, instance)
		end
	end
end
for _, instance in searched do
	if instance:IsA("LuaSourceContainer") and not isOurs(instance) then
		local readOk, source = pcall(function()
			return (instance :: any).Source
		end)
		if readOk and type(source) == "string" and string.find(source, "ProcessReceipt", 1, true) then
			table.insert(receiptScripts, instance:GetFullName())
		end
	end
end
if #receiptScripts > 0 then
	warn("⚠️ Ces scripts définissent aussi MarketplaceService.ProcessReceipt. Roblox n'en garde qu'un : "
		.. "désactive-les, sinon certains achats ne seront pas donnés :")
	for _, name in receiptScripts do
		warn("   - " .. name)
	end
end
local oldStats = ServerScriptService:FindFirstChild("leaderstats")
if oldStats and oldStats:IsA("Script") and oldStats.Enabled then
	warn("⚠️ ServerScriptService.leaderstats (ancien pack) crée d'autres statistiques et sauvegardes : désactive-le.")
end
local oldGui = StarterGui:FindFirstChild("GUI")
if oldGui and oldGui:FindFirstChild("HUD") and oldGui:FindFirstChild("Frames") then
	warn("⚠️ StarterGui.GUI (Essential UI Pack) est encore là : désactive-le (Enabled = false) pour ne pas avoir deux interfaces.")
end
if not workspace:FindFirstChildWhichIsA("SpawnLocation", true) then
	print("ℹ️ Pas de SpawnLocation : les objets de test apparaîtront autour du centre de la map.")
end

if recording then
	pcall(function()
		ChangeHistoryService:FinishRecording(recording, Enum.FinishRecordingOperation.Commit)
	end)
end
print("✅ BrainrotUI prête ! Enregistre la place, puis lance Play.")
print("ℹ️ Pour sauvegarder la progression en test : Paramètres du jeu > Sécurité > Autoriser l'accès de Studio aux services d'API.")
'''

output = (
    INSTALLER.replace("__SHARED__", table(shared))
    .replace("__SERVER__", table(server))
    .replace("__CLIENT__", table(client))
)
with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(output)
print(f"{os.path.relpath(OUT)}: {len(output) // 1024} KB, {len(shared)} shared + {len(server)} server + {len(client)} client scripts")
