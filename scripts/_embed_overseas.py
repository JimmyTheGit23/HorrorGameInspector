# -*- coding: utf-8 -*-
"""将 chaoziran_overseas.json 嵌入 chaoziran_data.json 的 chaoziran.overseas 块"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"c:\Users\alucardzhou\WorkBuddy\20260527101502\horror-intel-dashboard"
MAIN = BASE + r"\docs\data\chaoziran_data.json"
OVERSEAS = BASE + r"\docs\data\chaoziran_overseas.json"

main = json.load(open(MAIN, encoding="utf-8"))
overseas = json.load(open(OVERSEAS, encoding="utf-8"))
main["chaoziran"]["overseas"] = overseas
with open(MAIN, "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=2)
print("embedded overseas block: google_play=%s, youtube=%d, crawled_at=%s" % (
    overseas.get("google_play", {}).get("rating"),
    len(overseas.get("youtube", [])),
    overseas.get("crawled_at"),
))
