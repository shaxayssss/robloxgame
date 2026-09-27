-- Minimal Roblox engine mock: datatypes, instances validated against the real
-- API definitions (CLASSES / ENUMS), services, a virtual-time scheduler and tweens.
-- Server and client scripts run in the same VM and share Player objects.

local realTypeof = typeof
local ROOT_ENV = getfenv(1)
local VIRTUAL_EPOCH = 1790000000
local now = 0 -- virtual seconds

local function mtype(v)
	local mt = getmetatable(v)
	if type(mt) == "table" and rawget(mt, "__type") then
		return mt.__type
	end
	return realTypeof(v)
end

------------------------------------------------------------------ datatypes
local function datatype(name, fields, extra)
	local mt = { __type = name }
	mt.__index = function(t, k)
		local f = extra and extra[k]
		if f ~= nil then
			if type(f) == "function" and extra.__getters and extra.__getters[k] then
				return f(t)
			end
			return f
		end
		error(("%s is not a valid member of %s"):format(tostring(k), name), 2)
	end
	mt.__newindex = function()
		error(name .. " is read-only", 2)
	end
	return mt
end

-- Vector2
local Vector2mt
Vector2mt = { __type = "Vector2" }
local function V2(x, y)
	return setmetatable({ X = x or 0, Y = y or 0 }, Vector2mt)
end
Vector2mt.__index = function(t, k)
	if k == "Magnitude" then
		return math.sqrt(rawget(t, "X") ^ 2 + rawget(t, "Y") ^ 2)
	end
	error(tostring(k) .. " is not a valid member of Vector2", 2)
end
Vector2mt.__add = function(a, b) return V2(a.X + b.X, a.Y + b.Y) end
Vector2mt.__sub = function(a, b) return V2(a.X - b.X, a.Y - b.Y) end
Vector2mt.__mul = function(a, b)
	if type(a) == "number" then return V2(a * b.X, a * b.Y) end
	if type(b) == "number" then return V2(a.X * b, a.Y * b) end
	return V2(a.X * b.X, a.Y * b.Y)
end
Vector2mt.__eq = function(a, b) return a.X == b.X and a.Y == b.Y end
Vector2 = { new = V2, zero = V2(0, 0), one = V2(1, 1) }

-- Vector3
local Vector3mt = { __type = "Vector3" }
local function V3(x, y, z)
	return setmetatable({ X = x or 0, Y = y or 0, Z = z or 0 }, Vector3mt)
end
Vector3mt.__index = function(t, k)
	if k == "Magnitude" then
		return math.sqrt(rawget(t, "X") ^ 2 + rawget(t, "Y") ^ 2 + rawget(t, "Z") ^ 2)
	end
	error(tostring(k) .. " is not a valid member of Vector3", 2)
