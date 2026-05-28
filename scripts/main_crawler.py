"""
主采集脚本 - 整合所有爬虫，生成历史数据，输出到docs/data/
"""

import json
import os
import sys
from datetime import datetime

# 确保scripts目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from steam_crawler import crawl_steam
from chaoziran_crawler import crawl_chaoziran


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "data")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_history(steam_data, history_path):
    """将当日数据追加到历史记录（用于趋势图）"""
    history = load_json(history_path)
    today = datetime.now().strftime("%Y-%m-%d")

    for name, data in steam_data.items():
        if name not in history:
            history[name] = []

        spy = data.get("steamspy") or {}
        reviews = data.get("reviews") or {}

        entry = {
            "date": today,
            "ccu": spy.get("ccu", 0),
            "positive_rate": reviews.get("positive_rate", spy.get("positive_rate", 0)),
            "total_reviews": reviews.get("total_reviews", spy.get("positive", 0) + spy.get("negative", 0)),
        }

        # 避免同一天重复追加
        if history[name] and history[name][-1]["date"] == today:
            history[name][-1] = entry
        else:
            history[name].append(entry)

        # 保留最近30天
        history[name] = history[name][-30:]

    save_json(history, history_path)
    return history


def main():
    print("=" * 50)
    print(f"品类情报看板 - 数据采集开始 {datetime.now().isoformat()}")
    print("=" * 50)

    # 1. 采集Steam数据
    print("\n[1/2] 采集Steam数据...")
    try:
        steam_data = crawl_steam()
        save_json(steam_data, os.path.join(DATA_DIR, "steam_data.json"))
        print("   Steam数据采集完成")
    except Exception as e:
        print(f"   Steam数据采集失败: {e}")
        steam_data = {}

    # 2. 采集超自然行动组数据
    print("\n[2/2] 采集超自然行动组数据...")
    try:
        czr_data = crawl_chaoziran()
        save_json(czr_data, os.path.join(DATA_DIR, "chaoziran_data.json"))
        print("   超自然行动组数据采集完成")
    except Exception as e:
        print(f"   超自然行动组数据采集失败: {e}")
        czr_data = {}

    # 3. 更新历史数据
    print("\n[3/3] 更新历史数据...")
    history_path = os.path.join(DATA_DIR, "history.json")
    history = update_history(steam_data, history_path)
    print(f"   历史数据已更新（{len(history)}个游戏）")

    # 4. 输出摘要
    print("\n" + "=" * 50)
    print("采集摘要:")
    print("-" * 30)

    for name, data in steam_data.items():
        spy = data.get("steamspy") or {}
        reviews = data.get("reviews") or {}
        ccu = spy.get("ccu", "?")
        rate = reviews.get("positive_rate", spy.get("positive_rate", "?"))
        print(f"  {name}: 在线{ccu} | 好评率{rate}%")

    if czr_data.get("chaoziran"):
        czr = czr_data["chaoziran"]
        updates_count = len(czr.get("bwiki_updates", []))
        news_count = len(czr.get("official_news", []))
        print(f"  超自然行动组: 更新公告{updates_count}条 | 官网新闻{news_count}条")

    print("=" * 50)
    print(f"采集完成 {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
