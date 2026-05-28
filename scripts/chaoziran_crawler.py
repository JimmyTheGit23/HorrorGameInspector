"""
超自然行动组数据爬虫 - 采集更新公告 + TapTap数据 + 官网新闻
数据源：BWIKI更新公告页、TapTap网页版、官网
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error
import time
from datetime import datetime


def fetch_html(url, retries=3):
    """带重试的HTML请求"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://wiki.biligame.com/",
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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
    title_pattern = re.compile(r'<h[23][^>]*>.*?<span[^>]*>([^<]+)</span>', re.DOTALL)
    matches = title_pattern.findall(html)

    for match in matches[:10]:
        title = match.strip()
        if title and ("更新" in title or "公告" in title or "版本" in title or "活动" in title):
            updates.append({
                "title": title,
                "source": "BWIKI",
            })

    # 备用模式
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
    """从TapTap网页版提取超自然行动组数据（API已404，改用网页解析）"""
    app_id = 714123
    html = fetch_html(f"https://www.taptap.cn/app/{app_id}")
    if not html:
        print("  [WARN] TapTap网页版获取失败")
        return None

    result = {
        "app_id": app_id,
        "source": "taptap_webpage",
    }

    # 1. 从__NUXT_DATA__解析Nuxt3引用序列化
    payload_match = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if payload_match:
        try:
            payload = json.loads(payload_match.group(1))
            # 遍历dict找关键key的引用
            for i, item in enumerate(payload):
                if isinstance(item, dict):
                    for key in ["score", "rating", "fans_count", "download_count", "rating_count",
                                "review_count", "follow_count", "install_count"]:
                        if key in item:
                            ref_idx = item[key]
                            if isinstance(ref_idx, int) and 0 <= ref_idx < len(payload):
                                val = payload[ref_idx]
                                if isinstance(val, (int, float, str)):
                                    result[key] = val

                # 提取标签
                if isinstance(item, str):
                    tag_url = re.search(r'tag=([^"%&]+)', item)
                    if tag_url:
                        tag_name = urllib.parse.unquote(tag_url.group(1))
                        if tag_name not in result.get("tags", []):
                            result.setdefault("tags", []).append(tag_name)
        except (json.JSONDecodeError, IndexError):
            pass

    # 2. 从meta标签补充描述
    desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
    if desc:
        result["description"] = desc.group(1)

    # 3. 评分补充（多种来源验证）
    # 方法A: 页面显示的评分文本
    score_text = re.search(r'(\d\.\d)\s*(?:分|/10)', html)
    if score_text:
        result["score_display"] = float(score_text.group(1))

    # 方法B: aggregateRating
    ld = re.search(r'"aggregateRating"[^}]*"ratingValue"\s*:\s*"?([\d.]+)"?', html)
    if ld:
        result["rating_value"] = float(ld.group(1))

    # 如果Nuxt payload的score是引用索引（>10），用正则结果替代
    if "score" in result:
        s = result["score"]
        if isinstance(s, (int, float)) and s > 10:
            result.pop("score", None)

    # 确保有评分
    if "score" not in result:
        if "score_display" in result:
            result["score"] = result["score_display"]
        elif "rating_value" in result:
            result["score"] = result["rating_value"]

    # 4. 关注/下载数（中文格式）
    fans_text = re.search(r'([\d.]+)\s*万?\s*人关注', html)
    if fans_text:
        val = fans_text.group(1)
        result["fans_text"] = f"{val}万关注"

    dl_text = re.search(r'([\d.]+)\s*万?\s*次下载', html)
    if dl_text:
        val = dl_text.group(1)
        result["download_text"] = f"{val}万下载"

    return result


def get_official_news():
    """从官网获取新闻（官网为JS渲染，用chaoziran.com替代）"""
    # 官网首页可能有服务端渲染的部分
    url = "https://www.chaoziran.com/"
    html = fetch_html(url)
    if not html:
        return []

    news_items = []

    # 尝试提取新闻链接
    link_pattern = re.compile(
        r'<a[^>]*href="([^"]*)"[^>]*>([^<]*(?:更新|公告|版本|活动|新|优化|修复|联动|赛季|限时)[^<]*)</a>',
        re.IGNORECASE
    )
    matches = link_pattern.findall(html)

    seen = set()
    for href, title in matches[:15]:
        title = title.strip()
        if title and title not in seen:
            seen.add(title)
            news_items.append({
                "title": title,
                "url": href if href.startswith("http") else f"https://www.chaoziran.com{href}",
                "source": "官网",
            })

    # 备用: 搜索更多新闻结构
    if not news_items:
        # 搜索标题标签
        heading_pattern = re.compile(r'<h[23][^>]*>([^<]*(?:更新|公告|活动|版本)[^<]*)</h[23]>', re.IGNORECASE)
        matches = heading_pattern.findall(html)
        for title in matches[:10]:
            title = title.strip()
            if title and title not in seen:
                seen.add(title)
                news_items.append({
                    "title": title,
                    "source": "官网",
                })

    return news_items


def get_tomb_busters_info():
    """获取海外版Tomb Busters基础信息"""
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
    if taptap_data:
        score = taptap_data.get("score", "?")
        fans = taptap_data.get("fans_count", "?")
        print(f"  TapTap评分: {score}, 关注数: {fans}")

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
