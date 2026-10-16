// 所有提供方统一的 SSE 事件协议。
//
// 服务端 -> 客户端的事件类型（每行一个 JSON）：
//   {"type":"meta",  "provider":"deepseek", "model":"deepseek-chat"}
//   {"type":"delta", "text":"增量文本"}
//   {"type":"done",  "text":"完整文本"}
//   {"type":"error", "message":"错误说明"}

export function sseWrite(res, payload) {
  res.write(`data: ${JSON.stringify(payload)}\n\n`);
}

export function sseHeaders(res) {
  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no",
  });
}
