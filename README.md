# RSS Video Agent

一个从 RSS 消息流筛选短视频选题，并生成视频号、抖音、小红书、TikTok、YouTube Shorts 引流文案的本地网页工具。

第一版不依赖 Coze，不强制依赖 Lark/飞书。后端使用 FastAPI，前端使用 Streamlit，数据保存在 SQLite。

## 功能

- 从 `config/rss_sources.json` 读取 RSS 源并抓取最新文章
- 按分类、关键词、时间范围筛选消息
- 用规则评分输出短视频选题池
- 可调用 OpenAI 兼容 API 做选题分析和视频文案生成
- 交易认知模块：从“尼克｜交易性格”公开内容蒸馏知识源中检索相关认知，再按用户问题生成标题、标签和口播文案
- 用户账号：支持注册、登录、退出和修改密码，业务页面与 API 均需要登录
- 自动事前选题：从互联网抓取未来宏观、Web3、Token 解锁、AI 科技、监管和网络安全事件，并生成提前发布的视频内容包
- 没有配置 API Key 时，也能使用规则版降级文案跑通流程
- 预留 `data/imports/` 目录，后续可导入平台热点 CSV

## 安装依赖

建议使用 Python 3.11+。

```bash
cd rss-video-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置环境变量

```bash
cp .env.example .env
```

按需编辑 `.env`：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini

DATABASE_URL=sqlite:///./rss_video_agent.db
AUTH_SESSION_DAYS=7

RSS_MAX_ARTICLES_PER_SOURCE=10
RSS_TIMEOUT_SECONDS=15

TRADING_ECONOMICS_API_KEY=
FINNHUB_API_KEY=
COINMARKETCAL_API_KEY=
TOKEN_UNLOCKS_API_KEY=
MESSARI_API_KEY=

PRE_EVENT_FETCH_DAYS=30
PRE_EVENT_DEFAULT_COUNTRIES=United States,China,Japan,Euro Area
PRE_EVENT_MIN_IMPORTANCE=medium
```

如果不填 `OPENAI_API_KEY`，系统会使用本地规则版分析和文案模板，不会调用大模型。

## 用户登录

首次打开 Streamlit 页面时，需要先注册账号。注册成功后会自动登录，登录后可以在左侧边栏修改密码或退出登录。

- 用户名：3-32 位字母、数字或下划线
- 密码：至少 8 位，并同时包含字母和数字
- 登录方式：支持用户名或邮箱
- 会话有效期：默认 7 天，可通过 `AUTH_SESSION_DAYS` 调整
- 密码使用 PBKDF2 加盐哈希保存，数据库不会保存明文密码
- 修改密码后，原有登录会话会立即失效

使用独立 FastAPI 时，前端会通过 Bearer Token 调用受保护接口；Streamlit 直接运行模式也使用同一套账号和会话数据表。

事前事件源中，Trading Economics、Finnhub、CoinMarketCal、Token Unlocks、Messari 需要 API Key。Google News RSS 兜底搜索、Microsoft Patch Tuesday 规则事件等不需要 API Key。缺少某个 API Key 时，系统会在前端提示并跳过该 API 源，不会影响其他事件源抓取。

## 初始化数据库

```bash
python scripts/init_db.py
```

## 启动 FastAPI

```bash
python run_api.py
```

默认地址：

- API: `http://127.0.0.1:8000`
- 健康检查: `http://127.0.0.1:8000/health`
- API 文档: `http://127.0.0.1:8000/docs`

## 启动 Streamlit

另开一个终端：

```bash
cd rss-video-agent
source .venv/bin/activate
streamlit run ui/streamlit_app.py
```

如果 API 不在默认地址，可以这样启动：

```bash
API_BASE_URL=http://127.0.0.1:8000 streamlit run ui/streamlit_app.py
```

## 如何添加 RSS 源

编辑 `config/rss_sources.json`，在 `rss_sources` 数组中追加：

```json
{
  "name": "Example",
  "url": "https://example.com/feed.xml",
  "language": "en",
  "category": "tech_news",
  "enabled": true
}
```

字段说明：

