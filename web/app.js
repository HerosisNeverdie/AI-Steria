// AI薇Steria 前端：原生 ES module，无框架、无构建步骤。
const $ = (sel) => document.querySelector(sel);

const els = {
  messages: $("#messages"),
  empty: $("#empty"),
  form: $("#composer"),
  input: $("#input"),
  send: $("#send"),
  clear: $("#clear"),
  status: $("#status"),
};

/** 会话历史：[{ role: "user" | "assistant", content: string }] */
let history = [];
let busy = false;

// ---------- 状态栏 ----------
async function refreshStatus() {
  try {
    const res = await fetch("/api/health");
    const info = await res.json();
    if (info.provider === "mock") {
      setStatus(`mock 模式 · 未接入真实模型`, "warn");
    } else if (info.ready) {
      setStatus(`已连接 · ${info.provider}`, "ready");
    } else {
      setStatus(`${info.provider} · 缺少 API Key`, "error");
    }
  } catch {
    setStatus("服务端未响应", "error");
  }
}

function setStatus(text, kind) {
  els.status.textContent = text;
  els.status.className = `status ${kind || ""}`;
}

// ---------- 渲染 ----------
function hideEmpty() {
  if (els.empty && els.empty.parentNode) els.empty.remove();
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** 极简 Markdown：``` 代码块、`行内代码`、**粗体** */
function renderMarkdown(text) {
  const blocks = escapeHtml(text).split(/```/);
  return blocks
    .map((block, i) => {
      if (i % 2 === 1) {
        // 代码块，去掉首行语言标识
        const body = block.replace(/^[a-zA-Z0-9+#-]*\r?\n/, "");
        return `<pre><code>${body.replace(/\n$/, "")}</code></pre>`;
      }
      return block
        .replace(/`([^`\n]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    })
    .join("");
}

function scrollToBottom() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function addMessage(role, text) {
  hideEmpty();
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "我" : "薇";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  // 流式输出期间先按纯文本显示，结束时再渲染 Markdown
  bubble.textContent = text || "";

  wrap.append(avatar, bubble);
  els.messages.append(wrap);
  scrollToBottom();

  return {
    setText(value) {
      bubble.innerHTML = renderMarkdown(value);
    },
    setRaw(value) {
      bubble.textContent = value;
    },
    addCursor() {
      bubble.classList.add("cursor");
    },
    removeCursor() {
      bubble.classList.remove("cursor");
    },
  };
}

// ---------- 发送 ----------
async function send(text) {
  const content = text.trim();
  if (!content || busy) return;

  busy = true;
  els.send.disabled = true;
  els.input.value = "";
  autoGrow();

  addMessage("user", content);
  history.push({ role: "user", content });

  const view = addMessage("assistant", "");
  view.addCursor();

  let full = "";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });

    if (!res.ok || !res.body) {
      // 非流式错误（例如 400 / 500），按 JSON 处理
      const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = block.split(/\r?\n/).find((l) => l.startsWith("data:"));
        if (!line) continue;

        let evt;
        try {
          evt = JSON.parse(line.slice(5).trim());
        } catch {
          continue;
        }

        if (evt.type === "delta") {
          full += evt.text;
          view.setRaw(full); // 流式期间用纯文本，保证性能
          scrollToBottom();
        } else if (evt.type === "error") {
          throw new Error(evt.message);
        }
      }
    }

    view.removeCursor();
    view.setText(full);
    history.push({ role: "assistant", content: full });
  } catch (err) {
    view.removeCursor();
    view.setText(`⚠️ 出错了：${err.message}`);
    // 失败的一轮不写入历史，避免污染上下文
    history.pop();
  } finally {
    busy = false;
    els.send.disabled = false;
    els.input.focus();
    scrollToBottom();
  }
}

// ---------- 输入框自适应高度 ----------
function autoGrow() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 200)}px`;
}

// ---------- 事件绑定 ----------
els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  send(els.input.value);
});

els.input.addEventListener("input", autoGrow);

els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send(els.input.value);
  }
});

els.clear.addEventListener("click", () => {
  history = [];
  els.messages.innerHTML = "";
  location.reload();
});

document.addEventListener("click", (e) => {
  const chip = e.target.closest?.(".chip");
  if (chip) send(chip.textContent);
});

refreshStatus();
els.input.focus();
