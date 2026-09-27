-- Format: number and time formatting for the interface (1.25K, 3.4M, 12:05...).

local Format = {}

local SUFFIXES = { "", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc" }

-- Removes trailing zeros after a decimal point: "1.50" -> "1.5", "2.00" -> "2".
local function trimZeros(text: string): string
	if not string.find(text, ".", 1, true) then
		return text
	end
	text = (string.gsub(text, "0+$", ""))
	text = (string.gsub(text, "%.$", ""))
	return text
end

-- 999 -> "999", 1234 -> "1.23K", 12345 -> "12.3K", 123456 -> "123K", 1e6 -> "1M".
-- Values are floored so the display never shows more than the player owns.
function Format.short(value: number?): string
	local n = tonumber(value) or 0
	local sign = if n < 0 then "-" else ""
	n = math.abs(n)
	if n < 1000 then
		return sign .. tostring(math.floor(n))
	end
	local tier = math.floor(math.log10(n) / 3)
	local scaled = n / 10 ^ (tier * 3)
	-- guard against log10 rounding at exact powers of ten
	if scaled >= 1000 then
		tier += 1
		scaled /= 1000
	elseif scaled < 1 then
		tier -= 1
		scaled *= 1000
	end
	if tier >= #SUFFIXES then
		return sign .. string.format("%.2e", n)
	end
	local text
	if scaled >= 100 then
		text = tostring(math.floor(scaled))
	elseif scaled >= 10 then
		text = trimZeros(string.format("%.1f", math.floor(scaled * 10) / 10))
	else
		text = trimZeros(string.format("%.2f", math.floor(scaled * 100) / 100))
	end
	return sign .. text .. SUFFIXES[tier + 1]
end

-- 1234567 -> "1 234 567"
function Format.full(value: number?): string
	local text = tostring(math.floor(tonumber(value) or 0))
	local sign = ""
	if string.sub(text, 1, 1) == "-" then
		sign = "-"
		text = string.sub(text, 2)
	end
	local out = string.reverse((string.gsub(string.reverse(text), "(%d%d%d)", "%1 ")))
	out = (string.gsub(out, "^ ", ""))
	return sign .. out
end

-- Multiplier: 1.5 -> "1.5", 2 -> "2", 1.25 -> "1.25"
function Format.multiplier(value: number): string
	return trimZeros(string.format("%.2f", value))
end

-- Countdown: 75 -> "1:15", 3725 -> "1:02:05"
function Format.clock(seconds: number): string
	local total = math.max(0, math.ceil(seconds))
	local hours = math.floor(total / 3600)
	local minutes = math.floor(total % 3600 / 60)
	local secs = total % 60
	if hours > 0 then
		return string.format("%d:%02d:%02d", hours, minutes, secs)
	end
	return string.format("%d:%02d", minutes, secs)
end

-- Duration in words: 300 -> "5 min", 5400 -> "1 h 30", 45 -> "45 s"
function Format.duration(seconds: number): string
	local total = math.max(0, math.floor(seconds))
	if total < 60 then
		return total .. " s"
	elseif total < 3600 then
		return math.floor(total / 60) .. " min"
	end
	local hours = math.floor(total / 3600)
	local minutes = math.floor(total % 3600 / 60)
	if minutes == 0 then
		return hours .. " h"
	end
	return string.format("%d h %02d", hours, minutes)
end

-- Percentage with one decimal when useful: 0.3 -> "30%", 0.025 -> "2.5%"
function Format.percent(ratio: number): string
	local value = ratio * 100
	if value >= 10 or value == math.floor(value) then
		return string.format("%d%%", math.floor(value + 0.5))
	end
	return trimZeros(string.format("%.1f", value)) .. "%"
end

return Format
