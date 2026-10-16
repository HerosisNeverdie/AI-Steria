// OpenAI 兼容提供方。DeepSeek 也复用它，只是 baseUrl / model / key 不同。
import { config } from "../config.js";

/**
 * 通用的 SSE 流解析：把上游的 text/event-stream 拆成一个个 data 对象。
 */
async function* iterSse(body) {
  const decoder = new TextDecoder();
  let buffer = "";
  for await (const chunk of body) {
    buffer += decoder.decode(chunk, { stream: true });
    // SSE 以空行分隔事件
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      for (const line of block.split(/\r?\n/)) {
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (!data || data === "[DONE]") continue;
        try {
          yield JSON.parse(data);
        } catch {
          // 忽略无法解析的行
        }
      }
    }
  }
}

export function makeOpenAICompatibleProvider({ name, apiKey, model, baseUrl }) {
  return {
    name,
    model,
    async *stream({ messages, signal }) {
      if (!apiKey) {
        throw new Error(
          `${name} 缺少 API Key，请在 .env 中配置后再试。`,
        );
      }

      const res = await fetch(`${baseUrl.replace(/\/+$/, "")}/chat/completions`, {
        method: "POST",
        signal,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          stream: true,
          max_tokens: config.maxTokens,
          messages: [
            { role: "system", content: config.systemPrompt },
            ...messages,
          ],
        }),
      });

      if (!res.ok || !res.body) {
        const detail = await res.text().catch(() => "");
        throw new Error(
          `${name} 接口返回 ${res.status} ${res.statusText}${
            detail ? `：${detail.slice(0, 300)}` : ""
          }`,
        );
      }

      for await (const event of iterSse(res.body)) {
        const piece = event?.choices?.[0]?.delta?.content;
        if (piece) yield piece;
      }
    },
  };
}

export const deepseekProvider = () =>
  makeOpenAICompatibleProvider({
    name: "deepseek",
    apiKey: config.deepseek.apiKey,
    model: config.deepseek.model,
    baseUrl: config.deepseek.baseUrl,
  });

export const openaiProvider = () =>
  makeOpenAICompatibleProvider({
    name: "openai",
    apiKey: config.openai.apiKey,
    model: config.openai.model,
    baseUrl: config.openai.baseUrl,
  });
