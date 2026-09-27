"""Runs BrainrotUI outside Roblox: the real server + client code inside a mock of
the Roblox API, a scripted play session with checks, the installer twice, and
(optionally) approximate screenshots of the interface.

    python BrainrotFighter/UI/tools/run_checks.py --definitions globalTypes.d.luau [--render]

Needs: the `luau` CLI (or LUAU=/path/to/luau), the Roblox type definitions used by
luau-lsp (globalTypes.d.luau), and for --render: Pillow, numpy, the fonts
Fredoka One + Luckiest Guy in tools/.cache/fonts and Noto Color Emoji.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
SRC = os.path.join(UI, "src")
CACHE = os.path.join(HERE, ".cache")


def lua_string(text):
    level = 1
    while ("]" + "=" * level + "]") in text:
        level += 1
    eq = "=" * level
    return f"[{eq}[\n{text}]{eq}]"


def extract_api(definitions):
    """classes.luau / enums.luau: every class with its properties and methods, every enum."""
    lines = open(definitions, encoding="utf-8").read().split("\n")
    classes, enums = {}, {}
    current, enum = None, None
    for line in lines:
        m = re.match(r"^declare extern type (\w+)(?: extends (\w+))? with", line)
        if m:
            name, parent = m.group(1), m.group(2)
            e = re.match(r"^Enum(\w+)_INTERNAL$", name)
            if e and parent == "Enum":
                enum, current = [], None
                enums[e.group(1)] = enum
            else:
                enum = None
                current = {"super": parent, "props": {}, "methods": []}
                classes[name] = current
            continue
        if line.startswith("end"):
            current, enum = None, None
            continue
        if enum is not None:
            m = re.match(r"^\t(\w+): Enum\w+$", line)
            if m:
                enum.append(m.group(1))
        elif current is not None:
            m = re.match(r"^\t\t?function (\w+)\(", line)
            if m:
                current["methods"].append(m.group(1))
                continue
            m = re.match(r"^\t(\w+): (.+)$", line)
            if m:
                current["props"][m.group(1)] = m.group(2).strip()
    q = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    out = ["return {"]
    for name, c in classes.items():
        props = ", ".join(f"[{q(k)}] = {q(v)}" for k, v in c["props"].items())
        methods = ", ".join(f"[{q(k)}] = true" for k in c["methods"])
        sup = q(c["super"]) if c["super"] else "nil"
        out.append(f"\t[{q(name)}] = {{ super = {sup}, props = {{ {props} }}, methods = {{ {methods} }} }},")
    out.append("}")
    classes_lua = "\n".join(out)
    enums_lua = "return {\n" + "\n".join(f"\t{n} = {{ " + ", ".join(q(i) for i in items) + " },"
                                           for n, items in enums.items()) + "\n}"
    return classes_lua, enums_lua


def tree(path, name):
    full = os.path.join(SRC, path)
    if os.path.isdir(full):
        files = sorted(os.listdir(full))
        init = [f for f in files if f.startswith("init.")]
        if init:
            cls = "Script" if ".server." in init[0] else "LocalScript" if ".client." in init[0] else "ModuleScript"
            head = f'{{ name = "{name}", className = "{cls}", source = {lua_string(open(os.path.join(full, init[0]), encoding="utf-8").read())}, children = {{'
        else:
            head = f'{{ name = "{name}", className = "Folder", children = {{'
        kids = [tree(os.path.join(path, f), f.split(".")[0]) for f in files if not f.startswith("init.")]
        return head + ",\n".join(kids) + "} }"
    return f'{{ name = "{name}", className = "ModuleScript", source = {lua_string(open(full, encoding="utf-8").read())} }}'


def run(luau, parts, name):
    path = os.path.join(CACHE, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(parts))
    result = subprocess.run([luau, path], capture_output=True, text=True, timeout=600)
    return result.returncode, result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--definitions", required=True, help="Roblox globalTypes.d.luau (luau-lsp)")
    parser.add_argument("--render", action="store_true", help="also render screenshots into ../previews")
    args = parser.parse_args()
    luau = os.environ.get("LUAU", "luau")
    os.makedirs(CACHE, exist_ok=True)

    classes_lua, enums_lua = extract_api(args.definitions)
    api = [f"CLASSES = (function()\n{classes_lua}\nend)()", f"ENUMS = (function()\n{enums_lua}\nend)()"]
    mock = open(os.path.join(HERE, "mock.luau"), encoding="utf-8").read()

    sources = ("TREE = {\n shared = " + tree("ReplicatedStorage/BrainrotUI", "BrainrotUI")
               + ",\n server = " + tree("ServerScriptService/BrainrotUIServer", "BrainrotUIServer")
               + ",\n client = " + tree("StarterPlayerScripts/BrainrotUIClient", "BrainrotUIClient") + "\n}")
    scenario = open(os.path.join(HERE, "scenario.luau"), encoding="utf-8").read()
    code, log = run(luau, api + [sources, mock, scenario], "session.luau")
    with open(os.path.join(CACHE, "session.log"), "w", encoding="utf-8") as handle:
        handle.write(log)
    for line in log.splitlines():
        if not line.startswith("SNAP "):
            print(line[:300])
    ok = code == 0 and re.search(r"CHECKS passed=\d+ failed=0", log) is not None

    installer = open(os.path.join(UI, "BrainrotUI_Install.lua"), encoding="utf-8").read()
    installer_test = open(os.path.join(HERE, "installer_test.luau"), encoding="utf-8").read()
    code2, log2 = run(luau, api + [mock, "INSTALLER = " + lua_string(installer), installer_test], "installer.luau")
    print("installer:", "OK" if "INSTALLER OK" in log2 else log2[-2000:])
    ok = ok and code2 == 0 and "INSTALLER OK" in log2

    if args.render:
        sys.path.insert(0, HERE)
        import render
        render.render_log(os.path.join(CACHE, "session.log"), os.path.join(UI, "previews"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
