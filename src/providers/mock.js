// 本地假回复提供方：不需要任何 API Key，用来先把界面跑通。
// 它会假装"流式"输出，方便你验证前端打字机效果。

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const KNOWLEDGE = [
  "我是 AI薇Steria。当前运行在 mock 模式，回复是本地生成的，没有调用任何大模型。",
  "想要真实回答，请复制 .env.example 为 .env，把 PROVIDER 改成 deepseek 并填入 DEEPSEEK_API_KEY。",
  "这个项目是零依赖的：后端只用 Node.js 内置模块，前端是原生 HTML/CSS/JS。",
  "密钥只在服务端读取，永远不会发到浏览器，所以放 .env 里是安全的。",
];

function composeReply(messages) {
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  const question = (lastUser?.content || "").trim();
  const tip = KNOWLEDGE[question.length % KNOWLEDGE.length];
  const head = question
    ? `你问的是：「${question.length > 60 ? question.slice(0, 60) + "…" : question}」。`
    : "你好！";
  return [
    head,
    "",
    tip,
    "",
    "接口自检结果：",
    "- `POST /api/chat` 流式返回 ✅",
    "- 会话历史已在服务端拼接 ✅",
    "- 切换到真实模型后无需改前端代码 ✅",
  ].join("\n");
}

export const mockProvider = {
  name: "mock",
  model: "mock-local",
  async *stream({ messages }) {
    const reply = composeReply(messages);
    // 按 2 个字符一片输出，模拟流式
    for (let i = 0; i < reply.length; i += 2) {
      yield reply.slice(i, i + 2);
      await sleep(12);
    }
  },
};
