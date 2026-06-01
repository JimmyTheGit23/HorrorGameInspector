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


def get_taptap_forum_posts(app_id=714123, max_posts=10, official_only=False):
    """从TapTap论坛获取帖子列表（解析HTML中的moment链接+标题span+NUXT_DATA）"""
    url = f"https://www.taptap.cn/app/{app_id}/topic"
    if official_only:
        url += "?type=official"
    html = fetch_html(url)
    if not html:
        return []

    posts = []
    seen_ids = set()
    source_label = "TapTap官方" if official_only else "TapTap论坛"

    # 方法1: 从 __NUXT_DATA__ 解析帖子标题（最可靠）
    nuxt_match = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if nuxt_match:
        try:
            payload = json.loads(nuxt_match.group(1))
            # 过滤非帖子内容的元数据关键词
            meta_keywords = {'徽章', '粉丝', '关注', '帖子', '官方账号', '万人拥有',
                           '人拥有', '官方', '制作人', '论坛', 'TapTap', '平台',
                           '万关注', '万帖子', '《超自然行动组》', '版主', '玩家版主',
                           '该游戏已下架', '多人组队', '欢乐恐怖游戏', '已下架'}
            for item in payload:
                if isinstance(item, str) and 15 < len(item) < 80:
                    # 过滤掉明显的非帖子内容
                    if item in ['默认排序', '最新排序', '最热排序']:
                        continue
                    # 过滤包含元数据关键词的
                    if any(kw in item for kw in meta_keywords):
                        continue
                    # 过滤纯数字+单位的
                    if re.match(r'^[\d.]+\s*[万亿]?\s*\w+$', item):
                        continue
                    # 过滤用户名（无标点、无句号的短文本）
                    if len(item) < 20 and '，' not in item and '。' not in item and '！' not in item:
                        continue
                    # 帖子标题特征：包含中文且不是URL
                    if re.search(r'[\u4e00-\u9fff]', item) and not item.startswith('http'):
                        if item not in seen_ids:
                            seen_ids.add(item)
                            posts.append({
                                "title": item,
                                "source": source_label,
                                "url": f"https://www.taptap.cn/app/{app_id}/topic{'?type=official' if official_only else ''}",
                            })
                            if len(posts) >= max_posts:
                                break
        except (json.JSONDecodeError, IndexError):
            pass

    # 方法2: 从moment链接附近找标题（如果方法1没拿到足够数据）
    if len(posts) < max_posts:
        for m in re.finditer(r'href="(/moment/(\d+))"', html):
            moment_id = m.group(2)
            if moment_id in seen_ids:
                continue
            seen_ids.add(moment_id)

            # 扩大搜索范围到前后1000字符
            start = max(0, m.start() - 500)
            end = min(len(html), m.end() + 1000)
            context = html[start:end]

            # 尝试多种title匹配模式
            title_match = None
            for pattern in [
                r'<span[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</span>',
                r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
                r'data-testid="moment-title"[^>]*>([^<]+)',
            ]:
                title_match = re.search(pattern, context)
                if title_match:
                    break

            if title_match:
                title = title_match.group(1).strip()
                if title in ['默认排序', '最新排序', '最热排序']:
                    continue
                posts.append({
                    "title": title,
                    "source": source_label,
                    "url": f"https://www.taptap.cn{m.group(1)}",
                })
                if len(posts) >= max_posts:
                    break

    # 去重（NUXT_DATA可能包含截断和完整版本）
    unique_posts = []
    seen_titles = set()
    for p in posts:
        # 用前缀去重：如果已有标题是当前标题的前缀，跳过当前
        skip = False
        for t in seen_titles:
            if p["title"].startswith(t) or t.startswith(p["title"]):
                # 保留更长的那个
                if len(t) > len(p["title"]):
                    skip = True
                    break
        if not skip and p["title"] not in seen_titles:
            seen_titles.add(p["title"])
            unique_posts.append(p)

    return unique_posts[:max_posts]


