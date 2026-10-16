// 提供方注册表：按 .env 里的 PROVIDER 选择一个实现。
import { config } from "../config.js";
import { mockProvider } from "./mock.js";
import { deepseekProvider, openaiProvider } from "./openaiCompatible.js";

const registry = {
  mock: () => mockProvider,
  deepseek: deepseekProvider,
  openai: openaiProvider,
};

export function getProvider() {
  const factory = registry[config.provider];
  if (!factory) {
    throw new Error(
      `未知的 PROVIDER：「${config.provider}」。可选：${Object.keys(registry).join(" | ")}`,
    );
  }
  return factory();
}

export const availableProviders = Object.keys(registry);
