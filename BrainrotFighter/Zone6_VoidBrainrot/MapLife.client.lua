-- MapLife: client-side ambient animation for the Brainrot Fighter maps.
-- Animates every BasePart tagged "MapLife" on this player's screen only (nothing replicates, the
-- server never pays for it). The map installers create this LocalScript and set these attributes:
--   LifeBob (studs)   LifePeriod (s)   LifePhase (0-1)   LifeSpin (rad/s)   LifeAxis (Vector3)
--   LifePivot (Vector3)   LifeSway (rad)   LifeLook (Vector3: resting gaze, the part follows the player)
--   LifeGlitch (bool)   LifePulse (0-1: neon colour and light brightness breathing)
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local TAG = "MapLife"
local MAX_DISTANCE = 900 -- parts farther than this from the camera are left alone
local PULSE_INTERVAL = 1 / 20 -- colours and lights are refreshed 20 times per second at most
local GAZE_SPEED = 3

local movers = {}
local pulsers = {}
local clock = 0
local pulseClock = 0
local parts = {}
local frames = {}

local function rotationBetween(a, b)
	local axis = a:Cross(b)
	local dot = math.clamp(a:Dot(b), -1, 1)
	if axis.Magnitude < 1e-5 then
		if dot > 0 then
			return CFrame.identity
		end
		local other = if math.abs(a.Y) < 0.9 then Vector3.yAxis else Vector3.xAxis
		return CFrame.fromAxisAngle(a:Cross(other).Unit, math.pi)
	end
	return CFrame.fromAxisAngle(axis.Unit, math.acos(dot))
end

local function register(inst)
	if not inst:IsA("BasePart") or movers[inst] or pulsers[inst] then
		return
	end
	local period = inst:GetAttribute("LifePeriod") or 6
	local axis = inst:GetAttribute("LifeAxis") or Vector3.yAxis
	local state = {
		rest = inst.CFrame,
		pivot = inst:GetAttribute("LifePivot") or inst.Position,
		bob = inst:GetAttribute("LifeBob") or 0,
		omega = 2 * math.pi / math.max(period, 0.5),
		phase = (inst:GetAttribute("LifePhase") or 0) * 2 * math.pi,
		spin = inst:GetAttribute("LifeSpin") or 0,
		axis = if axis.Magnitude > 1e-6 then axis.Unit else Vector3.yAxis,
		sway = inst:GetAttribute("LifeSway") or 0,
		look = inst:GetAttribute("LifeLook"),
		glitch = inst:GetAttribute("LifeGlitch") == true,
		pulse = inst:GetAttribute("LifePulse") or 0,
		color = inst.Color,
		transparency = inst.Transparency,
		gaze = CFrame.identity,
		jitter = Vector3.zero,
		nextGlitch = 0,
		lights = {},
	}
	for _, d in inst:GetDescendants() do
		if d:IsA("Light") then
			table.insert(state.lights, { light = d, brightness = d.Brightness })
		end
	end
	if state.bob ~= 0 or state.spin ~= 0 or state.sway ~= 0 or state.look or state.glitch then
		movers[inst] = state
	end
	if state.pulse > 0 then
		pulsers[inst] = state
	end
end

local function unregister(inst)
	movers[inst] = nil
	pulsers[inst] = nil
end

local function focusPoint(camera)
	local character = Players.LocalPlayer.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if root then
		return root.Position + Vector3.new(0, 1.5, 0)
	end
	return camera.CFrame.Position
end

local function step(dt)
	clock += dt
	local camera = workspace.CurrentCamera
	if not camera then
		return
	end
	local eye = camera.CFrame.Position
	local target = focusPoint(camera)
	table.clear(parts)
	table.clear(frames)
	for part, s in movers do
		if (s.pivot - eye).Magnitude < MAX_DISTANCE then
			local w = clock * s.omega + s.phase
			local rot = CFrame.identity
			if s.spin ~= 0 then
				rot = CFrame.fromAxisAngle(s.axis, clock * s.spin)
			end
			if s.sway ~= 0 then
				rot = CFrame.Angles(math.sin(w * 0.8) * s.sway, 0, math.cos(w * 0.6) * s.sway) * rot
			end
			if s.look then
				local toTarget = target - s.pivot
				if toTarget.Magnitude > 1 then
					local want = rotationBetween(s.look, toTarget.Unit)
					s.gaze = s.gaze:Lerp(want, math.min(1, dt * GAZE_SPEED))
				end
				rot = s.gaze * rot
			end
			local offset = Vector3.new(0, math.sin(w) * s.bob, 0)
			if s.glitch then
				if clock >= s.nextGlitch then
					s.nextGlitch = clock + 0.05 + math.random() * 0.6
					if math.random() < 0.55 then
						s.jitter = Vector3.new(math.random() - 0.5, math.random() - 0.5, math.random() - 0.5) * 3
					else
						s.jitter = Vector3.zero
					end
					part.Transparency = if math.random() < 0.2 then 1 else s.transparency
				end
				offset += s.jitter
			end
			table.insert(parts, part)
			table.insert(frames, CFrame.new(s.pivot + offset) * rot * CFrame.new(-s.pivot) * s.rest)
		end
	end
	if #parts > 0 then
		workspace:BulkMoveTo(parts, frames, Enum.BulkMoveMode.FireCFrameChanged)
	end

	pulseClock += dt
	if pulseClock < PULSE_INTERVAL then
		return
	end
	pulseClock = 0
	for part, s in pulsers do
		if (s.pivot - eye).Magnitude < MAX_DISTANCE then
			local f = 1 + s.pulse * 0.45 * math.sin(clock * s.omega + s.phase)
			if part.Material == Enum.Material.Neon then
				local c = s.color
				part.Color = Color3.new(math.min(1, c.R * f), math.min(1, c.G * f), math.min(1, c.B * f))
			end
			for _, entry in s.lights do
				entry.light.Brightness = entry.brightness * f
			end
		end
	end
end

for _, inst in CollectionService:GetTagged(TAG) do
	register(inst)
end
CollectionService:GetInstanceAddedSignal(TAG):Connect(register)
CollectionService:GetInstanceRemovedSignal(TAG):Connect(unregister)
RunService.Heartbeat:Connect(step)