def get_tieba_hot_posts(kw="超自然行动组", max_posts=10):
    """从百度贴吧获取热帖（贴吧反爬严格，返回基于社区观察的热门话题）"""
    tieba_url = f"https://tieba.baidu.com/f?kw={urllib.parse.quote(kw)}"
    # 贴吧直接爬取会被403，基于社区观察提供热门话题关键词
    hot_topics = [
        {"topic": "找固玩/组队", "note": "找队友、找兔子、找四队"},
        {"topic": "外挂举报", "note": "卡音响、龙珠、瞬移等外挂讨论"},
        {"topic": "摸金攻略", "note": "龙宫、精绝古城等地图攻略"},
        {"topic": "皮肤/时装", "note": "新皮肤爆料、穿搭分享"},
        {"topic": "版本讨论", "note": "更新内容、平衡性讨论"},
        {"topic": "BUG反馈", "note": "游戏bug、优化建议"},
    ]
    return {
        "source": "百度贴吧",
        "url": tieba_url,
        "note": "贴吧反爬严格，显示基于社区观察的热门话题",
        "hot_posts": [],
        "hot_topics": hot_topics,
    }


def simple_sentiment(title):
    """简易情感分析（基于关键词）"""
    negative_words = ['垃圾', '退坑', '坑', '破防', '怒', '骂', '垃圾', '氪金', '骗', '差', '烂',
                      '掉', '崩', '卡', 'bug', 'Bug', 'BUG', '恨', '惨', '亏', '坑爹', '离谱',
                      '黑', '号价', '出号', '退游', '不玩了', '骂了', '举报', '投诉']
    positive_words = ['好评', '喜欢', '赞', '棒', '开心', '福利', '免费', '爽', '良心', '精彩',
                      '厉害', '好看', '漂亮', '帅', '牛', '白嫖', '终于', '等到了']
    neg_score = sum(1 for w in negative_words if w in title)
    pos_score = sum(1 for w in positive_words if w in title)
    if neg_score > pos_score:
        return "negative"
    elif pos_score > neg_score:
        return "positive"
    return "neutral"


def get_tomb_busters_info():
    """Tomb Busters 海外版数据 - 目前手动维护"""
    return {
        "name": "Tomb Busters",
        "launch_date": "2026-05-27",
        "platforms": ["iOS", "Android", "PC"],
        "regions": ["美国", "日本", "韩国", "港澳台"],
        "app_store_rating": 4.5,
        "website": "https://www.tombbusters.net/",
        "note": "数据需手动更新"
    }


def filter_bwiki_updates(updates):
    """过滤BWIKI中的导航标题等脏数据"""
    skip_titles = {'游戏内公告', 'WIKI站公告', 'BWIKI', ''}
    filtered = []
    seen = set()
    for u in updates:
        title = u.get('title', '').strip()
        if title in skip_titles or title in seen:
            continue
        seen.add(title)
        filtered.append(u)
    return filtered


def crawl_chaoziran():
    """主爬虫：采集超自然行动组全部数据"""
    print("[超自然行动组] 采集BWIKI更新公告...")
    bwiki_updates = get_bwiki_updates()
    bwiki_updates = filter_bwiki_updates(bwiki_updates)
    print(f"  获取到 {len(bwiki_updates)} 条BWIKI更新公告（已过滤脏数据）")

    time.sleep(2)

    print("[超自然行动组] 采集TapTap官方论坛公告...")
    taptap_official = get_taptap_forum_posts(official_only=True, max_posts=10)
    print(f"  获取到 {len(taptap_official)} 条TapTap官方公告")

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

    time.sleep(2)

    print("[超自然行动组] 采集TapTap论坛帖子...")
    taptap_forum = get_taptap_forum_posts()
    print(f"  获取到 {len(taptap_forum)} 条论坛帖子")

    print("[超自然行动组] 采集百度贴吧数据...")
    tieba_data = get_tieba_hot_posts()
    print(f"  贴吧数据: {tieba_data['note']}")

    # 为论坛帖子添加情感标签
    for post in taptap_forum:
        post["sentiment"] = simple_sentiment(post["title"])

    # 优先使用TapTap官方论坛公告作为更新公告数据源
    update_announcements = taptap_official if taptap_official else bwiki_updates
    if taptap_official:
        print(f"  [SOURCE] 使用TapTap官方论坛公告({len(taptap_official)}条)")
    elif bwiki_updates:
        print(f"  [SOURCE] 使用BWIKI更新公告({len(bwiki_updates)}条)")

    result = {
        "chaoziran": {
            "bwiki_updates": update_announcements,
            "taptap": taptap_data,
            "official_news": official_news,
            "community": {
                "taptap_forum": taptap_forum,
                "tieba": tieba_data,
            },
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
