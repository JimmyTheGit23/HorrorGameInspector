# HorrorIntel Automation Memory

## 2026-06-02 执行摘要

- **main_crawler.py**: 成功。采集6款Steam游戏数据（R.E.P.O.在线34225、Lethal Company在线4304、Phasmophobia在线9912、Content Warning在线1255、FEEDERS在线0/SteamSpy 403、NARAKA在线6649）+ 超自然行动组数据（BWIKI 6条、TapTap公告10条、论坛7条、评分6.8、关注11198925）。FEEDERS因SteamSpy 403未获取到数据。
- **chaoziran_crawler.py**: 成功。补充采集超自然行动组数据（BWIKI 6条、TapTap公告10条、论坛10条、评分6.8、关注11198937）。官网新闻0条，保留旧数据8条。
- **validate_links.py**: 成功。chaoziran_data.json: valid=18, invalid=0, unknown=12, unchanged=13。1条链接从unknown→valid。history.json和steam_data.json无链接需验证。
- **Git**: 3文件变更(116+/77-)，commit 22af316，push成功到main。
