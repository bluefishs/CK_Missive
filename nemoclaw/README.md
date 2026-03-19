# NemoClaw 開發平台

> NemoClaw 是乾坤智能體的自覺代理人平台。
> 在此平台內撰寫 OpenClaw 代理人腳本，站在兩個巨人肩膀上。

## 架構

```
NemoClaw Platform (本目錄)
├── agents/          ← OpenClaw 代理人腳本
│   └── ck-missive/  ← 乾坤公文代理人 (OpenClaw Skill)
├── sandbox/         ← 沙箱配置 (安全邊界)
└── config/          ← NemoClaw 平台配置
```

## 三者關係

- **NemoClaw** = 開發平台 + 沙箱 (控制層)
- **OpenClaw** = 多頻道 Agent 框架 (執行層)
- **乾坤** = 公文領域智能引擎 (領域層)

## 啟動

```bash
# 1. 乾坤引擎 (已在運行)
pm2 start ecosystem.config.js

# 2. OpenClaw 代理人 (透過 NemoClaw 沙箱)
cd nemoclaw/agents/ck-missive
# 配置 → 見 skill.yaml
```
