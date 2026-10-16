// 极简 .env 读取（零依赖）。Node 20.6+ 本身有 --env-file，但为了兼容性这里自己解析。
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, "..");

function loadDotEnv() {
  try {
    const raw = readFileSync(join(rootDir, ".env"), "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      let value = trimmed.slice(eq + 1).trim();
      // 去掉成对的引号
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      // 已存在的真实环境变量优先
      if (!(key in process.env)) process.env[key] = value;
    }
  } catch {
    // 没有 .env 文件是正常情况，忽略
  }
}

loadDotEnv();

const provider = (process.env.PROVIDER || "mock").toLowerCase();

export const config = {
  rootDir,
  port: Number(process.env.PORT || 8787),
  provider,
  systemPrompt:
    process.env.SYSTEM_PROMPT ||
    "你是 AI薇Steria，一个友好、简洁、乐于助人的中文 AI 助手。",
  maxTokens: Number(process.env.MAX_TOKENS || 2048),
  deepseek: {
    apiKey: process.env.DEEPSEEK_API_KEY || "",
    model: process.env.DEEPSEEK_MODEL || "deepseek-chat",
    baseUrl: process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com",
  },
  openai: {
    apiKey: process.env.OPENAI_API_KEY || "",
    model: process.env.OPENAI_MODEL || "gpt-4o-mini",
    baseUrl: process.env.OPENAI_BASE_URL || "https://api.openai.com/v1",
  },
};

/** 返回当前 provider 是否已经配好可用的凭据 */
export function providerReady() {
  switch (config.provider) {
    case "deepseek":
      return Boolean(config.deepseek.apiKey);
    case "openai":
      return Boolean(config.openai.apiKey);
    case "mock":
      return true;
    default:
      return false;
  }
}
