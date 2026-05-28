# GRC恐怖多人品类情报

自动采集《超自然行动组》、R.E.P.O. 及同类竞品数据的信息看板。

## 覆盖游戏

| 游戏 | 平台 | 类型 |
|------|------|------|
| 超自然行动组 (Tomb Busters) | iOS/Android/PC | 多人欢乐恐怖撤离 |
| R.E.P.O. | Steam | 合作恐怖撤离 |
| Lethal Company | Steam | 合作恐怖撤离 |
| Phasmophobia | Steam | 合作猎鬼恐怖 |
| Content Warning | Steam | 合作恐怖拍摄 |
| FEEDERS | Steam | 合作恐怖撤离 |

## 数据维度

- **最新更新**：官网/BWIKI更新公告、Steam更新日志
- **排行榜**：Steam在线人数、TapTap评分/下载量、App Store排名
- **舆论**：Steam评测趋势、玩家标签、社区热度
- **竞品对比**：在线人数趋势、好评率、价格、拥有量

## 自动更新

- GitHub Actions 每日 UTC 00:00（北京时间 08:00）自动采集
- 支持手动触发：Actions 页面点击 "Run workflow"

## 本地运行

```bash
cd scripts
python main_crawler.py
```

然后用浏览器打开 `docs/index.html`。

## 部署到 GitHub Pages

1. 将代码推送到 GitHub 仓库
2. Settings → Pages → Source 选择 `gh-pages` 分支或 `docs` 目录
3. 访问 `https://你的用户名.github.io/仓库名/`

## 技术栈

- **爬虫**：Python 3 (urllib, 无第三方依赖)
- **前端**：纯HTML + Tailwind CSS (CDN) + Chart.js (CDN)
- **部署**：GitHub Pages + GitHub Actions
