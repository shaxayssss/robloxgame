-- BrainrotUI configuration: every number, price, reward, text and colour of the interface.
-- Shared by the server (which enforces it) and the client (which only displays it).
--
-- Product and game pass IDs are 0 until you create them on the Creator Dashboard.
-- A product with Id = 0 stays visible but tells the player it is not on sale yet.

local UIConfig = {}

-- Saving. Changing StoreName starts every player from scratch.
UIConfig.Data = {
	StoreName = "BrainrotUI_v1",
	AutosaveInterval = 60, -- seconds
}

-- What a brand new player starts with.
UIConfig.StartingData = {
	Coins = 0,
	Gems = 0,
	Power = 0,
	Rebirths = 0,
	Spins = 1,
}

-- HUD counters, top to bottom. Colors = text gradient, Stroke = text outline.
UIConfig.Currencies = {
	{
		Key = "Coins",
		Label = "Pièces",
		Icon = "💰",
		Colors = { Color3.fromRGB(160, 255, 80), Color3.fromRGB(255, 232, 60) },
		Stroke = Color3.fromRGB(30, 72, 0),
		ShopShortcut = true,
	},
	{
		Key = "Gems",
		Label = "Gemmes",
		Icon = "💎",
		Colors = { Color3.fromRGB(130, 240, 255), Color3.fromRGB(90, 150, 255) },
		Stroke = Color3.fromRGB(10, 38, 92),
	},
	{
		Key = "Power",
		Label = "Puissance",
		Icon = "💪",
		Colors = { Color3.fromRGB(255, 225, 90), Color3.fromRGB(255, 125, 40) },
		Stroke = Color3.fromRGB(84, 36, 0),
	},
}

-- Columns of the Roblox player list.
UIConfig.Leaderstats = {
	{ Key = "Power", Name = "Puissance" },
	{ Key = "Rebirths", Name = "Renaissances" },
}

-- Rebirth: requirement for rebirth n (starting at 0) = BasePower * Growth ^ n.
UIConfig.Rebirth = {
	BasePower = 100,
	Growth = 3,
	MultiplierPerRebirth = 0.5, -- +50 % power gain per rebirth
	GemsPerRebirth = 15, -- rebirth number n gives GemsPerRebirth * n gems
	ResetCoins = true, -- coins also go back to zero
	SkipProduct = "RebirthSkip", -- key in UIConfig.Products
}

-- Temporary multipliers. Stat = what they multiply.
UIConfig.Boosts = {
	Power = { Label = "x2 Puissance", Icon = "⚡", Stat = "Power", Multiplier = 2 },
	Coins = { Label = "x2 Pièces", Icon = "🍀", Stat = "Coins", Multiplier = 2 },
}

-- Rarities of the Index. Weight = chance of a power orb of that rarity.
-- OrbPower = power given by an orb, IndexReward = gems for completing the series.
UIConfig.Rarities = {
	{ Key = "Common", Label = "Commun", Color = Color3.fromRGB(170, 180, 196), Weight = 62, OrbPower = 1, IndexReward = 25 },
	{ Key = "Rare", Label = "Rare", Color = Color3.fromRGB(70, 165, 255), Weight = 25, OrbPower = 3, IndexReward = 60 },
	{ Key = "Epic", Label = "Épique", Color = Color3.fromRGB(190, 100, 255), Weight = 10, OrbPower = 8, IndexReward = 150 },
	{ Key = "Legendary", Label = "Légendaire", Color = Color3.fromRGB(255, 196, 40), Weight = 3, OrbPower = 25, IndexReward = 400 },
}

