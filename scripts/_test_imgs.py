import urllib.request, re, json

# Get TapTap icon for 超自然行动组
url = "https://www.taptap.cn/app/714123"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")

# Extract all image URLs
imgs = re.findall(r'(https?://[^"\'\\]+\.(?:png|jpg|webp))', html)
print(f"Total images found: {len(imgs)}")
for i in imgs[:30]:
    lower = i.lower()
    if any(kw in lower for kw in ["icon", "logo", "avatar", "cover", "banner", "app"]):
        print(f"  MATCH: {i[:150]}")

# Also search Nuxt payload for icon
payload_match = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if payload_match:
    payload = json.loads(payload_match.group(1))
    for i, item in enumerate(payload):
        if isinstance(item, str) and ("icon" in item.lower() or "cover" in item.lower()) and item.startswith("http"):
            print(f"  NUXT[{i}]: {item[:150]}")
