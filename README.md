<div align="center">

# AI薇Steria

**一个轻量、零依赖的 AI 聊天助手应用**

流式回复 · 多模型切换 · 密钥留在服务端

![Node](https://img.shields.io/badge/Node.js-%E2%89%A518.17-339933?logo=node.js&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

## 这是什么

AI薇Steria 是一个可以直接跑起来的 AI 聊天助手：

- **零依赖**——后端只用 Node.js 内置模块，前端是原生 HTML/CSS/JS，不需要 `npm install`，不需要打包工具；
- **流式输出**——基于 SSE，逐字显示回复，带打字机光标；
- **多模型支持**——内置 DeepSeek、OpenAI 及任意 OpenAI 兼容网关（Ollama / vLLM / OneAPI 等）；
- **mock 模式**——没配 API Key 也能先把界面跑通；
- **密钥安全**——API Key 只存在于服务端 `.env`，永远不下发到浏览器。

## 快速开始

需要 Node.js **18.17 或更高版本**（用到内置 `fetch` 和 `AbortController`）。

```bash
git clone https://github.com/576648958/AI-Steria.git
cd AI-Steria
npm start
```

打开 <http://localhost:8787> 即可对话。默认是 **mock 模式**，回复由本地生成，不消耗额度。

### 接入真实模型

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

编辑 `.env`：

```ini
PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_MODEL=deepseek-chat
```

重启服务，状态栏会变成绿色的「已连接 · deepseek」。

## 支持的提供方

| `PROVIDER` | 说明 | 必填变量 |
| --- | --- | --- |
| `mock` | 本地假回复，无需密钥，默认值 | — |
| `deepseek` | DeepSeek 官方 API | `DEEPSEEK_API_KEY` |
| `openai` | OpenAI 或任意 OpenAI 兼容网关 | `OPENAI_API_KEY`、可选 `OPENAI_BASE_URL` |

接本地 Ollama 的例子：

```ini
PROVIDER=openai
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=qwen2.5:7b
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `8787` | 服务监听端口 |
| `PROVIDER` | `mock` | `mock` / `deepseek` / `openai` |
| `SYSTEM_PROMPT` | 内置人设 | 系统提示词 |
| `MAX_TOKENS` | `2048` | 单次回复最大 token |
| `DEEPSEEK_API_KEY` | 空 | DeepSeek 密钥 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型名 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek 接口地址 |
| `OPENAI_API_KEY` | 空 | OpenAI / 兼容网关密钥 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 接口地址 |

## API

### `GET /api/health`

```json
{
  "ok": true,
  "app": "AI薇Steria",
  "provider": "mock",
  "ready": true,
  "providers": ["mock", "deepseek", "openai"]
}
```

### `POST /api/chat`

请求体：

```json
{
  "messages": [
    { "role": "user", "content": "你好" }
  ]
}
```

返回 `text/event-stream`，每条事件形如 `data: {...}`：

| `type` | 含义 | 字段 |
| --- | --- | --- |
| `meta` | 本次使用的提供方 | `provider`、`model` |
| `delta` | 增量文本 | `text` |
| `done` | 完成 | `text`（完整回复） |
| `error` | 出错 | `message` |

用 curl 试一下：

```bash
curl -N -X POST http://localhost:8787/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}"
```

## 项目结构

```
AI-Steria/
├── src/
│   ├── server.js                    # HTTP 服务：静态托管 + 流式接口
│   ├── config.js                    # .env 解析与配置
│   └── providers/
│       ├── index.js                 # 提供方注册表
│       ├── mock.js                  # 本地假回复
│       ├── openaiCompatible.js      # OpenAI / DeepSeek 通用实现
│       └── sse.js                   # SSE 输出工具
├── web/
│   ├── index.html                   # 页面结构
│   ├── style.css                    # 样式
│   └── app.js                       # 前端逻辑（流式接收 + 渲染）
├── .env.example                     # 环境变量模板
├── .gitignore
├── LICENSE
└── package.json
```

## 安全说明

- `.env` 已加入 `.gitignore`，**不会被提交**；请勿把密钥写进源码或前端；
- 静态文件服务做了路径穿越防护，只允许访问 `web/` 目录内的文件；
- 会话历史最多保留最近 40 条，单条内容上限 16000 字符；
- 本项目面向本地/内网使用。若要公网部署，请自行补充鉴权、限流和 HTTPS。

## 常见问题

**端口被占用？** 改 `.env` 里的 `PORT`，或先关掉占用进程。

**状态栏显示「缺少 API Key」？** `.env` 里 `PROVIDER` 和对应的 `*_API_KEY` 没配齐，或改完没有重启服务。

**回复不是逐字出现的？** 部分反向代理会缓冲 SSE，需要关掉缓冲（响应头已带 `X-Accel-Buffering: no`）。

## 后续可做

- [ ] 多会话管理与会话持久化
- [ ] Markdown 完整渲染（表格、列表）与代码高亮
- [ ] 导出对话为 Markdown / JSON
- [ ] Docker 部署与鉴权

## License

[MIT](LICENSE) © 2026 576648958