end
Vector3mt.__add = function(a, b) return V3(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
Vector3mt.__sub = function(a, b) return V3(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
Vector3mt.__mul = function(a, b)
	if type(a) == "number" then return V3(a * b.X, a * b.Y, a * b.Z) end
	if type(b) == "number" then return V3(a.X * b, a.Y * b, a.Z * b) end
	return V3(a.X * b.X, a.Y * b.Y, a.Z * b.Z)
end
Vector3 = { new = V3, zero = V3(0, 0, 0) }

-- CFrame (translation only is enough here)
local CFramemt = { __type = "CFrame" }
local function CF(x, y, z)
	if mtype(x) == "Vector3" then
		return setmetatable({ Position = x }, CFramemt)
	end
	return setmetatable({ Position = V3(x or 0, y or 0, z or 0) }, CFramemt)
end
CFramemt.__index = function(_, k) error(tostring(k) .. " is not a valid member of CFrame", 2) end
CFramemt.__mul = function(a, b)
	if mtype(b) == "CFrame" then return CF(a.Position + b.Position) end
	return a.Position + b
end
CFrame = { new = CF, Angles = function() return CF(0, 0, 0) end, lookAt = function(p) return CF(p) end }

-- UDim / UDim2
local UDimmt = { __type = "UDim" }
UDimmt.__index = function(_, k) error(tostring(k) .. " is not a valid member of UDim", 2) end
local function UD(s, o) return setmetatable({ Scale = s or 0, Offset = o or 0 }, UDimmt) end
UDimmt.__add = function(a, b) return UD(a.Scale + b.Scale, a.Offset + b.Offset) end
UDim = { new = UD }
local UDim2mt = { __type = "UDim2" }
UDim2mt.__index = function(t, k)
	if k == "Width" then return rawget(t, "X") end
	if k == "Height" then return rawget(t, "Y") end
	error(tostring(k) .. " is not a valid member of UDim2", 2)
end
local function UD2(xs, xo, ys, yo)
	return setmetatable({ X = UD(xs, xo), Y = UD(ys, yo) }, UDim2mt)
end
UDim2mt.__add = function(a, b) return UD2(a.X.Scale + b.X.Scale, a.X.Offset + b.X.Offset, a.Y.Scale + b.Y.Scale, a.Y.Offset + b.Y.Offset) end
UDim2mt.__eq = function(a, b) return a.X.Scale == b.X.Scale and a.X.Offset == b.X.Offset and a.Y.Scale == b.Y.Scale and a.Y.Offset == b.Y.Offset end
UDim2 = {
	new = function(xs, xo, ys, yo)
		if mtype(xs) == "UDim" then
			return UD2(xs.Scale, xs.Offset, xo.Scale, xo.Offset)
		end
		return UD2(xs, xo, ys, yo)
	end,
	fromScale = function(x, y) return UD2(x, 0, y, 0) end,
	fromOffset = function(x, y) return UD2(0, x, 0, y) end,
}

-- Color3
local Color3mt = { __type = "Color3" }
local function C3(r, g, b) return setmetatable({ R = r or 0, G = g or 0, B = b or 0 }, Color3mt) end
Color3mt.__index = function(t, k)
	if k == "Lerp" then
		return function(a, b, alpha)
			return C3(a.R + (b.R - a.R) * alpha, a.G + (b.G - a.G) * alpha, a.B + (b.B - a.B) * alpha)
		end
	end
	if k == "ToHSV" then return function() return 0, 0, 0 end end
	error(tostring(k) .. " is not a valid member of Color3", 2)
end
Color3mt.__eq = function(a, b) return a.R == b.R and a.G == b.G and a.B == b.B end
Color3 = {
	new = C3,
	fromRGB = function(r, g, b) return C3((r or 0) / 255, (g or 0) / 255, (b or 0) / 255) end,
	fromHSV = function(h, s, v)
		local i = math.floor(h * 6); local f = h * 6 - i
		local p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
		i = i % 6
		if i == 0 then return C3(v, t, p) elseif i == 1 then return C3(q, v, p) elseif i == 2 then return C3(p, v, t)
		elseif i == 3 then return C3(p, q, v) elseif i == 4 then return C3(t, p, v) else return C3(v, p, q) end
	end,
}

-- Sequences
local function keypointType(name)
	local mt = { __type = name }
	mt.__index = function(_, k) error(tostring(k) .. " is not a valid member of " .. name, 2) end
	return mt
end
local CSKmt, NSKmt = keypointType("ColorSequenceKeypoint"), keypointType("NumberSequenceKeypoint")
ColorSequenceKeypoint = { new = function(t, c) return setmetatable({ Time = t, Value = c }, CSKmt) end }
NumberSequenceKeypoint = { new = function(t, v, e) return setmetatable({ Time = t, Value = v, Envelope = e or 0 }, NSKmt) end }
local CSmt, NSmt = keypointType("ColorSequence"), keypointType("NumberSequence")
local function checkKeypoints(kps, name)
	assert(#kps >= 2 and #kps <= 20, name .. ": 2..20 keypoints required")
	assert(kps[1].Time == 0 and kps[#kps].Time == 1, name .. ": must start at 0 and end at 1")
	for i = 2, #kps do
		assert(kps[i].Time >= kps[i - 1].Time, name .. ": keypoints must be sorted")
	end
end
ColorSequence = {
	new = function(a, b)
		local kps
		if mtype(a) == "Color3" then
			kps = { ColorSequenceKeypoint.new(0, a), ColorSequenceKeypoint.new(1, b or a) }
		else
			kps = a
		end
		checkKeypoints(kps, "ColorSequence")
		return setmetatable({ Keypoints = kps }, CSmt)
	end,
}
NumberSequence = {
	new = function(a, b)
		local kps
		if type(a) == "number" then
			kps = { NumberSequenceKeypoint.new(0, a), NumberSequenceKeypoint.new(1, b or a) }
		else
			kps = a
		end
		checkKeypoints(kps, "NumberSequence")
		return setmetatable({ Keypoints = kps }, NSmt)
	end,
}
local NRmt = keypointType("NumberRange")
NumberRange = { new = function(a, b) return setmetatable({ Min = a, Max = b or a }, NRmt) end }
local Rectmt = keypointType("Rect")
Rect = { new = function(a, b, c, d) return setmetatable({ Min = V2(a, b), Max = V2(c, d) }, Rectmt) end }
local TweenInfomt = keypointType("TweenInfo")
TweenInfo = {
	new = function(time, style, direction, repeatCount, reverses, delay)
		return setmetatable({
			Time = time or 1,
			EasingStyle = style or Enum.EasingStyle.Quad,
			EasingDirection = direction or Enum.EasingDirection.Out,
			RepeatCount = repeatCount or 0,
			Reverses = reverses or false,
			DelayTime = delay or 0,
		}, TweenInfomt)
	end,
}
local Fontmt = keypointType("Font")
Font = {
	fromEnum = function(item)
		assert(item.EnumType == "Font", "Font.fromEnum expects an Enum.Font")
		return setmetatable({ Family = item.Name, Weight = "Regular", Style = "Normal" }, Fontmt)
	end,
	new = function(family) return setmetatable({ Family = family, Weight = "Regular", Style = "Normal" }, Fontmt) end,
}
local RaycastParamsmt = { __type = "RaycastParams" }
RaycastParamsmt.__index = function(_, k) error(tostring(k) .. " is not a valid member of RaycastParams", 2) end
RaycastParams = {
	new = function()
		return setmetatable({ FilterType = nil, FilterDescendantsInstances = {}, IgnoreWater = false, CollisionGroup = "Default", RespectCanCollide = false }, { __type = "RaycastParams" })
	end,
}
local Randommt = { __type = "Random" }
Randommt.__index = {
	NextNumber = function(self, a, b)
		self.state = (self.state * 1103515245 + 12345) % 2147483648
		local r = self.state / 2147483648
		if a then return a + (b - a) * r end
		return r
	end,
	NextInteger = function(self, a, b)
		return a + math.floor(self:NextNumber() * (b - a + 1))
	end,
}
Random = { new = function(seed) return setmetatable({ state = seed or 12345 }, Randommt) end }

------------------------------------------------------------------ enums
local enumItemMt = { __type = "EnumItem" }
enumItemMt.__index = function(_, k) error(tostring(k) .. " is not a valid member of EnumItem", 2) end
enumItemMt.__tostring = function(item) return "Enum." .. item.EnumType .. "." .. item.Name end
Enum = setmetatable({}, {
	__index = function(t, enumName)
		local items = ENUMS[enumName]
		if not items then
			error(tostring(enumName) .. " is not a valid Enum", 2)
		end
		local enum = {}
		for index, name in items do
			enum[name] = setmetatable({ Name = name, Value = index, EnumType = enumName }, enumItemMt)
		end
		local proxy = setmetatable({}, {
			__index = function(_, itemName)
				if itemName == "GetEnumItems" then
					return function() local list = {} for _, n in items do table.insert(list, enum[n]) end return list end
				end
				local item = enum[itemName]
				if not item then
					error(tostring(itemName) .. " is not a valid EnumItem of Enum." .. enumName, 2)
				end
				return item
			end,
		})
		rawset(t, enumName, proxy)
		return proxy
	end,
})

------------------------------------------------------------------ scheduler
local queue = {}
local seq = 0
local function schedule(at, co, ...)
	seq += 1
	table.insert(queue, { at = at, seq = seq, co = co, args = table.pack(...) })
end
local ERRORS = {}
local function resume(co, ...)
	local ok, err = coroutine.resume(co, ...)
	if not ok then
		local trace = debug.traceback(co, tostring(err))
		table.insert(ERRORS, trace)
		print("SCRIPT ERROR: " .. trace)
	end
end
task = {}
function task.spawn(f, ...)
	local co = if type(f) == "thread" then f else coroutine.create(f)
	resume(co, ...)
	return co
end
function task.defer(f, ...)
	local co = if type(f) == "thread" then f else coroutine.create(f)
	schedule(now, co, ...)
	return co
end
function task.delay(t, f, ...)
	local co = if type(f) == "thread" then f else coroutine.create(f)
	schedule(now + (t or 0), co, ...)
	return co
end
function task.wait(t)
	local co = coroutine.running()
	local start = now
	schedule(now + math.max(t or 0, 1 / 60), co)
	coroutine.yield()
	return now - start
end
function task.cancel() end

------------------------------------------------------------------ signals
local Signalmt = { __type = "RBXScriptSignal" }
Signalmt.__index = Signalmt
local Connectionmt = { __type = "RBXScriptConnection" }
Connectionmt.__index = Connectionmt
function Connectionmt:Disconnect() self.Connected = false end
local function newSignal() return setmetatable({ handlers = {} }, Signalmt) end
function Signalmt:Connect(fn)
	assert(type(fn) == "function", "Connect expects a function")
	local c = setmetatable({ Connected = true, fn = fn }, Connectionmt)
	table.insert(self.handlers, c)
	return c
end
function Signalmt:Once(fn)
	local c
	c = self:Connect(function(...) c:Disconnect() fn(...) end)
	return c
end
function Signalmt:Wait()
	local co = coroutine.running()
	local c
	c = self:Connect(function(...) c:Disconnect() resume(co, ...) end)
	return coroutine.yield()
end
function Signalmt:Fire(...)
	for _, c in table.clone(self.handlers) do
		if c.Connected then
			task.spawn(c.fn, ...)
		end
	end
end

------------------------------------------------------------------ instances
local Instancemt = { __type = "Instance" }
local ALL = setmetatable({}, { __mode = "k" })

local function classInfo(className, key)
	local c = className
	while c do
		local info = CLASSES[c]
		if not info then return nil end
		if info.props[key] then return "prop", info.props[key] end
		if info.methods[key] then return "method" end
		c = info.super
	end
	return nil
end
local function isA(className, target)
	local c = className
	while c do
		if c == target then return true end
		local info = CLASSES[c]
		c = info and info.super
	end
	return false
end

local DEFAULTS = {
	Visible = true, BackgroundTransparency = 0, BackgroundColor3 = C3(0.64, 0.635, 0.647), BorderSizePixel = 1,
	Size = UD2(0, 0, 0, 0), Position = UD2(0, 0, 0, 0), AnchorPoint = V2(0, 0), Rotation = 0, ZIndex = 1,
	LayoutOrder = 0, TextTransparency = 0, Transparency = 0, Scale = 1, Enabled = true, Thickness = 1,
	Text = "", TextSize = 14, TextColor3 = C3(0, 0, 0), Value = 0, ClipsDescendants = false, Active = false,
	CanvasPosition = V2(0, 0), Interactable = true, TextScaled = false, TextWrapped = false,
}

local methods = {}
local newInstance

local function propType(inst, key)
	local kind, ptype = classInfo(inst.ClassName, key)
	return kind, ptype
end

local function checkValue(inst, key, ptype, value)
	if value == nil then return end
	local t = ptype:gsub("%?$", "")
	local vt = mtype(value)
	local simple = { number = "number", boolean = "boolean", string = "string", ContentId = "string", Content = nil }
	if simple[t] then
		if vt ~= simple[t] then
			error(("bad value for %s.%s: expected %s, got %s"):format(inst.ClassName, key, t, vt), 3)
		end
	elseif t:match("^Enum%u") then
		if vt ~= "EnumItem" or ("Enum" .. value.EnumType) ~= t then
			error(("bad value for %s.%s: expected %s, got %s"):format(inst.ClassName, key, t, vt == "EnumItem" and ("Enum" .. value.EnumType) or vt), 3)
		end
	elseif ({ UDim2 = 1, UDim = 1, Vector2 = 1, Vector3 = 1, Color3 = 1, ColorSequence = 1, NumberSequence = 1, Font = 1, NumberRange = 1, Rect = 1, CFrame = 1 })[t] then
		if vt ~= t then
			error(("bad value for %s.%s: expected %s, got %s"):format(inst.ClassName, key, t, vt), 3)
		end
	end
end

Instancemt.__index = function(inst, key)
	local props = rawget(inst, "_props")
	if props[key] ~= nil then return props[key] end
	if key == "Parent" then return rawget(inst, "_parent") end
	if key == "ClassName" then return rawget(inst, "_class") end
	local special = rawget(inst, "_getters")
	if special and special[key] then return special[key](inst) end
	local kind, ptype = classInfo(rawget(inst, "_class"), key)
	if kind == "method" or (methods[key] and not kind) then
		local m = methods[key]
		if not m then
			error(("mock: method %s:%s not implemented"):format(rawget(inst, "_class"), key), 2)
		end
		return m
	end
	if kind == "prop" then
		if ptype:match("^RBXScriptSignal") then
			local signals = rawget(inst, "_signals")
			if not signals[key] then signals[key] = newSignal() end
			return signals[key]
		end
		if DEFAULTS[key] ~= nil then return DEFAULTS[key] end
		return nil
	end
	for _, child in rawget(inst, "_children") do
		if child.Name == key then return child end
	end
	error(("%s is not a valid member of %s \"%s\""):format(tostring(key), rawget(inst, "_class"), tostring(props.Name)), 2)
end

local function fireChanged(inst, key, value)
	local signals = rawget(inst, "_signals")
	local pc = rawget(inst, "_propSignals")[key]
	if pc then pc:Fire() end
	if signals.Changed then
		if isA(rawget(inst, "_class"), "ValueBase") then
			if key == "Value" then signals.Changed:Fire(value) end
		else
			signals.Changed:Fire(key)
		end
	end
end

Instancemt.__newindex = function(inst, key, value)
	if rawget(inst, "_destroyed") and key == "Parent" then
		error("The Parent property of " .. tostring(inst.Name) .. " is locked", 2)
	end
	if key == "Parent" then
		local old = rawget(inst, "_parent")
		if old == value then return end
		if old then
			local list = rawget(old, "_children")
			local i = table.find(list, inst)
			if i then table.remove(list, i) end
		end
		rawset(inst, "_parent", value)
		if value then
			assert(mtype(value) == "Instance", "Parent must be an Instance")
			table.insert(rawget(value, "_children"), inst)
			local sig = rawget(value, "_signals").ChildAdded
			if sig then sig:Fire(inst) end
		end
		fireChanged(inst, "Parent", value)
		return
	end
	local setter = rawget(inst, "_setters")
	if setter and setter[key] then
		setter[key](inst, value)
		return
	end
	local kind, ptype = classInfo(rawget(inst, "_class"), key)
	if kind ~= "prop" then
		error(("%s is not a valid member of %s"):format(tostring(key), rawget(inst, "_class")), 2)
	end
	if ptype:match("^RBXScriptSignal") then
		error(("%s.%s is an event and cannot be assigned"):format(rawget(inst, "_class"), key), 2)
	end
	checkValue(inst, key, ptype, value)
	local props = rawget(inst, "_props")
	if props[key] == value then return end
	props[key] = value
	fireChanged(inst, key, value)
end
Instancemt.__tostring = function(inst) return tostring(rawget(inst, "_props").Name) end

newInstance = function(className, isService)
	if not CLASSES[className] then
		error("Unable to create an Instance of type \"" .. tostring(className) .. "\"", 3)
	end
	local inst = setmetatable({
		_class = className,
		_props = { Name = className },
		_children = {},
		_signals = {},
		_propSignals = {},
		_attributes = {},
		_attrSignals = {},
	}, Instancemt)
	ALL[inst] = true
	return inst
end

function methods.IsA(self, name) return isA(self.ClassName, name) end
function methods.GetChildren(self) return table.clone(rawget(self, "_children")) end
function methods.GetDescendants(self)
	local out = {}
	local function walk(i) for _, c in rawget(i, "_children") do table.insert(out, c) walk(c) end end
	walk(self)
	return out
end
function methods.FindFirstChild(self, name, recursive)
	for _, c in rawget(self, "_children") do
		if c.Name == name then return c end
	end
	if recursive then
		for _, c in rawget(self, "_children") do
			local f = methods.FindFirstChild(c, name, true)
			if f then return f end
		end
	end
	return nil
end
function methods.FindFirstChildOfClass(self, cls)
	for _, c in rawget(self, "_children") do if c.ClassName == cls then return c end end
	return nil
end
function methods.FindFirstChildWhichIsA(self, cls, recursive)
	for _, c in rawget(self, "_children") do if c:IsA(cls) then return c end end
	if recursive then
		for _, c in rawget(self, "_children") do
			local f = methods.FindFirstChildWhichIsA(c, cls, true)
			if f then return f end
		end
	end
	return nil
end
function methods.FindFirstAncestorOfClass(self, cls)
	local p = self.Parent
	while p do if p.ClassName == cls then return p end p = p.Parent end
	return nil
end
function methods.IsDescendantOf(self, other)
	local p = self.Parent
	while p do if p == other then return true end p = p.Parent end
	return false
end
function methods.WaitForChild(self, name, timeout)
	local found = methods.FindFirstChild(self, name)
	local waited = 0
	while not found do
		if waited > 5 then
			error(("Infinite yield on %s:WaitForChild(\"%s\")"):format(tostring(self.Name), name), 2)
		end
		waited += task.wait(0.1)
		found = methods.FindFirstChild(self, name)
	end
	return found
end
function methods.Destroy(self)
	for _, c in table.clone(rawget(self, "_children")) do methods.Destroy(c) end
	self.Parent = nil
	rawset(self, "_destroyed", true)
end
function methods.ClearAllChildren(self)
	for _, c in table.clone(rawget(self, "_children")) do methods.Destroy(c) end
end
function methods.GetAttribute(self, name) return rawget(self, "_attributes")[name] end
function methods.GetAttributes(self) return table.clone(rawget(self, "_attributes")) end
function methods.SetAttribute(self, name, value)
	assert(type(name) == "string" and name:match("^[%w_]+$") and #name <= 100, "bad attribute name " .. tostring(name))
	local vt = mtype(value)
	assert(value == nil or vt == "number" or vt == "string" or vt == "boolean" or vt == "Color3" or vt == "Vector3" or vt == "UDim2", "bad attribute type " .. vt)
	local attrs = rawget(self, "_attributes")
	if attrs[name] == value then return end
	attrs[name] = value
	local s = rawget(self, "_attrSignals")[name]
	if s then s:Fire() end
	local sig = rawget(self, "_signals").AttributeChanged
	if sig then sig:Fire(name) end
end
function methods.GetAttributeChangedSignal(self, name)
	local list = rawget(self, "_attrSignals")
	if not list[name] then list[name] = newSignal() end
	return list[name]
end
function methods.GetPropertyChangedSignal(self, name)
	local kind = classInfo(self.ClassName, name)
	assert(kind == "prop", "not a property: " .. tostring(name))
	local list = rawget(self, "_propSignals")
	if not list[name] then list[name] = newSignal() end
	return list[name]
end
function methods.Kick(self, message) print("KICK " .. tostring(self.Name) .. ": " .. tostring(message)) self.Parent = nil end

------------------------------------------------------------------ remotes
function methods.InvokeServer(self, ...)
	local handler = rawget(self, "_props").OnServerInvoke
	assert(handler, "no OnServerInvoke")
	return handler(LOCAL_PLAYER, ...)
end
function methods.FireClient(self, player, ...)
	self.OnClientEvent:Fire(...)
end
function methods.FireServer(self, ...)
	self.OnServerEvent:Fire(LOCAL_PLAYER, ...)
end
function methods.FireAllClients(self, ...) self.OnClientEvent:Fire(...) end
function methods.Fire(self, ...) self.Event:Fire(...) end

------------------------------------------------------------------ tweens
local EASE = {}
function EASE.Linear(t) return t end
function EASE.Quad(t) return t * t end
function EASE.Quart(t) return t ^ 4 end
function EASE.Quint(t) return t ^ 5 end
function EASE.Sine(t) return 1 - math.cos(t * math.pi / 2) end
function EASE.Back(t) local s = 1.70158 return t * t * ((s + 1) * t - s) end
function EASE.Cubic(t) return t ^ 3 end
local function ease(style, direction, t)
	local f = EASE[style.Name] or EASE.Quad
	if direction.Name == "In" then return f(t) end
	if direction.Name == "Out" then return 1 - f(1 - t) end
	if t < 0.5 then return f(t * 2) / 2 end
	return 1 - f((1 - t) * 2) / 2
end
local function lerp(a, b, t)
	local ta = mtype(a)
	if ta == "number" then return a + (b - a) * t end
	if ta == "UDim2" then
		return UD2(a.X.Scale + (b.X.Scale - a.X.Scale) * t, a.X.Offset + (b.X.Offset - a.X.Offset) * t, a.Y.Scale + (b.Y.Scale - a.Y.Scale) * t, a.Y.Offset + (b.Y.Offset - a.Y.Offset) * t)
	end
	if ta == "Color3" then return a:Lerp(b, t) end
	if ta == "Vector2" then return V2(a.X + (b.X - a.X) * t, a.Y + (b.Y - a.Y) * t) end
	return if t >= 1 then b else a
end
local activeTweens = {}
local Tweenmt = { __type = "Instance" }
local function newTween(inst, info, goal)
	assert(mtype(info) == "TweenInfo", "TweenService:Create expects a TweenInfo")
	for key, value in goal do
		local kind, ptype = classInfo(inst.ClassName, key)
		assert(kind == "prop", ("tween: %s is not a property of %s"):format(key, inst.ClassName))
		checkValue(inst, key, ptype, value)
	end
	local tween = { inst = inst, info = info, goal = goal, Completed = newSignal(), PlaybackState = Enum.PlaybackState.Begin }
	function tween.Play(self)
		self.start = now + info.DelayTime
		self.from = {}
		self.PlaybackState = Enum.PlaybackState.Playing
		-- a newer tween on the same property cancels the older one
		for other in activeTweens do
			if other.inst == inst and other ~= self then
				for key in goal do
					if other.goal[key] ~= nil then
						activeTweens[other] = nil
						other.PlaybackState = Enum.PlaybackState.Cancelled
						other.Completed:Fire(Enum.PlaybackState.Cancelled)
						break
					end
				end
			end
		end
		activeTweens[self] = true
	end
	function tween.Cancel(self)
		if activeTweens[self] then
			activeTweens[self] = nil
			self.Completed:Fire(Enum.PlaybackState.Cancelled)
		end
	end
	function tween.Pause(self) activeTweens[self] = nil end
	function tween.Destroy() end
	return tween
end
local function stepTweens()
	for tween in table.clone(activeTweens) do
		if activeTweens[tween] and now >= tween.start then
			local info = tween.info
			if next(tween.from) == nil then
				for key in tween.goal do tween.from[key] = tween.inst[key] end
			end
			local elapsed = now - tween.start
			local duration = math.max(info.Time, 1e-6)
			local t, done
			if info.RepeatCount < 0 then
				local cycle = if info.Reverses then duration * 2 else duration
				local local_ = elapsed % cycle
				t = local_ / duration
				if t > 1 then t = 2 - t end
				done = false
			else
				t = math.min(elapsed / duration, 1)
				done = elapsed >= duration
			end
			local alpha = ease(info.EasingStyle, info.EasingDirection, t)
			for key, target in tween.goal do
				tween.inst[key] = lerp(tween.from[key], target, alpha)
			end
			if done then
				activeTweens[tween] = nil
				tween.PlaybackState = Enum.PlaybackState.Completed
				tween.Completed:Fire(Enum.PlaybackState.Completed)
			end
		end
	end
end

------------------------------------------------------------------ data model
game = newInstance("DataModel")
game.Name = "Game"
rawset(game, "_getters", { JobId = function() return "" end, PlaceId = function() return 0 end, GameId = function() return 0 end })
local services = {}
local function service(name)
	local s = services[name]
	if not s then
		s = newInstance(name)
		s.Name = name
		s.Parent = game
		services[name] = s
	end
	return s
end
function methods.GetService(self, name) return service(name) end
function methods.BindToClose(self, fn) table.insert(BIND_TO_CLOSE, fn) end
BIND_TO_CLOSE = {}

local Players = service("Players")
local Workspace = service("Workspace")
workspace = Workspace
local RunService = service("RunService")
local camera = newInstance("Camera")
rawset(camera, "_getters", {
	ViewportSize = function() return VIEWPORT end,
	CFrame = function() return CF(0, 10, 0) end,
})
camera.Parent = Workspace
rawset(Workspace, "_getters", { CurrentCamera = function() return camera end })
function methods.GetServerTimeNow() return VIRTUAL_EPOCH + now end
function methods.Raycast() return nil end
function methods.BulkMoveTo() end
function methods.IsStudio() return true end
function methods.IsServer() return true end
function methods.IsClient() return true end

-- TweenService
function methods.Create(self, inst, info, goal) return newTween(inst, info, goal) end
-- SoundService
PLAYED_SOUNDS = {}
function methods.PlayLocalSound(self, sound) table.insert(PLAYED_SOUNDS, sound.Name) end
-- Marketplace
PROMPTS = {}
function methods.PromptProductPurchase(self, player, id) table.insert(PROMPTS, { "Product", id }) end
function methods.PromptGamePassPurchase(self, player, id) table.insert(PROMPTS, { "Pass", id }) end
function methods.GetProductInfoAsync(self, id) return { PriceInRobux = 42 } end
function methods.UserOwnsGamePassAsync() return false end
function methods.GetPolicyInfoForPlayerAsync() return { ArePaidRandomItemsRestricted = false } end
function methods.CanSendGameInviteAsync() return false end
function methods.PromptGameInvite() end
-- DataStore (in memory, with UpdateAsync semantics)
DATASTORE = {}
local function deepCopy(value)
	if type(value) ~= "table" then return value end
	local out = {}
	for k, v in value do out[k] = deepCopy(v) end
	return out
end
warn = function(...) print("WARN", ...) end
local DataStoremt = { __type = "Instance" }
DataStoremt.__index = {
	GetAsync = function(self, key) return deepCopy(DATASTORE[key]) end,
	UpdateAsync = function(self, key, fn)
		local new = fn(deepCopy(DATASTORE[key]))
		if new ~= nil then
			DATASTORE[key] = deepCopy(new)
			return deepCopy(new)
		end
		return nil
	end,
	SetAsync = function(self, key, value) DATASTORE[key] = value end,
}
function methods.GetDataStore(self, name) return setmetatable({ name = name }, DataStoremt) end
-- CollectionService
local tagged = {}
function methods.GetTagged(self, tag) return table.clone(tagged[tag] or {}) end
function methods.AddTag(self, inst, tag) tagged[tag] = tagged[tag] or {} table.insert(tagged[tag], inst) end
local tagSignals = {}
function methods.GetInstanceAddedSignal(self, tag) tagSignals[tag] = tagSignals[tag] or newSignal() return tagSignals[tag] end
function methods.GetInstanceRemovedSignal(self, tag) return newSignal() end
-- ContextActionService / UserInputService
BOUND_ACTIONS = {}
function methods.BindActionAtPriority(self, name, fn, touch, priority, ...)
	assert(type(priority) == "number", "priority must be a number")
	BOUND_ACTIONS[name] = fn
end
function methods.UnbindAction(self, name) BOUND_ACTIONS[name] = nil end
function methods.GetLastInputType() return Enum.UserInputType.MouseButton1 end
-- Players
function methods.GetPlayers(self) return self:GetChildren() end
function methods.GetPlayerByUserId(self, id)
	for _, p in self:GetChildren() do if p.UserId == id then return p end end
	return nil
end
function methods.GetPlayerFromCharacter() return nil end

Instance = { new = function(className, parent)
	local inst = newInstance(className)
	if className == "ScreenGui" then
		rawset(inst, "_getters", { AbsoluteSize = function() return V2(VIEWPORT.X, VIEWPORT.Y - TOP_INSET) end })
	end
	if parent then inst.Parent = parent end
	return inst
end }

typeof = mtype

function makePlayer(userId, name)
	local p = newInstance("Player")
	rawset(p, "_userId", userId)
	rawset(p, "_getters", { UserId = function(i) return rawget(i, "_userId") end })
	p.Name = name
	local gui = newInstance("PlayerGui")
	gui.Name = "PlayerGui"
	gui.Parent = p
	local scripts = newInstance("PlayerScripts")
	scripts.Name = "PlayerScripts"
	scripts.Parent = p
	return p
end

------------------------------------------------------------------ script loading
local moduleCache = {}
local runChunk
local function requireModuleImpl(target)
	assert(mtype(target) == "Instance" and target.ClassName == "ModuleScript", "require expects a ModuleScript")
	if moduleCache[target] == nil then
		local result = runChunk(target, rawget(target, "_source"), rawget(target, "_path"))
		assert(result ~= nil, "module returned nil: " .. rawget(target, "_path"))
		moduleCache[target] = result
	end
	return moduleCache[target]
end
requireModule = requireModuleImpl
runChunk = function(inst, source, chunkName, ...)
	local fn, err = loadstring(source, "=" .. chunkName)
	if not fn then error("compile error in " .. chunkName .. ": " .. tostring(err)) end
	local env = setmetatable({ script = inst, require = nil }, { __index = ROOT_ENV })
	env.require = requireModuleImpl
	env.os = setmetatable({
		clock = function() return now end,
		time = function() return math.floor(VIRTUAL_EPOCH + now) end,
	}, { __index = os })
	setfenv(fn, env)
	return fn(...)
end

-- path parts like {"ReplicatedStorage", "BrainrotUI", "UIConfig"} → builds folders/scripts
function mountTree(parent, node, pathPrefix)
	local inst = newInstance(node.className)
	inst.Name = node.name
	rawset(inst, "_path", pathPrefix .. "/" .. node.name)
	if node.source then rawset(inst, "_source", node.source) end
	for _, child in node.children or {} do
		mountTree(inst, child, pathPrefix .. "/" .. node.name)
	end
	inst.Parent = parent
	return inst
end

function runScript(inst)
	local co = coroutine.create(function()
		runChunk(inst, rawget(inst, "_source"), rawget(inst, "_path"))
	end)
	resume(co)
end

function advance(seconds, step)
	step = step or (1 / 30)
	local target = now + seconds
	while now < target - 1e-9 do
		now += step
		local rs = rawget(RunService, "_signals")
		if rs.RenderStepped then rs.RenderStepped:Fire(step) end
		if rs.Heartbeat then rs.Heartbeat:Fire(step) end
		stepTweens()
		table.sort(queue, function(a, b) if a.at == b.at then return a.seq < b.seq end return a.at < b.at end)
		while queue[1] and queue[1].at <= now do
			local item = table.remove(queue, 1)
			if coroutine.status(item.co) == "suspended" then
				resume(item.co, table.unpack(item.args, 1, item.args.n))
			end
		end
	end
end

function virtualNow() return now end

------------------------------------------------------------------ snapshot
local function encodeValue(v)
	local t = mtype(v)
	if t == "number" then
		if v ~= v or v == math.huge or v == -math.huge then return "0" end
		return string.format("%.6g", v)
	elseif t == "boolean" then return tostring(v)
	elseif t == "string" then
		return '"' .. v:gsub('[%c"\\]', function(c)
			if c == '"' then return '\\"' elseif c == "\\" then return "\\\\" elseif c == "\n" then return "\\n" else return string.format("\\u%04x", c:byte()) end
		end) .. '"'
	elseif t == "UDim2" then return string.format("[%g,%g,%g,%g]", v.X.Scale, v.X.Offset, v.Y.Scale, v.Y.Offset)
	elseif t == "UDim" then return string.format("[%g,%g]", v.Scale, v.Offset)
	elseif t == "Vector2" then return string.format("[%g,%g]", v.X, v.Y)
	elseif t == "Color3" then return string.format("[%g,%g,%g]", v.R, v.G, v.B)
	elseif t == "EnumItem" then return '"' .. v.Name .. '"'
	elseif t == "Font" then return '"' .. v.Family .. '"'
	elseif t == "ColorSequence" then
		local parts = {}
		for _, k in v.Keypoints do table.insert(parts, string.format("[%g,%g,%g,%g]", k.Time, k.Value.R, k.Value.G, k.Value.B)) end
		return "[" .. table.concat(parts, ",") .. "]"
	elseif t == "NumberSequence" then
		local parts = {}
		for _, k in v.Keypoints do table.insert(parts, string.format("[%g,%g]", k.Time, k.Value)) end
		return "[" .. table.concat(parts, ",") .. "]"
	end
	return nil
end
local SNAP_PROPS = {
	"Name", "Visible", "Size", "Position", "AnchorPoint", "Rotation", "ZIndex", "LayoutOrder", "BackgroundColor3",
	"BackgroundTransparency", "ClipsDescendants", "Text", "TextColor3", "TextSize", "TextTransparency", "TextScaled",
	"TextWrapped", "TextXAlignment", "TextYAlignment", "FontFace", "CornerRadius", "Thickness", "Color", "Transparency",
	"ApplyStrokeMode", "Enabled", "Offset", "Scale", "Padding", "FillDirection", "HorizontalAlignment", "VerticalAlignment",
	"SortOrder", "CellSize", "CellPadding", "PaddingTop", "PaddingBottom", "PaddingLeft", "PaddingRight", "MaxTextSize",
	"MinTextSize", "CanvasSize", "CanvasPosition", "AutomaticCanvasSize", "ScrollBarThickness", "DisplayOrder", "AspectRatio",
}
function snapshot(inst)
	local parts = { '{"c":"' .. inst.ClassName .. '","p":{' }
	local first = true
	local props = rawget(inst, "_props")
	for _, key in SNAP_PROPS do
		local v = props[key]
		if v == nil and DEFAULTS[key] ~= nil and classInfo(inst.ClassName, key) == "prop" then v = DEFAULTS[key] end
		if v ~= nil then
			local enc = encodeValue(v)
			if enc then
				table.insert(parts, (if first then "" else ",") .. '"' .. key .. '":' .. enc)
				first = false
			end
		end
	end
	table.insert(parts, '},"k":[')
	for i, child in rawget(inst, "_children") do
		table.insert(parts, (if i > 1 then "," else "") .. snapshot(child))
	end
	table.insert(parts, "]}")
	return table.concat(parts)
end

function setViewport(size)
	VIEWPORT = size
end
VIEWPORT = V2(1280, 720)
TOP_INSET = 58
