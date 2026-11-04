# 环境经验（macOS / WorkBuddy 沙箱，实测于 2026-10-09）

## Node / npm
- 受管 Node 22：`/Users/jack/.workbuddy/binaries/node/versions/22.22.2-6/bin/node`（npm 同目录）
- npm 官方源偶发 502 → 使用 `--registry=https://registry.npmmirror.com`
- 共享 node workspace（`~/.workbuddy/binaries/node/workspace`）安装易冲突（ENOENT rename），一律装到项目目录
- **禁止** `npm install -g`

## Remotion 渲染（关键，三次踩坑换来）
1. 必须 `env -u NODE_OPTIONS`：WorkBuddy 注入的 `node-language-shim.cjs` 会让 `mkdir` 报 `EEXIST` / webpack cache 报 `ENOENT`
2. 必须设本地 `TMPDIR=<project>/.tmp`
3. 渲染命令需要 `dangerouslyDisableSandbox`（沙箱内 brokered-fs 会失败）
4. Bash 后台任务的 cwd 不保证持久：命令里必须显式 `cd`，或调用 `scripts/render.sh <project_dir> <comp_id> <out>`
5. 首次渲染自动下载 Chrome Headless Shell（~170MB），可正常下载

## Amazon 数据抓取
- `curl` / WebFetch 抓 amazon.com 会被反爬（返回 3KB 拦截页），且 WebFetch 会剥离图片 URL
- 可靠方案：`scripts/fetch-amazon.js`（playwright-core + 系统 Chrome，`channel: 'chrome'`，无需下载浏览器），可拿到主图 hiRes URL（`data-old-hires`）、缩略图、价格
- 图片高清下载：`https://m.media-amazon.com/images/I/<ID>._AC_SL1500_.jpg`；注意部分图最大只有 500px
- 备选：第三方评测站（bestreviews.guide 等）页面的 HTML 里含 `m.media-amazon.com/images/I/...` 原图 ID

## TTS 女声旁白
- `edge-tts` 装入受管 Python venv：`~/.workbuddy/binaries/python/envs/default`
- pip 源：`-i https://pypi.tuna.tsinghua.edu.cn/simple`
- 推荐声音 `en-US-AvaNeural`，`--rate=+8%`；参考脚本 `scripts/gen-vo.py`
- 每段旁白时长必须 ≤ 场景时长；用 `afinfo <file> | grep "estimated duration"` 校验，超时则缩短文案重新生成（提速超过 +20% 会变味）
- edge-tts 走微软在线服务，需要非沙箱网络

## BGM
- ccMixter（bgm-library skill 依赖）在当前网络不可达（`Parse Error: Expected HTTP/`）；失败时直接交付无 BGM 版并告知用户可在 TikTok/Reels 编辑器配乐
