# -*- coding: utf-8 -*-
"""对比 HEAD 与工作区的 chaoziran_data.json，输出变化摘要（自动化日常用）"""
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

raw = subprocess.run(
    ["git", "show", "HEAD:docs/data/chaoziran_data.json"],
    capture_output=True,
).stdout.decode("utf-8")
old = json.loads(raw)["chaoziran"]
new = json.load(open("../docs/data/chaoziran_data.json", encoding="utf-8"))["chaoziran"]


def fmt(t):
    return t.replace("\n", " ")[:44]


old_titles = [fmt(p["title"]) for p in old["bwiki_updates"]]
new_titles = [fmt(p["title"]) for p in new["bwiki_updates"]]
print("=== 新增 TapTap 官方帖 ===")
for t in new_titles:
    if t not in old_titles:
        print(" +", t)
print("=== 消失帖（新帖挤出/预期） ===")
for t in old_titles:
    if t not in new_titles:
        print(" -", t)

print("=== 指标 ===")
for k in ["fans_count", "review_count", "score"]:
    print(k, old.get("taptap", {}).get(k), "->", new.get("taptap", {}).get(k))

print("stock", old["stock_price"]["price"], "->", new["stock_price"]["price"],
      new["stock_price"]["change_pct"], "%")

cn_o = old["cn_app_store_rankings"]["cn"]
cn_n = new["cn_app_store_rankings"]["cn"]
for k in ["free_games", "grossing_overall", "grossing_games"]:
    print("CN", k, cn_o.get(k), "->", cn_n.get(k))

for r in ["us", "jp", "kr"]:
    ro = old["tomb_busters"]["regions_data"][r]
    rn = new["tomb_busters"]["regions_data"][r]
    print("TB", r, ro["rating"], ro["rating_count"], "->", rn["rating"], rn["rating_count"])

go = old.get("overseas", {}).get("google_play", {})
gn = new["overseas"]["google_play"]
print("GooglePlay", go.get("rating"), go.get("review_count"), "->", gn["rating"], gn["review_count"])

print("tracker:", [t["name"] for t in old["new_content_tracker"]],
      "->", [t["name"] for t in new["new_content_tracker"]])
print("forum posts:", len(old["community"]["taptap_forum"]),
      "->", len(new["community"]["taptap_forum"]))
print("youtube:", len(old.get("overseas", {}).get("youtube", [])),
      "->", len(new["overseas"]["youtube"]))
