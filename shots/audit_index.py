import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PATH = (r"C:\Users\seang\AppData\Local\Temp\claude\c--Users-seang-Zombie-game"
        r"\c650776f-bc63-4a89-a372-5111061ad61d\tasks\wlsxhlvpd.output")
raw = open(PATH, encoding="utf-8", errors="replace").read()
start = raw.rfind("[", 0, raw.find('"pillar"'))
data = json.loads(raw[start:raw.rfind("]") + 1])
full = {"THE VESSEL BUILDER", "FLIGHT / MAP INFORMATION DESIGN",
        "DOCKING & LANDING AS GAMEPLAY"}
for p in data:
    name = p["pillar"].upper()
    print("=" * 18, name, "=" * 18)
    print("VERDICT:", p["verdict"])
    for f in p["findings"]:
        print("  [%s/%s] %s" % (f["severity"][:4].upper(), f["effort"], f["title"]))
        if any(k in name for k in ("BUILDER", "FLIGHT", "DOCKING", "COLONY", "BASES")):
            print("      impact:", f["player_impact"])
            print("      fix:", f["fix"])
    print()
