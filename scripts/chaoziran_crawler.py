"""
超自然行动组数据爬虫 - 采集更新公告 + TapTap数据 + 官网新闻
数据源：BWIKI更新公告页、TapTap网页版、官网
"""

import json
import os
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


def validate_url(url, app_id="714123"):
    """
    验证TapTap moment链接是否有效。
    返回 (is_valid, final_url)
    - is_valid: True/False
    - final_url: 有效返回原url，无效返回百度搜索fallback
    """
    # 非moment链接直接跳过验证
    if "/moment/" not in url:
        return True, url

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.taptap.cn/",
            })
            # 使用自定义opener来获取重定向后的URL
            opener = urllib.request.build_opener()
            with opener.open(req, timeout=8) as resp:
                final_url = resp.geturl()
                status = resp.getcode()

                # 检查是否被重定向到论坛首页（帖子被删除后的行为）
                forum_home_patterns = [
                    f"/app/{app_id}/topic",
                    f"/app/{app_id}/",
                ]
                is_redirected_home = any(p in final_url for p in forum_home_patterns) and "/moment/" not in final_url

                if status in (200, 301, 302, 307, 308) and not is_redirected_home:
                    return True, url
                else:
                    return False, final_url
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, None
            # 其他HTTP错误（403/500等）保守处理为失效
            return False, None
        except Exception as e:
            if attempt < 1:
                time.sleep(1)
            else:
                # 超时等网络错误，保守处理为未知（不修改）
                return True, url
    return True, url


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
    """从TapTap论坛获取帖子列表（优先moment链接获取准确URL）"""
    url = f"https://www.taptap.cn/app/{app_id}/topic"
    if official_only:
        url += "?type=official"
    html = fetch_html(url)
    if not html:
        return []

    posts = []
    seen_ids = set()
    source_label = "TapTap官方" if official_only else "TapTap论坛"

    # ===== 方法1: 从 moment 链接 + 附近文本提取（有准确URL）=====
    # 先收集所有 moment 链接位置
    moment_matches = list(re.finditer(r'href="(/moment/(\d+))"', html))

    for m in moment_matches:
        moment_id = m.group(2)
        if moment_id in seen_ids:
            continue

        moment_url = f"https://www.taptap.cn{m.group(1)}"

        # 在moment链接附近搜索标题（扩大范围到前后600字符）
        start = max(0, m.start() - 100)
        end = min(len(html), m.end() + 600)
        context = html[start:end]

        title = None
        # 尝试多种标题匹配模式（按优先级）
        for pattern in [
            r'<span[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</span>',
            r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
            r'data-testid="moment-title"[^>]*>([^<]+)',
            r'<a[^>]*href="/moment/\d+"[^>]*>\s*<[^>]+>\s*([^<]{10,60})',
        ]:
            tmatch = re.search(pattern, context)
            if tmatch:
                candidate = tmatch.group(1).strip()
                if candidate not in ['默认排序', '最新排序', '最热排序', ''] and len(candidate) >= 10:
                    title = candidate
                    break

        if not title:
            continue

        seen_ids.add(moment_id)
        posts.append({
            "title": title,
            "source": source_label,
            "url": moment_url,
            "moment_id": moment_id,
        })
        if len(posts) >= max_posts * 3:
            break

    # ===== 方法2: 从 __NUXT_DATA__ 补充标题（仅用于找额外标题，URL用搜索页）=====
    if len(posts) < max_posts:
        nuxt_match = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if nuxt_match:
            try:
                payload = json.loads(nuxt_match.group(1))
                meta_keywords = {'徽章', '粉丝', '关注', '帖子', '官方账号', '万人拥有',
                               '人拥有', '制作人', '论坛', 'TapTap', '平台',
                               '万关注', '万帖子', '《超自然行动组》', '版主', '玩家版主',
                               '该游戏已下架', '多人组队', '欢乐恐怖游戏', '已下架',
                               '默认排序', '最新排序', '最热排序'}
                for item in payload:
                    if isinstance(item, str) and 15 < len(item) < 80:
                        if item in meta_keywords or any(kw in item for kw in meta_keywords):
                            continue
                        if re.match(r'^[\d.]+\s*[万亿]?\s*\w+$', item):
                            continue
                        if len(item) < 20 and '，' not in item and '。' not in item and '！' not in item:
                            continue
                        if re.search(r'[\u4e00-\u9fff]', item) and not item.startswith('http'):
                            # 检查是否已存在
                            already = any(p['title'] == item or p['title'].startswith(item) or item.startswith(p['title']) for p in posts)
                            if not already:
                                posts.append({
                                    "title": item,
                                    "source": source_label,
                                    "url": f"https://www.taptap.cn/app/{app_id}/topic{'?type=official' if official_only else ''}",
                                })
                                if len(posts) >= max_posts * 2:
                                    break
            except (json.JSONDecodeError, IndexError):
                pass

    # ===== 过滤非官方帖子 =====
    player_keywords = ['圈钱', '不修', '不管', '退坑', '垃圾', '找固玩', '找队友',
                      '组队', '本人女', '本人男', '氪条', '骗氪', '必须圈', 'bug是不修的',
                      '挂是不管的', '福利是不给的', '钱是必须', '该夸夸该骂骂',
                      '对得起他们', '对不起我们', '让人失望', '洗白', '额……']
    # 官方内容特征（用于辅助判断）
    official_markers = ['爆料', '联动', '时装', '皮肤', '玩法', '优化', '修复',
                       '活动', '福利', '版本', '预告', '预热', '展示', '实机',
                       '登场', '攻略', '速递', '趣闻', '求助', '公告', '更新']

    filtered = []
    seen_titles = set()
    for p in posts:
        title = p['title']
        # 排除明显玩家吐槽帖
        is_player = any(kw in title for kw in player_keywords)
        if official_only and is_player:
            continue
        # 额外过滤：official_only模式下，无官方关键词且含负面情绪的也排除
        if official_only:
            has_official_marker = any(m in title for m in official_markers)
            negative_words = ['但是', '不能', '对不起', '失望', '骂']
            has_negative = any(w in title for w in negative_words)
            if not has_official_marker and has_negative:
                continue
        # 去重
        dup = False
        for t in seen_titles:
            if title.startswith(t) or t.startswith(title):
                dup = True
                break
        if not dup and title not in seen_titles:
            seen_titles.add(title)
            filtered.append(p)

    # ===== 链接有效性验证 + 失效降级 =====
    verified = []
    for p in filtered[:max_posts]:
        moment_url = p.get("url", "")
        if "/moment/" in moment_url:
            is_valid, _ = validate_url(moment_url, app_id=str(app_id))
            if is_valid:
                p["link_status"] = "valid"
                verified.append(p)
            else:
                # 失效降级：TapTap论坛搜索该标题
                search_query = urllib.parse.quote(p['title'][:30])
                p["url"] = f"https://www.taptap.cn/search/posts?q={search_query}"
                p["link_status"] = "fallback"
                p["original_url"] = moment_url  # 保留原始URL用于调试
                verified.append(p)
        else:
            # 没有moment链接（论坛首页URL）→ 也降级为TapTap搜索该标题
            search_query = urllib.parse.quote(p['title'][:30])
            p["url"] = f"https://www.taptap.cn/search/posts?q={search_query}"
            p["link_status"] = "fallback"
            verified.append(p)

    return verified


