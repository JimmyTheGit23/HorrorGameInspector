# -*- coding: utf-8 -*-
"""将 git HEAD 中因 SSL 失败丢失的旧维度合并回 chaoziran_overseas.json"""
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"c:\Users\alucardzhou\WorkBuddy\20260527101502\horror-intel-dashboard"
PATH = BASE + r"\docs\data\chaoziran_overseas.json"

new = json.load(open(PATH, encoding="utf-8"))
old_raw = subprocess.run(
    ["git", "show", "HEAD:docs/data/chaoziran_overseas.json"],
    capture_output=True, cwd=BASE,
).stdout.decode("utf-8")
old = json.loads(old_raw)

restored = []
# 仅当新值为空/缺失而旧值有数据时回填
if not new.get("google_play") and old.get("google_play"):
    new["google_play"] = old["google_play"]
    restored.append("google_play(rating=%s, review_count=%s)" % (
        old["google_play"].get("rating"), old["google_play"].get("review_count")))

new_gpr = new.get("google_play_reviews") or []
old_gpr = old.get("google_play_reviews") or []
if not new_gpr and old_gpr:
    new["google_play_reviews"] = old_gpr
    restored.append("google_play_reviews(%d items)" % len(old_gpr))

new_yt = new.get("youtube") or []
old_yt = old.get("youtube") or []
if not new_yt and old_yt:
    new["youtube"] = old_yt
    restored.append("youtube(%d videos)" % len(old_yt))

if restored:
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)
    print("restored:", ", ".join(restored))
else:
    print("nothing to restore")
