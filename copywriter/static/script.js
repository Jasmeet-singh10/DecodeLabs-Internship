const form = document.getElementById("gen-form");
const generateBtn = document.getElementById("generate-btn");
const results = document.getElementById("results");
const errorMsg = document.getElementById("error-msg");

const tempSlider = document.getElementById("temperature");
const tempVal = document.getElementById("temp-val");
const topPSlider = document.getElementById("top_p");
const topPVal = document.getElementById("top-p-val");

tempSlider.addEventListener("input", () => {
  tempVal.textContent = parseFloat(tempSlider.value).toFixed(2);
});
topPSlider.addEventListener("input", () => {
  topPVal.textContent = parseFloat(topPSlider.value).toFixed(2);
});

function showError(message) {
  errorMsg.textContent = message;
  errorMsg.hidden = false;
}

function clearError() {
  errorMsg.hidden = true;
  errorMsg.textContent = "";
}

function renderResults(resultsByPlatform) {
  results.innerHTML = "";
  const entries = Object.entries(resultsByPlatform);

  if (entries.length === 0) {
    results.innerHTML = '<p class="empty-state">Generated copy will appear here.</p>';
    return;
  }

  entries.forEach(([platform, text]) => {
    const card = document.createElement("div");
    card.className = "result-card";

    const header = document.createElement("div");
    header.className = "result-card__header";

    const label = document.createElement("span");
    label.className = "result-card__platform";
    label.textContent = platform;

    const copyBtn = document.createElement("button");
    copyBtn.className = "result-card__copy-btn";
    copyBtn.type = "button";
    copyBtn.textContent = "copy";
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(text);
      copyBtn.textContent = "copied";
      setTimeout(() => (copyBtn.textContent = "copy"), 1200);
    });

    header.appendChild(label);
    header.appendChild(copyBtn);

    const body = document.createElement("p");
    body.className = "result-card__text";
    body.textContent = text;

    card.appendChild(header);
    card.appendChild(body);
    results.appendChild(card);
  });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();

  const payload = {
    product_name: document.getElementById("product_name").value.trim(),
    description: document.getElementById("description").value.trim(),
    tone: document.getElementById("tone").value.trim(),
    platform: document.getElementById("platform").value,
    temperature: parseFloat(tempSlider.value),
    top_p: parseFloat(topPSlider.value),
  };

  if (!payload.product_name || !payload.description || !payload.tone) {
    showError("Product name, description, and tone are all required.");
    return;
  }

  generateBtn.disabled = true;
  generateBtn.textContent = "Generating…";

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }

    renderResults(data.results);
  } catch (err) {
    showError("Network error — is the server running?");
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate copy";
  }
});
