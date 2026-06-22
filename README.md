# RSS Video Agent

一个从 RSS 消息流筛选短视频选题，并生成视频号、抖音、小红书、TikTok、YouTube Shorts 引流文案的本地网页工具。

第一版不依赖 Coze，不强制依赖 Lark/飞书。后端使用 FastAPI，前端使用 Streamlit，数据保存在 SQLite。

## 功能

- 从 `config/rss_sources.json` 读取 RSS 源并抓取最新文章
- 按分类、关键词、时间范围筛选消息
- 用规则评分输出短视频选题池
- 可调用 OpenAI 兼容 API 做选题分析和视频文案生成
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

RSS_MAX_ARTICLES_PER_SOURCE=20
RSS_TIMEOUT_SECONDS=20
```

如果不填 `OPENAI_API_KEY`，系统会使用本地规则版分析和文案模板，不会调用大模型。

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

输出包含：

- 选题判断
- 3 个推荐标题
- 视频骨架
- 完整口播文案
- 剪辑配图关键词
- 自检

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