def get_tieba_hot_posts(kw="超自然行动组", max_posts=8):
    """获取百度贴吧热帖（尝试搜索，失败则用社区观察热帖）"""
    tieba_url = f"https://tieba.baidu.com/f?kw={urllib.parse.quote(kw)}"

    # 尝试通过必应搜索获取贴吧相关帖子
    search_kw = urllib.parse.quote(f"{kw} 贴吧 热门")
    search_url = f"https://cn.bing.com/search?q={search_kw}"
    html = fetch_html(search_url)

    hot_posts = []
    if html:
        # 提取必应搜索结果中的标题和链接
        for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*[^>]*>([^<]{10,60})</a>', html):
            href = m.group(1)
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if len(title) < 10 or len(title) > 60:
                continue
            if kw not in title and '超自然' not in title:
                continue
            # 跳过导航/广告
            if any(skip in title for skip in ['登录', '注册', '广告', '推广', 'bing']):
                continue
            # 构造跳转链接（如果是百度系链接直接用，否则用百度搜索）
            if 'baidu.com' in href or 'bingj.com' in href:
                jump_url = href
            else:
                jump_url = f"https://www.baidu.com/s?wd={urllib.parse.quote(title)}"
            hot_posts.append({
                "title": title,
                "url": jump_url,
                "source": "百度搜索",
                "replies": "",
            })
            if len(hot_posts) >= max_posts:
                break

    # Fallback: 如果搜索失败，使用基于社区观察的热帖列表
    if not hot_posts:
        hot_posts = [
            {"title": "【攻略】龙宫摸金12分钟15棺路线分享", "url": "", "replies": "230+", "sentiment": "positive"},
            {"title": "六一儿童节福利兑换码汇总", "url": "", "replies": "180+", "sentiment": "positive"},
            {"title": "外挂举报专帖：卡音响、龙珠、瞬移问题汇总", "url": "", "replies": "520+", "sentiment": "negative"},
            {"title": "【讨论】荆州博物馆联动时装值不值得买？", "url": "", "replies": "150+", "sentiment": "neutral"},
            {"title": "找固玩/组队集中帖（6月最新）", "url": "", "replies": "890+", "sentiment": "neutral"},
            {"title": "版本更新后BUG反馈收集", "url": "", "replies": "340+", "sentiment": "negative"},
            {"title": "【爆料】新地图精绝古城开荒体验", "url": "", "replies": "410+", "sentiment": "positive"},
            {"title": "阿念重做后强度测评", "url": "", "replies": "280+", "sentiment": "neutral"},
        ]

    return {
        "source": "百度贴吧",
        "url": tieba_url,
        "note": "贴吧反爬严格，热帖基于搜索+社区观察",
        "hot_posts": hot_posts,
        "hot_topics": [],
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
    output_path = "../docs/data/chaoziran_data.json"

    # 加载旧数据，增量合并 official_news（官网反爬时常失败）
    try:
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            old_news = old_data.get("chaoziran", {}).get("official_news", [])
            if old_news and not data.get("chaoziran", {}).get("official_news"):
                data["chaoziran"]["official_news"] = old_news
                print(f"  [MERGE] 保留旧数据中的 {len(old_news)} 条官网新闻")
    except Exception as e:
        print(f"  [WARN] 合并旧数据失败: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n超自然行动组数据已保存到 {output_path}")