- `name`: 来源名
- `url`: RSS 地址
- `language`: `zh` 或 `en`
- `category`: 分类，例如 `crypto_news`、`ai_news`、`world_cup`、`tech_news`
- `enabled`: 是否启用

## 如何生成选题

1. 启动 FastAPI 和 Streamlit。
2. 打开 Streamlit 网页。
3. 进入“消息流获取”。
4. 点击“抓取最新 RSS”。
5. 选择分类、关键词和时间范围。
6. 点击“筛选选题”。
7. 查看评分最高的 5-10 条消息。
8. 可点击“选题分析”获取结构化分析。

## 如何生成视频文案

方式一：从文章生成

1. 在“消息流获取”中点击某条消息旁边的“生成文案”。
2. 切到“文案生成”。
3. 选择视频时长和平台。
4. 点击“生成文章文案”。

方式二：主题直写

1. 切到“主题直写”。
2. 输入主题。
3. 选择视频时长和平台。
4. 点击“生成主题文案”。

方式三：交易认知问答

1. 在左侧导航打开与“Web3实时热度消息墙”并列的“交易认知”页面。
2. 输入问题，例如“交易为什么要设置止损？”。
3. 选择平台和视频时长。
4. 点击“生成交易认知文案”。
5. 页面会同时展示内容包和本次采用的认知依据。

交易认知模块位于 `app/trading_cognition/`，是独立于 RSS 新闻源的本地知识源。它先通过关键词和中文片段匹配检索相关认知卡片，再把命中的核心判断、论证路径和行动规则交给模型。关闭“使用大模型生成”后，可使用本地规则版完成链路验证。

该模块只生成交易认知、交易心理、复盘和风险管理内容，不提供具体品种、点位、买卖信号、仓位比例或收益承诺，生成内容不构成投资建议。

输出包含：

- 选题判断
- 3 个推荐标题
- 视频骨架
- 完整口播文案
- 剪辑配图关键词
- 自检

## 自动事前选题

自动事前选题用于提前发现未来重要事件，并生成 KOL 可提前发布的视频内容包。第一版不需要导入 CSV，也不包含体育赛事方向。

使用步骤：

1. 启动 FastAPI 和 Streamlit。
2. 打开 Streamlit 侧边栏里的“自动事前选题”页面。
3. 点击“抓取未来 7 天事件”或“抓取未来 30 天事件”。
4. 使用时间范围、分类、重要性、状态和关键词筛选事件。
5. 选择某个事件，点击“生成事前选题”。
6. 设置目标平台、视频时长和补充要求。
7. 点击“生成内容”，系统会输出视频标题、封面标题、视频标签、选题理由、文案方向、完整口播文案和建议发布时间。

命令行抓取：

```bash
python scripts/fetch_pre_events.py --days 7
python scripts/fetch_pre_events.py --days 30 --category Web3
python scripts/fetch_pre_events.py --days 30 --category 宏观数据 --force-refresh
```

新增事件数据源：

1. 在 `config/event_sources.json` 中增加来源配置。
2. 在 `app/services/event_collectors/` 下新增采集器，继承 `BaseEventCollector`。
3. 采集器返回统一的 `EventItem`。
4. 在 `app/services/event_collectors/__init__.py` 的 `COLLECTORS` 中注册分类。
5. 如果需要关键词匹配，在 `config/event_keywords.json` 中补充关键词。

事件去重策略：

- 系统会用 `event_name + event_time + source` 生成 `content_hash`。
- 同一事件重复出现时会跳过或按 `force_refresh` 更新。
- 没有明确日期的事件不会入库；只有日期没有具体时间的事件默认按当天 09:00 处理。

注意：

- GPT 只负责基于已抓取事件生成内容，不负责凭空创造事件。
- 事件源失败不会中断整体抓取。
- 没有来源链接的事件不会被标记为 high 或 critical。
- 当前模块不包含世界杯、F1、NBA、欧冠等体育赛事。

## 平台热点 CSV 导入预留

第一版不直接爬取 TikTok、微信视频号、抖音、小红书。

后续可以把平台热点 CSV 放到：

