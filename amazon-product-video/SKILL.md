---
name: amazon-product-video
description: 从 Amazon ASIN 一站式生成竖屏（9:16）社交媒体产品宣传视频（Remotion + 英文女声旁白）。当用户给出 Amazon ASIN 并要求"做产品视频/社媒短视频/TikTok/Reels/Shorts 宣传视频"时使用。This skill should be used when the user provides an Amazon ASIN and wants a product promo video, social media short, or listing video generated from the live product page (title, bullets, main images), including female-voice TTS narration and MP4 delivery.
agent_created: true
---

# Amazon Product Video

## Overview

从用户提供的 Amazon ASIN 自动完成全流程：抓取产品页（标题/卖点/主图）→ 规划 6 场景分镜 → 用内置 Remotion 模板生成 1080×1920 竖屏视频 → edge-tts 英文女声旁白 → 渲染 MP4 交付。默认风格为深色大胆吸睛（dark + 亮橙/明黄撞色 + 超大粗体排版），全英文文案面向美国站。

## Workflow

### Step 0 — 环境准备（只做一次）

先读 `references/environment-notes.md`（关键环境坑，必读），然后：

1. 复制模板到工作区：`cp -r assets/remotion-template <workspace>/remotion-videos`
2. 安装依赖（用受管 Node 22，npmmirror 源）：
   `cd <workspace>/remotion-videos && npm install --registry=https://registry.npmmirror.com`
3. TTS 环境：受管 Python venv `~/.workbuddy/binaries/python/envs/default` 安装 `edge-tts`（清华镜像源）
4. 抓取依赖：项目目录安装 `playwright-core`（不需下载浏览器，用系统 Chrome）

### Step 1 — 抓取产品数据

运行 `scripts/fetch-amazon.js`（playwright-core + 系统 Chrome，绕过反爬）获取：主图 hiRes URL（`data-old-hires`）、全部辅图 ID、价格、标题。

- 高清图下载格式：`https://m.media-amazon.com/images/I/<ID>._AC_SL1500_.jpg`，存到项目 `public/assets/`
- 标题/卖点/评分用 WebFetch 抓页面文本即可（图片 URL 必须靠脚本或第三方评测站）
- 用 Read 工具逐张查看下载的图片，挑出：主图（hero）、生活方式图、细节/面料图、功能图

### Step 2 — 改写视频文案

模板组合位于 `src/compositions/subrtex-promo/`（6 场景，720 帧 / 30fps / 24s）：

| 场景 | 文件 | 时长 | 内容 |
|------|------|------|------|
| Hook | HookScene.tsx | 3s | 痛点开场 |
| Reveal | RevealScene.tsx | 4s | 主图 + 产品名 + 评分徽章 |
| Pieces | PiecesScene.tsx | 4s | 核心卖点 1（列表逐项） |
| RealLife | RealLifeScene.tsx | 4s | 核心卖点 2（使用场景） |
| Fabric | FabricScene.tsx | 4s | 核心卖点 3（材质/参数） |
| CTA | CtaScene.tsx | 5s | 行动号召 + 购买指引 |

从 Amazon 卖点提炼英文短文案（每行 ≤ 5 个词，全大写），替换各场景文件顶部文案与 `public/assets` 图片引用；配色在 `VideoComposition.tsx` 的 `BRAND` 常量区。如产品不是 7 件套结构，把 Pieces/RealLife/Fabric 三场景改成该产品最强的 3 个卖点。

### Step 3 — 生成女声旁白

参照 `scripts/gen-vo.py`：edge-tts，声音 `en-US-AvaNeural`，`rate=+8%`，每场景一段存 `public/vo/vo-N.mp3`。旁白稿与画面文案呼应但可更口语。

**硬约束**：用 `afinfo <file>` 校验每段时长 ≤ 对应场景时长（3/4/4/4/4/5 秒）；超时则缩短文案重新生成，不要简单提速（>+20% 会变调）。

### Step 4 — 渲染交付

调用 `scripts/render.sh <project_dir> <composition_id> <output.mp4>`（已内置 `env -u NODE_OPTIONS`、本地 TMPDIR 等修复；需 `dangerouslyDisableSandbox`）。

渲染后：
1. `afinfo <mp4>` 验证有 AAC 音轨且时长正确
2. 关键帧抽查：`npx remotion still src/index.ts <comp> .tmp/frame-N.png --frame=N` 并用 Read 查看
3. 用 present_files 交付 MP4

## 常见问题

- **渲染报 EEXIST/ENOENT (mkdir、webpack cache)** → 没清 NODE_OPTIONS 或没设本地 TMPDIR，用 render.sh
- **npx could not determine executable** → cwd 不在项目目录，命令里显式 `cd`
- **Amazon 抓到 3KB 拦截页** → curl 被反爬，必须用 fetch-amazon.js
- **ccMixter BGM 拉取失败** → 当前网络不可达属正常，交付无 BGM 版并建议用户在发布平台编辑器配乐

## Resources

### scripts/
- `fetch-amazon.js` — playwright-core 抓 Amazon 产品页主图/辅图/价格（需项目目录装 playwright-core，系统 Chrome）
- `gen-vo.py` — edge-tts 批量生成 6 段英文女声旁白
- `render.sh` — 带全部环境修复的渲染封装：`render.sh <project_dir> <comp_id> <out>`

### references/
- `environment-notes.md` — 沙箱/Node/npm/渲染/抓取/TTS 的全部实测坑与修复（Step 0 前必读）

### assets/
- `remotion-template/` — 完整可渲染的 Remotion 项目模板（6 场景深色大胆风格竖屏视频，含旁白挂载点），复制后改文案即用