-- Index entries. Every power orb reveals one brainrot of its rarity.
-- Icon is an emoji; Image (rbxassetid://...) replaces it when set.
UIConfig.Index = {
	{ Id = "Pastarello", Name = "Pastarello Zigzag", Rarity = "Common", Icon = "🍝" },
	{ Id = "Pagnotto", Name = "Pagnotto Saltellino", Rarity = "Common", Icon = "🍞" },
	{ Id = "Bananello", Name = "Bananello Boing", Rarity = "Common", Icon = "🍌" },
	{ Id = "Pizzarotto", Name = "Pizzarotto Turbo", Rarity = "Rare", Icon = "🍕" },
	{ Id = "Formaggino", Name = "Formaggino Razzo", Rarity = "Rare", Icon = "🧀" },
	{ Id = "Cornetto", Name = "Cornetto Cannone", Rarity = "Rare", Icon = "🥐" },
	{ Id = "Espressino", Name = "Espressino Tornado", Rarity = "Epic", Icon = "☕" },
	{ Id = "Melonzio", Name = "Melonzio Ninja", Rarity = "Epic", Icon = "🍉" },
	{ Id = "Gelatone", Name = "Gelatone Cosmico", Rarity = "Epic", Icon = "🍦" },
	{ Id = "Squalone", Name = "Squalone Spaghettone", Rarity = "Legendary", Icon = "🦈" },
	{ Id = "Coccodrillo", Name = "Coccodrillo Tortellino", Rarity = "Legendary", Icon = "🐊" },
	{ Id = "Cappuccione", Name = "Re Cappuccione", Rarity = "Legendary", Icon = "👑" },
}

-- Lucky wheel. The server draws the reward; Weight is the relative chance
-- (the odds are shown to players, as Roblox requires for paid random items).
-- A reward holds Coins, Gems, Power, Spins, or Boosts = { BoostName = seconds }.
UIConfig.Wheel = {
	FreeSpinCooldown = 15 * 60, -- one free spin every 15 minutes
	Rewards = {
		{ Coins = 500, Weight = 30, Color = Color3.fromRGB(255, 92, 120) },
		{ Gems = 10, Weight = 22, Color = Color3.fromRGB(70, 170, 255) },
		{ Coins = 2500, Weight = 18, Color = Color3.fromRGB(255, 190, 50) },
		{ Boosts = { Power = 300 }, Weight = 14, Color = Color3.fromRGB(180, 95, 255) },
		{ Gems = 50, Weight = 10, Color = Color3.fromRGB(70, 210, 120) },
		{ Spins = 2, Weight = 6, Color = Color3.fromRGB(255, 130, 50) },
	},
	SpinProducts = { "Spins3", "Spins9" }, -- keys in UIConfig.Products
}

-- Game passes. Rewards are granted once; Multipliers apply forever.
UIConfig.GamePasses = {
	{
		Key = "StarterPack",
		Id = 0,
		Name = "Pack de départ",
		Description = "Un gros coup de pouce, une seule fois.",
		Icon = "🎁",
		PriceHint = 99,
		Rewards = { Coins = 25000, Gems = 100, Spins = 5 },
		Colors = { Color3.fromRGB(175, 80, 255), Color3.fromRGB(255, 120, 215) },
	},
	{
		Key = "DoublePower",
		Id = 0,
		Name = "Puissance x2",
		Description = "Double toute la puissance gagnée, pour toujours.",
		Icon = "💪",
		PriceHint = 199,
		Multipliers = { Power = 2 },
		Colors = { Color3.fromRGB(255, 120, 40), Color3.fromRGB(255, 205, 60) },
	},
	{
		Key = "DoubleCoins",
		Id = 0,
		Name = "Pièces x2",
		Description = "Double toutes les pièces ramassées, pour toujours.",
		Icon = "💰",
		PriceHint = 149,
		Multipliers = { Coins = 2 },
		Colors = { Color3.fromRGB(40, 185, 90), Color3.fromRGB(160, 235, 70) },
	},
}

-- Developer products (bought as many times as wanted).
-- Section decides where the product appears: Boosts / Coins (shop), Wheel, Rebirth, Offer (HUD).
UIConfig.Products = {
	{ Key = "BoostPower", Id = 0, Section = "Boosts", Name = "x2 Puissance", Description = "15 minutes", Icon = "⚡", PriceHint = 25, Grant = { Boosts = { Power = 900 } } },
	{ Key = "BoostCoins", Id = 0, Section = "Boosts", Name = "x2 Pièces", Description = "15 minutes", Icon = "🍀", PriceHint = 25, Grant = { Boosts = { Coins = 900 } } },
	{ Key = "BoostBoth", Id = 0, Section = "Boosts", Name = "Méga boost", Description = "Les deux, 30 minutes", Icon = "🚀", PriceHint = 79, Grant = { Boosts = { Power = 1800, Coins = 1800 } } },
	{ Key = "Coins1", Id = 0, Section = "Coins", Name = "Liasse", Description = "+5K pièces", Icon = "💵", PriceHint = 19, Grant = { Coins = 5000 } },
	{ Key = "Coins2", Id = 0, Section = "Coins", Name = "Sac", Description = "+50K pièces", Icon = "💰", PriceHint = 79, Grant = { Coins = 50000 } },
	{ Key = "Coins3", Id = 0, Section = "Coins", Name = "Banque", Description = "+500K pièces", Icon = "🏦", PriceHint = 249, Grant = { Coins = 500000 } },
	{ Key = "Spins3", Id = 0, Section = "Wheel", Name = "+3 tours", Icon = "🎡", PriceHint = 39, Grant = { Spins = 3 } },
	{ Key = "Spins9", Id = 0, Section = "Wheel", Name = "+9 tours", Icon = "🎡", PriceHint = 99, Tag = "MÉGA OFFRE", Grant = { Spins = 9 } },
	{ Key = "RebirthSkip", Id = 0, Section = "Rebirth", Name = "Renaissance immédiate", Icon = "🔁", PriceHint = 49, Grant = { RebirthSkip = true } },
	{ Key = "Offer", Id = 0, Section = "Offer", Name = "Offre spéciale", Icon = "💰", PriceHint = 45, Grant = { Coins = 250000 } },
}

-- Test pickups spawned around the SpawnLocation so everything can be tried at once.
-- Your own parts work too: tag them "BrainrotUIPickup" and set the attributes
-- Kind = "Coins" or "Power", and Rarity (Common/Rare/Epic/Legendary) for power orbs.
UIConfig.Pickups = {
	AutoSpawn = true,
	Tag = "BrainrotUIPickup",
	Count = 18,
	MinRadius = 14,
	MaxRadius = 70,
	RespawnTime = 8,
	CoinChance = 0.4,
	CoinAmount = 25,
}

-- Interface sounds (empty string = silent).
UIConfig.Sounds = {
	Volume = 0.5,
	Ids = {
		Click = "rbxasset://sounds/clickfast.wav",
		Open = "rbxasset://sounds/swoosh.wav",
		Tick = "rbxasset://sounds/snap.wav",
		Reward = "rbxasset://sounds/electronicpingshort.wav",
	},
}

-- Colours and fonts.
UIConfig.Theme = {
	TitleFont = Enum.Font.LuckiestGuy,
	BodyFont = Enum.Font.FredokaOne,
	Panel = Color3.fromRGB(28, 23, 52),
	PanelLight = Color3.fromRGB(46, 39, 82),
	Outline = Color3.fromRGB(12, 8, 22),
	Text = Color3.fromRGB(255, 255, 255),
	Muted = Color3.fromRGB(196, 190, 228),
	Green = Color3.fromRGB(72, 214, 84),
	Gold = Color3.fromRGB(255, 196, 40),
	Blue = Color3.fromRGB(60, 160, 255),
	Cyan = Color3.fromRGB(50, 215, 245),
	Purple = Color3.fromRGB(165, 90, 255),
	Pink = Color3.fromRGB(255, 90, 170),
	Orange = Color3.fromRGB(255, 140, 40),
	Red = Color3.fromRGB(240, 62, 72),
	Disabled = Color3.fromRGB(122, 120, 140),
	Windows = {
		Shop = { Color3.fromRGB(255, 215, 70), Color3.fromRGB(255, 135, 30) },
		Rebirth = { Color3.fromRGB(200, 110, 255), Color3.fromRGB(255, 80, 170) },
		Index = { Color3.fromRGB(80, 230, 255), Color3.fromRGB(60, 120, 255) },
		Wheel = { Color3.fromRGB(255, 110, 160), Color3.fromRGB(255, 170, 50) },
	},
}

-- Every text shown to players.
UIConfig.Text = {
	ShopButton = "BOUTIQUE",
	RebirthButton = "RENAISSANCE",
	IndexButton = "INDEX",
	WheelButton = "ROUE",
	InviteButton = "INVITER",
	OfferTag = "OFFRE",

	ShopTitle = "BOUTIQUE",
	RebirthTitle = "RENAISSANCE",
	IndexTitle = "INDEX",
	WheelTitle = "ROUE",

	SectionPasses = "PASS",
	SectionBoosts = "BOOSTS",
	SectionCoins = "PIÈCES",
	Owned = "POSSÉDÉ ✓",

	RebirthNumber = "Renaissance n°%d",
	Before = "AVANT",
	After = "APRÈS",
	PowerMultiplier = "multiplicateur de puissance",
	RebirthReward = "Récompense : +%s 💎",
	RebirthWarning = "⚠ Ta puissance et tes pièces repartent de zéro",
	RebirthAction = "RENAÎTRE",
	RebirthSkip = "PASSER",
	RebirthDone = "RENAISSANCE !",
	RebirthDoneSub = "Puissance x%s pour toujours",
	RebirthNotReady = "Pas encore assez de puissance !",
	RebirthReady = "Tu peux renaître !",

	IndexCollection = "Collection : %d / %d",
	IndexClaim = "RÉCLAMER %s 💎",
	IndexClaimed = "RÉCLAMÉ ✓",
	IndexIncomplete = "Trouve-les tous !",
	IndexLocked = "???",
	IndexNew = "NOUVEAU",
	IndexNewItem = "Nouveau brainrot : %s !",
	IndexClaimDone = "Série %s complétée : +%s 💎",
	IndexAlreadyClaimed = "Récompense déjà réclamée",

	Spins = "TOURS : %d",
	FreeSpinIn = "🎁 Tour gratuit dans %s",
	FreeSpinReady = "🎁 Tour gratuit disponible !",
	SpinAction = "TOURNER !",
	SpinsProduct = "+%d TOURS",
	Odds = "CHANCES",
	NoSpins = "Plus de tours : reviens plus tard ou achètes-en !",
	WheelWon = "GAGNÉ !",
	WheelSubtitle = "Roue de la chance",
	RandomRestricted = "Achat de tours indisponible ici",

	Buying = "Achat en cours…",
	PurchaseCancelled = "Achat annulé",
	PurchaseError = "L'achat n'a pas pu s'ouvrir",
	ProductMissing = "« %s » n'est pas encore en vente (ID à mettre dans UIConfig)",
	ThanksPurchase = "Merci pour ton achat ! 💖",
	AlreadyOwned = "Tu possèdes déjà ce pass",
	PassRewardGranted = "Récompenses du %s reçues !",
	BoostStarted = "%s activé !",

	InviteUnavailable = "Les invitations ne sont pas disponibles ici",
	TooFast = "Doucement !",
	GenericError = "Oups, réessaie",
	SessionOnly = "Mode test : ta progression ne sera pas sauvegardée",
	DataLoadFailed = "Impossible de charger tes données. Reviens dans un instant !",
}

return UIConfig
