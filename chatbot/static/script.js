const log = document.getElementById("log");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const submitBtn = form.querySelector("button[type='submit']");
const historyCount = document.getElementById("history-count");
const resetBtn = document.getElementById("reset-btn");

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `msg msg--${role}`;

  const label = document.createElement("span");
  label.className = "msg__role";
  label.textContent = role === "user" ? "you" : role === "assistant" ? "AI" : "error";

  const body = document.createElement("span");
  body.className = "msg__text";
  body.textContent = text;

  el.appendChild(label);
  el.appendChild(body);
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

async function sendMessage(message) {
  submitBtn.disabled = true;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();

    if (!res.ok) {
      addMessage("error", data.error || "Something went wrong.");
      return;
    }

    addMessage("assistant", data.reply);
    historyCount.textContent = data.history_length;
  } catch (err) {
    addMessage("error", "Network error — is the server running?");
  } finally {
    submitBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return; // client-side mirror of the server's validation gate
  addMessage("user", message);
  input.value = "";
  sendMessage(message);
});

resetBtn.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  log.innerHTML = "";
  historyCount.textContent = "0";
  input.focus();
});

input.focus();
