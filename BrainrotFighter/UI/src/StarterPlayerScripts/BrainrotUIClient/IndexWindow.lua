-- IndexWindow: the brainrot collection, one tab per rarity. Unfound entries are
-- hidden behind "?". A complete series gives a gem reward (server checked).

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local shared = ReplicatedStorage:WaitForChild("BrainrotUI")
local Config = require(shared:WaitForChild("UIConfig"))
local Rules = require(shared:WaitForChild("Rules"))
local Format = require(shared:WaitForChild("Format"))
local Widgets = require(script.Parent:WaitForChild("Widgets"))
local State = require(script.Parent:WaitForChild("State"))
local Windows = require(script.Parent:WaitForChild("Windows"))
local Notify = require(script.Parent:WaitForChild("Notify"))
local Effects = require(script.Parent:WaitForChild("Effects"))

local Theme = Widgets.Theme
local Text = Config.Text
local create = Widgets.create

local IndexWindow = {}

local WIDTH, HEIGHT = 700, 490

type Card = {
	Frame: Frame,
	Icon: TextLabel,
	Name: TextLabel,
	Count: Frame,
	CountLabel: TextLabel,
	New: Frame,
}

local cards: { [string]: Card } = {}
local tabs: { [string]: Widgets.Button & { Badge: Widgets.Badge } } = {}
local unseen: { [string]: boolean } = {}
local selected = Config.Rarities[1].Key
local changedCallbacks: { () -> () } = {}

local function owned(itemId: string): number
	return State.number("Idx_" .. itemId)
end

local function foundCount(rarityKey: string): (number, number)
	local found, total = 0, 0
	for _, item in Rules.ItemsByRarity[rarityKey] do
		total += 1
		if owned(item.Id) > 0 then
			found += 1
		end
	end
	return found, total
end

local function claimable(rarityKey: string): boolean
	local found, total = foundCount(rarityKey)
	return total > 0 and found == total and State.get("Claim_" .. rarityKey) ~= true
end

-- True when a series can be claimed or new entries were found (HUD badge).
function IndexWindow.hasNews(): boolean
	if next(unseen) ~= nil then
		return true
	end
	for _, rarity in Config.Rarities do
		if claimable(rarity.Key) then
			return true
		end
	end
	return false
end

function IndexWindow.onChanged(callback: () -> ())
	table.insert(changedCallbacks, callback)
end

local function notifyChanged()
	for _, callback in changedCallbacks do
		callback()
	end
end

-- An entry found during this session: highlighted until the Index is opened.
function IndexWindow.markNew(itemId: string)
	unseen[itemId] = true
	notifyChanged()
end

local function makeCard(parent: Instance, item: { [string]: any }, order: number): Card
	local rarity = Rules.RarityByKey[item.Rarity]
	local frame = create("Frame", {
		Name = item.Id,
		BackgroundColor3 = Widgets.shade(rarity.Color, 0.55),
		LayoutOrder = order,
		ZIndex = 33,
		Parent = parent,
	}, { Widgets.corner(14), Widgets.stroke(3) })
	create("Frame", {
		Name = "Strip",
		Size = UDim2.new(1, 0, 0, 8),
		BackgroundColor3 = rarity.Color,
		ZIndex = 34,
		Parent = frame,
	}, { Widgets.corner(14) })
	local icon = Widgets.text({ Name = "Icon", Text = item.Icon, TextSize = 72, Stroke = false, Position = UDim2.fromOffset(0, 18), Size = UDim2.new(1, 0, 0, 90), ZIndex = 34, Parent = frame })
	local name = Widgets.text({
		Name = "Name",
		Text = item.Name,
		TextSize = 17,
		Scaled = true,
		Wrapped = true,
		Stroke = 2,
		Position = UDim2.fromOffset(8, 114),
		Size = UDim2.new(1, -16, 0, 58),
		ZIndex = 34,
		Parent = frame,
	})
	local count = create("Frame", {
		Name = "Count",
		AnchorPoint = Vector2.new(1, 0),
		Position = UDim2.new(1, -6, 0, 12),
		Size = UDim2.fromOffset(44, 24),
		BackgroundColor3 = Color3.new(0, 0, 0),
		BackgroundTransparency = 0.45,
		ZIndex = 35,
		Parent = frame,
	}, { Widgets.round() })
	local countLabel = Widgets.text({ Text = "x1", Font = "Title", TextSize = 16, Stroke = 2, ZIndex = 36, Position = UDim2.fromOffset(0, 1), Parent = count })
	local new = create("Frame", {
		Name = "New",
		Position = UDim2.fromOffset(-6, 8),
		Size = UDim2.fromOffset(78, 22),
		BackgroundColor3 = Theme.Red,
		Rotation = -10,
		Visible = false,
		ZIndex = 37,
		Parent = frame,
	}, { Widgets.round(), Widgets.stroke(2) })
	Widgets.text({ Text = Text.IndexNew, Font = "Title", TextSize = 14, Stroke = 2, ZIndex = 38, Position = UDim2.fromOffset(0, 1), Parent = new })
	return { Frame = frame, Icon = icon, Name = name, Count = count, CountLabel = countLabel, New = new }
