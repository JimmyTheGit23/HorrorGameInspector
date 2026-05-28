"""
Steam数据爬虫 - 采集恐怖撤离/合作恐怖游戏数据
数据源：Steam Store API + Steam Review API + Steam Player Count API
"""

import json
import urllib.request
import urllib.error
import time
from datetime import datetime

# 追踪的Steam游戏列表
STEAM_GAMES = {
    "R.E.P.O.": 3241660,
    "Lethal Company": 1966720,
    "Phasmophobia": 739630,
    "Content Warning": 2881650,
    "FEEDERS": 4408510,
}


def fetch_json(url, retries=3):
    """带重试的JSON请求"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [FAIL] {url}: {e}")
                return None


def fetch_html(url, retries=3):
    """带重试的HTML请求"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [FAIL] {url}: {e}")
                return None


def get_steam_app_data(appid):
    """从Steam Store API获取游戏详情"""
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=cn&l=schinese"
    data = fetch_json(url)
    if not data or str(appid) not in data:
        return None

    app_data = data[str(appid)]
    if not app_data.get("success"):
        return None

    info = app_data["data"]
    return {
        "name": info.get("name", ""),
        "type": info.get("type", ""),
        "short_description": info.get("short_description", ""),
        "header_image": info.get("header_image", ""),
        "developers": info.get("developers", []),
        "publishers": info.get("publishers", []),
        "price": info.get("price_overview", {}).get("final_formatted", "免费"),
        "release_date": info.get("release_date", {}).get("date", ""),
        "metacritic": info.get("metacritic", {}).get("score", None),
        "recommendations": info.get("recommendations", {}).get("total", 0),
        "platforms": info.get("platforms", {}),
        "categories": [c["description"] for c in info.get("categories", [])],
        "genres": [g["description"] for g in info.get("genres", [])],
    }


def get_steam_current_players(appid):
    """从Steam社区页面获取当前在线玩家数"""
    url = f"https://store.steampowered.com/app/{appid}/"
    html = fetch_html(url)
    if not html:
        return 0

    # Steam商店页面中包含当前在线人数
    import re
    # 匹配 "当前有 X 名玩家在线" 或类似的格式
    pattern = re.compile(r'(\d[\d,]+)\s*(?:人在线|playing now|In-Game|online)', re.IGNORECASE)
    match = pattern.search(html)
    if match:
        return int(match.group(1).replace(",", ""))

    # 备用: 从SteamDB的API获取
    return 0


def get_steam_reviews(appid):
    """从Steam Review API获取评测摘要"""
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&purchase_type=all&language=schinese&review_type=all"
    data = fetch_json(url)
    if not data or not data.get("success"):
        url = f"https://store.steampowered.com/appreviews/{appid}?json=1&purchase_type=all&language=all&review_type=all"
        data = fetch_json(url)
    if not data or not data.get("success"):
        return None

    summary = data.get("query_summary", {})
    return {
        "total_reviews": summary.get("total_reviews", 0),
        "positive": summary.get("total_positive", 0),
        "negative": summary.get("total_negative", 0),
        "positive_rate": round(
            summary.get("total_positive", 0) / max(summary.get("total_reviews", 1), 1) * 100, 1
        ),
    }


def get_steamcharts_ccu(appid):
    """从SteamCharts获取当前在线人数"""
    # SteamCharts的搜索需要游戏slug，这里用另一种方式
    # 直接用Steam API的ISteamUserStats接口
    try:
        url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}"
        data = fetch_json(url)
        if data and data.get("response", {}).get("result") == 1:
            return data["response"].get("player_count", 0)
    except:
        pass
    return 0


def get_steamspy_data(appid):
    """从SteamSpy获取玩家数据(备用，可能403)"""
    url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    data = fetch_json(url)
    if not data:
        return None

    return {
        "owners_estimate": data.get("owners", "N/A"),
        "players_2weeks": data.get("players_2weeks", 0),
        "average_2weeks": data.get("average_2weeks", 0),
        "median_2weeks": data.get("median_2weeks", 0),
        "ccu": data.get("ccu", 0),
        "positive": data.get("positive", 0),
        "negative": data.get("negative", 0),
        "positive_rate": round(
            data.get("positive", 0) / max(data.get("positive", 0) + data.get("negative", 0), 1) * 100, 1
        ),
        "tags": dict(list(data.get("tags", {}).items())[:10]),
    }


def crawl_steam():
    """主爬虫：采集所有Steam游戏数据"""
    results = {}

    for name, appid in STEAM_GAMES.items():
        print(f"[Steam] 采集 {name} (appid: {appid})...")

        store_data = get_steam_app_data(appid)
        time.sleep(1.5)

        # 当前在线人数：优先Steam API，备用SteamSpy
        ccu = get_steamcharts_ccu(appid)
        time.sleep(1)

        # SteamSpy数据(可能失败)
        spy_data = get_steamspy_data(appid)
        time.sleep(1.5)

        # 如果Steam API拿到ccu但SteamSpy没拿到，用API的值
        if spy_data and ccu > 0:
            spy_data["ccu"] = ccu
        elif not spy_data and ccu > 0:
            spy_data = {"ccu": ccu}

        review_data = get_steam_reviews(appid)
        time.sleep(1.5)

        results[name] = {
            "appid": appid,
            "store": store_data,
            "steamspy": spy_data,
            "reviews": review_data,
            "ccu": ccu,
            "crawled_at": datetime.now().isoformat(),
        }
        print(f"   {name} 完成 (在线: {ccu})")

    return results


if __name__ == "__main__":
    data = crawl_steam()
    output_path = "data/steam_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSteam数据已保存到 {output_path}")
