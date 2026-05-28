"""
超自然行动组数据爬虫 - 采集更新公告 + TapTap数据
数据源：BWIKI更新公告页、TapTap应用页、官网
"""

import json
import re
import urllib.request
import urllib.error
import time
from datetime import datetime


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


def fetch_json(url, retries=3):
    """带重试的JSON请求"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "HorrorIntelDashboard/1.0 (research bot)"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [FAIL] {url}: {e}")
                return None


def get_bwiki_updates():
    """从BWIKI获取超自然行动组更新公告"""
    url = "https://wiki.biligame.com/chaoziran/%E6%9B%B4%E6%96%B0%E5%85%AC%E5%91%8A"
    html = fetch_html(url)
    if not html:
        return []

    updates = []
    # 匹配更新公告标题（BWIKI的标题结构）
    # 尝试提取 h2/h3 标题和日期
    title_pattern = re.compile(r'<h[23][^>]*>.*?<span[^>]*>([^<]+)</span>', re.DOTALL)
    matches = title_pattern.findall(html)

    for match in matches[:10]:  # 最近10条
        title = match.strip()
        if title and "更新" in title or "公告" in title or "版本" in title or "活动" in title:
            updates.append({
                "title": title,
                "source": "BWIKI",
            })

    # 如果正则没匹配到，尝试另一种模式
    if not updates:
        alt_pattern = re.compile(r'<a[^>]*href="[^"]*"[^>]*>([^<]*(?:更新|公告|版本|活动)[^<]*)</a>', re.IGNORECASE)
        matches = alt_pattern.findall(html)
        for match in matches[:10]:
            title = match.strip()
            if title:
                updates.append({
                    "title": title,
                    "source": "BWIKI",
                })

    return updates


def get_taptap_data():
    """获取TapTap超自然行动组数据"""
    app_id = 714123
    # 尝试新版API
    urls = [
        f"https://www.taptap.cn/webapiv2/app/v2/detail?id={app_id}&plat=android",
        f"https://www.taptap.cn/webapiv2/app/v2/detail?id={app_id}",
        f"https://api.taptap.cn/webapiv2/app/v2/detail?id={app_id}&plat=android",
    ]
    for url in urls:
        data = fetch_json(url)
        if data and "data" in data:
            app_info = data["data"]
            return {
                "name": app_info.get("name", ""),
                "score": app_info.get("score", 0),
                "rating_count": app_info.get("rating_count", 0),
                "download_count": app_info.get("download_count", 0),
                "fans_count": app_info.get("fans_count", 0),
                "summary": app_info.get("summary", ""),
                "developer": app_info.get("developer", ""),
                "category": app_info.get("category", ""),
                "tags": [t.get("name", "") for t in app_info.get("tags", [])],
                "icon": app_info.get("icon", ""),
                "screenshots": [s.get("url", "") for s in app_info.get("screenshots", [])[:3]],
            }

    # API失败则从网页版抓取
    html = fetch_html(f"https://www.taptap.cn/app/{app_id}")
    if html:
        import re
        score_match = re.search(r'"score"\s*:\s*([\d.]+)', html)
        rating_match = re.search(r'"rating_count"\s*:\s*(\d+)', html)
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', html)
        return {
            "name": name_match.group(1) if name_match else "",
            "score": float(score_match.group(1)) if score_match else 0,
            "rating_count": int(rating_match.group(1)) if rating_match else 0,
            "source": "webpage_fallback",
        }

    print("  [WARN] TapTap数据采集失败")
    return None


def get_official_news():
    """从官网获取新闻"""
    url = "https://czrxdzgame.com/news"
    html = fetch_html(url)
    if not html:
        return []

    news_items = []
    # 尝试提取新闻标题和链接
    link_pattern = re.compile(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*(?:更新|公告|版本|活动|新|优化|修复)[^<]*)</a>', re.IGNORECASE)
    matches = link_pattern.findall(html)

    for href, title in matches[:10]:
        title = title.strip()
        if title:
            news_items.append({
                "title": title,
                "url": href if href.startswith("http") else f"https://czrxdzgame.com{href}",
                "source": "官网",
            })

    return news_items


def get_tomb_busters_info():
    """获取海外版Tomb Busters基础信息"""
    # 这部分主要通过搜索API或已知数据填充
    return {
        "name": "Tomb Busters",
        "regions": ["美国", "日本", "韩国"],
        "launch_date": "2026-05-27",
        "platforms": ["iOS", "Android", "PC"],
        "note": "巨人网络海外发行，港澳台试点已进入免费榜前三",
    }


def crawl_chaoziran():
    """主爬虫：采集超自然行动组全部数据"""
    print("[超自然行动组] 采集BWIKI更新公告...")
    bwiki_updates = get_bwiki_updates()
    print(f"  获取到 {len(bwiki_updates)} 条更新公告")

    time.sleep(2)

    print("[超自然行动组] 采集TapTap数据...")
    taptap_data = get_taptap_data()

    time.sleep(2)

    print("[超自然行动组] 采集官网新闻...")
    official_news = get_official_news()
    print(f"  获取到 {len(official_news)} 条官网新闻")

    result = {
        "chaoziran": {
            "bwiki_updates": bwiki_updates,
            "taptap": taptap_data,
            "official_news": official_news,
            "tomb_busters": get_tomb_busters_info(),
            "crawled_at": datetime.now().isoformat(),
        }
    }

    return result


if __name__ == "__main__":
    data = crawl_chaoziran()
    output_path = "data/chaoziran_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n超自然行动组数据已保存到 {output_path}")