```text
data/imports/
```

建议 CSV 字段：

```text
platform,title,description,url,views,likes,comments,shares,published_at,category
```

当前版本先预留目录和字段约定，后续可把 CSV 行转成文章或热点素材，再复用同一套评分和文案生成逻辑。

## API

- `GET /health`
- `POST /api/news/fetch`
- `GET /api/news/list`
- `GET /api/news/topics`
- `POST /api/news/analyze`
- `POST /api/script/from_article`
- `POST /api/script/from_topic`
- `POST /api/pre-events/fetch`
- `GET /api/pre-events/list`
- `GET /api/pre-events/upcoming`
- `POST /api/pre-topics/generate`
- `GET /api/pre-topics/list`
- `PUT /api/pre-topics/{topic_id}/status`
- `PUT /api/pre-events/{event_id}/status`
- `POST /api/web3-hot/fetch-now`
- `GET /api/web3-hot/list`
- `GET /api/web3-hot/ticker`
- `GET /api/web3-hot/{item_id}`
- `POST /api/web3-hot/{item_id}/generate-content`
- `GET /api/web3-hot/stats`

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/news/fetch
curl "http://127.0.0.1:8000/api/news/topics?category=ai_news&time_range=最近%2024%20小时&limit=10"
```

## 常见问题

### Streamlit 提示连接失败

确认 FastAPI 已启动：

```bash
curl http://127.0.0.1:8000/health
```

### 抓取 RSS 失败

可能原因：

- 当前网络无法访问对应 RSS
- RSS 源临时不可用
- 站点拒绝请求

接口会返回 `errors`，不会因为单个 RSS 源失败而中断全部抓取。

### 没有生成高质量中文文案

确认 `.env` 里配置了可用的 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`。未配置时系统会使用本地规则模板，只适合跑通流程。

### 英文新闻标题没有完整翻译

配置大模型后，点击“选题分析”会按 Prompt 输出中文标题和中文选题分析。无 API Key 时只提供降级标题。

### 数据库在哪里

默认是项目根目录下的：

```text
rss_video_agent.db
```

可通过 `.env` 的 `DATABASE_URL` 修改。

## Web3 实时热度消息墙

Streamlit 侧边栏新增页面：`Web3实时热度消息墙`。

这个模块用于聚合 Web3 / Crypto 热点消息，并按热度分展示。第一版支持：

- Web3 新闻 RSS 抓取
- Google News RSS 关键词召回
- X Recent Search API
- 可选 LunarCrush API
- `heat_score` 热度分，满分 100
- `red / yellow / gray` 热度等级
- `new / rising / hot / cooling` 趋势状态
- 点击热点生成视频标题、封面标题、标签和口播文案

命令行抓取：

```bash
python scripts/fetch_web3_hot.py
python scripts/fetch_web3_hot.py --source-type rss
python scripts/fetch_web3_hot.py --source-type google_news_rss --keyword ETF
```

配置 X API：

```bash
X_BEARER_TOKEN=你的_X_BEARER_TOKEN
```

`X Crypto Search` 默认启用；没有配置 Token 时系统会跳过 X，不影响 RSS 和 Google News RSS。程序不设置每日用量、请求间隔或费用预算限制，实际用量与费用以 X 开发者账户为准。

配置 LunarCrush：

```bash
LUNARCRUSH_API_KEY=你的_LUNARCRUSH_API_KEY
```

然后把 `config/web3_hot_sources.json` 里的 `LunarCrush` 改为 `"enabled": true`。没有配置时系统会跳过 LunarCrush。

新增热点数据源：

编辑 `config/web3_hot_sources.json`，新增 RSS 或 Google News RSS 来源：

```json
{
  "name": "Example Source",
  "type": "rss",
  "enabled": true,
  "priority": "P1",
  "url": "https://example.com/feed.xml",
  "poll_interval_seconds": 180
}
```

调整刷新频率：

```bash
WEB3_HOT_REFRESH_SECONDS=60
WEB3_HOT_ITEM_TTL_HOURS=24
WEB3_HOT_MAX_ITEMS_PER_SOURCE=50
```
