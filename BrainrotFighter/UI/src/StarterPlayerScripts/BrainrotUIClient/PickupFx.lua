-- PickupFx: makes the collectible coins and orbs float and spin, on this
-- screen only (the server never moves them). Pickups far from the camera are skipped.

local CollectionService = game:GetService("CollectionService")
local RunService = game:GetService("RunService")

local PickupFx = {}

local MAX_DISTANCE = 160

function PickupFx.start(tag: string)
	local entries: { [BasePart]: { base: CFrame, phase: number } } = {}

	local function add(instance: Instance)
		if instance:IsA("BasePart") then
			entries[instance] = { base = instance.CFrame, phase = math.random() * math.pi * 2 }
		end
	end
	for _, instance in CollectionService:GetTagged(tag) do
		add(instance)
	end
	CollectionService:GetInstanceAddedSignal(tag):Connect(add)
	CollectionService:GetInstanceRemovedSignal(tag):Connect(function(instance)
		entries[instance :: BasePart] = nil
	end)

	local parts: { BasePart } = {}
	local frames: { CFrame } = {}
	RunService.RenderStepped:Connect(function()
		local camera = workspace.CurrentCamera
		if not camera or next(entries) == nil then
			return
		end
		table.clear(parts)
		table.clear(frames)
		local cameraPosition = camera.CFrame.Position
		local now = os.clock()
		for part, entry in entries do
			if (entry.base.Position - cameraPosition).Magnitude < MAX_DISTANCE then
				table.insert(parts, part)
				table.insert(frames, entry.base * CFrame.new(0, math.sin(now * 2 + entry.phase) * 0.4, 0) * CFrame.Angles(0, now * 1.6 + entry.phase, 0))
			end
		end
		if #parts > 0 then
			workspace:BulkMoveTo(parts, frames, Enum.BulkMoveMode.FireCFrameChanged)
		end
	end)
end

return PickupFx