end

local function refreshCard(item: { [string]: any })
	local card = cards[item.Id]
	local count = owned(item.Id)
	local rarity = Rules.RarityByKey[item.Rarity]
	if count > 0 then
		card.Frame.BackgroundColor3 = Widgets.shade(rarity.Color, 0.55)
		card.Icon.Text = item.Icon
		card.Icon.FontFace = Font.fromEnum(Theme.BodyFont)
		card.Icon.TextColor3 = Theme.Text
		card.Name.Text = item.Name
		card.Count.Visible = true
		card.CountLabel.Text = "x" .. Format.short(count)
	else
		card.Frame.BackgroundColor3 = Theme.Panel
		card.Icon.Text = "?"
		card.Icon.FontFace = Font.fromEnum(Theme.TitleFont)
		card.Icon.TextColor3 = Theme.Disabled
		card.Name.Text = Text.IndexLocked
		card.Count.Visible = false
	end
	card.New.Visible = unseen[item.Id] == true
end

function IndexWindow.build(request: (string, any?) -> { [string]: any })
	local window = Windows.create("Index", { Title = Text.IndexTitle, Width = WIDTH, Height = HEIGHT, Colors = Theme.Windows.Index })
	local body = window.Body

	-- rarity tabs
	local tabRow = Widgets.frame({
		Name = "Tabs",
		Position = UDim2.fromOffset(0, 14),
		Size = UDim2.new(1, 0, 0, 46),
		ZIndex = 33,
		Parent = body,
	}, { Widgets.list(Enum.FillDirection.Horizontal, 10) })

	-- header: progress of the selected series + claim button
	local header = Widgets.frame({ Name = "Header", Position = UDim2.fromOffset(0, 70), Size = UDim2.new(1, 0, 0, 46), ZIndex = 33, Parent = body })
	local seriesLabel = Widgets.text({ Name = "Series", Text = "", Font = "Title", TextSize = 26, Stroke = 3, XAlign = Enum.TextXAlignment.Left, Size = UDim2.new(0, 170, 1, 0), ZIndex = 33, Parent = header })
	local bar = Widgets.progressBar({
		Name = "Progress",
		Parent = header,
		Position = UDim2.new(0, 176, 0.5, -15),
		Size = UDim2.fromOffset(210, 30),
		TextSize = 18,
		Colors = { Theme.Cyan, Theme.Blue },
	})
	bar.Instance.ZIndex = 33
	local claimButton
	claimButton = Widgets.button({
		Name = "Claim",
		Parent = header,
		AnchorPoint = Vector2.new(1, 0.5),
		Position = UDim2.new(1, -4, 0.5, 0),
		Size = UDim2.fromOffset(250, 46),
		Color = Theme.Green,
		Text = "",
		TextSize = 20,
		Depth = 4,
		ZIndex = 34,
		OnClick = function()
			local rarityKey = selected
			local result = request("ClaimIndex", rarityKey)
			if result.ok then
				Effects.rewardPopup("💎", "+" .. Format.short(result.gems or 0), result.message, Theme.Cyan)
			else
				Notify.show(result.message or Text.GenericError, "error")
			end
		end,
	})

	-- grid of entries
	local grid = create("ScrollingFrame", {
		Name = "Grid",
		Position = UDim2.fromOffset(0, 126),
		Size = UDim2.new(1, 0, 1, -158),
		BackgroundTransparency = 1,
		ScrollBarThickness = 6,
		ScrollBarImageColor3 = Theme.Muted,
		ScrollingDirection = Enum.ScrollingDirection.Y,
		CanvasSize = UDim2.new(),
		AutomaticCanvasSize = Enum.AutomaticSize.Y,
		ZIndex = 33,
		Parent = body,
	}, {
		create("UIGridLayout", {
			CellSize = UDim2.fromOffset(172, 186),
			CellPadding = UDim2.fromOffset(14, 14),
			HorizontalAlignment = Enum.HorizontalAlignment.Center,
			SortOrder = Enum.SortOrder.LayoutOrder,
		}),
		Widgets.padding(6, 6, 6, 6),
	})
	local collection = Widgets.text({
		Name = "Collection",
		Text = "",
		TextSize = 18,
		Color = Theme.Muted,
		Stroke = 2,
		XAlign = Enum.TextXAlignment.Right,
		AnchorPoint = Vector2.new(1, 1),
		Position = UDim2.new(1, -4, 1, -4),
		Size = UDim2.fromOffset(260, 24),
		ZIndex = 33,
		Parent = body,
	})

	for order, item in Config.Index do
		cards[item.Id] = makeCard(grid, item, order)
	end

	local function refresh()
		local total, found = 0, 0
		for _, item in Config.Index do
			refreshCard(item)
			cards[item.Id].Frame.Visible = item.Rarity == selected
			total += 1
			if owned(item.Id) > 0 then
				found += 1
			end
		end
		collection.Text = Text.IndexCollection:format(found, total)
		for _, rarity in Config.Rarities do
			local tab = tabs[rarity.Key]
			tab.Badge.Set(if claimable(rarity.Key) then "!" else nil)
			tab.Instance.Size = if rarity.Key == selected then UDim2.fromOffset(150, 46) else UDim2.fromOffset(136, 42)
		end
		local rarity = Rules.RarityByKey[selected]
		local seriesFound, seriesTotal = foundCount(selected)
		seriesLabel.Text = Widgets.upper(rarity.Label)
		seriesLabel.TextColor3 = rarity.Color
		bar.Set(if seriesTotal > 0 then seriesFound / seriesTotal else 0, ("%d / %d"):format(seriesFound, seriesTotal))
		if State.get("Claim_" .. selected) == true then
			claimButton.SetText(Text.IndexClaimed)
			claimButton.SetEnabled(false)
		elseif seriesFound == seriesTotal and seriesTotal > 0 then
			claimButton.SetText(Text.IndexClaim:format("+" .. Format.short(rarity.IndexReward)))
			claimButton.SetEnabled(true)
		else
			claimButton.SetText(Text.IndexIncomplete)
			claimButton.SetEnabled(false)
		end
	end

	for order, rarity in Config.Rarities do
		local tab
		tab = Widgets.button({
			Name = rarity.Key,
			Parent = tabRow,
			LayoutOrder = order,
			Size = UDim2.fromOffset(136, 42),
			Color = rarity.Color,
			Text = rarity.Label,
			TextSize = 20,
			Depth = 4,
			ZIndex = 34,
			OnClick = function()
				selected = rarity.Key
				grid.CanvasPosition = Vector2.zero
				refresh()
			end,
		})
		tab.Badge = Widgets.badge(tab.Instance)
		tabs[rarity.Key] = tab
	end
	window.DefaultSelection = tabs[selected].Instance

	-- opening the Index "sees" the new entries of the tab once it closes
	table.insert(window.OnClose, function()
		table.clear(unseen)
		refresh()
		notifyChanged()
	end)
	table.insert(window.OnOpen, refresh)

	State.onAnyChange(function(key)
		if string.sub(key, 1, 4) == "Idx_" or string.sub(key, 1, 6) == "Claim_" then
			refresh()
			notifyChanged()
		end
	end)
	IndexWindow.onChanged(function()
		if Windows.isOpen("Index") then
			refresh()
		end
	end)
	refresh()
end

return IndexWindow
