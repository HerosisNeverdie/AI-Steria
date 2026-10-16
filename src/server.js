// AI薇Steria 服务端
// 零依赖：只用 Node.js 内置模块（http / fs / path）。
// 职责：托管 web/ 静态页面 + 提供 /api/chat 流式接口。
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve, sep } from "node:path";

import { config, providerReady } from "./config.js";
import { getProvider, availableProviders } from "./providers/index.js";
import { sseHeaders, sseWrite } from "./providers/sse.js";

const WEB_DIR = resolve(config.rootDir, "web");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readBody(req, limit = 512 * 1024) {
  return new Promise((resolvePromise, reject) => {
    let size = 0;
    const chunks = [];
    req.on("data", (c) => {
      size += c.length;
      if (size > limit) {
        reject(new Error("请求体过大"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolvePromise(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

// 防御路径穿越：解析后的路径必须仍在 web/ 目录内
function safeStaticPath(urlPath) {
  const decoded = decodeURIComponent(urlPath.split("?")[0]);
  const rel = decoded === "/" ? "index.html" : decoded.replace(/^\/+/, "");
  const target = resolve(WEB_DIR, normalize(rel));
  if (target !== WEB_DIR && !target.startsWith(WEB_DIR + sep)) return null;
  return target;
}

async function serveStatic(req, res) {
  const target = safeStaticPath(req.url || "/");
  if (!target) {
    sendJson(res, 403, { error: "forbidden" });
    return;
  }
  try {
    const info = await stat(target);
    if (!info.isFile()) throw new Error("not a file");
    const body = await readFile(target);
    res.writeHead(200, {
      "Content-Type": MIME[extname(target).toLowerCase()] || "application/octet-stream",
      "Content-Length": body.length,
      "Cache-Control": "no-cache",
    });
    res.end(body);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("404 Not Found");
  }
}

function normalizeMessages(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((m) => m && typeof m.content === "string")
    .map((m) => ({
      role: m.role === "assistant" ? "assistant" : "user",
      content: m.content.slice(0, 16000),
    }))
    .slice(-40); // 只保留最近 40 条，避免上下文无限增长
}

async function handleChat(req, res) {
  let messages;
  try {
    const body = await readBody(req);
    messages = normalizeMessages(JSON.parse(body || "{}").messages);
  } catch {
    sendJson(res, 400, { error: "请求体不是合法的 JSON" });
    return;
  }

  if (messages.length === 0) {
    sendJson(res, 400, { error: "messages 不能为空" });
    return;
  }

  let provider;
  try {
    provider = getProvider();
  } catch (err) {
    sendJson(res, 500, { error: err.message });
    return;
  }

  if (!providerReady() && provider.name !== "mock") {
    sendJson(res, 500, {
      error: `PROVIDER=${config.provider} 还没有配置 API Key，请检查 .env 文件。`,
    });
    return;
  }

  const controller = new AbortController();
  req.on("close", () => controller.abort());

  sseHeaders(res);

  try {
    sseWrite(res, { type: "meta", provider: provider.name, model: provider.model });
    let full = "";
    for await (const piece of provider.stream({ messages, signal: controller.signal })) {
      if (res.writableEnded) break;
      full += piece;
      sseWrite(res, { type: "delta", text: piece });
    }
    if (!res.writableEnded) {
      sseWrite(res, { type: "done", text: full });
      res.end();
    }
  } catch (err) {
    if (!res.writableEnded) {
      sseWrite(res, { type: "error", message: err?.message || String(err) });
      res.end();
    }
  }
}

const server = createServer(async (req, res) => {
  const url = req.url || "/";

  if (url === "/api/health") {
    sendJson(res, 200, {
      ok: true,
      app: "AI薇Steria",
      provider: config.provider,
      ready: providerReady(),
      providers: availableProviders,
    });
    return;
  }

  if (url === "/api/chat") {
    if (req.method !== "POST") {
      sendJson(res, 405, { error: "请使用 POST" });
      return;
    }
    await handleChat(req, res);
    return;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    sendJson(res, 405, { error: "方法不被允许" });
    return;
  }

  await serveStatic(req, res);
});

server.listen(config.port, () => {
  const line = "─".repeat(52);
  console.log(line);
  console.log("  AI薇Steria 已启动");
  console.log(line);
  console.log(`  地址      : http://localhost:${config.port}`);
  console.log(`  提供方    : ${config.provider}${providerReady() ? "" : "（凭据未配置）"}`);
  console.log(`  可选提供方: ${availableProviders.join(" | ")}`);
  if (config.provider === "mock") {
    console.log("  提示      : 当前是 mock 模式，配置 .env 后可切换真实模型");
  }
  console.log(line);
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    server.close(() => process.exit(0));
  });
}
