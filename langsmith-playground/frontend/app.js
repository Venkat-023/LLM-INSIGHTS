const statusGrid = document.querySelector("#statusGrid");
const resultArea = document.querySelector("#resultArea");
const activityState = document.querySelector("#activityState");

const setBusy = (message) => {
  activityState.textContent = message;
};

const api = async (path, body = undefined) => {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
};

const metric = (label, value) => `
  <div class="status-card">
    <strong>${label}</strong>
    <span>${value}</span>
  </div>
`;

const loadStatus = async () => {
  const status = await api("/api/status");
  statusGrid.innerHTML = [
    metric("Project", status.project),
    metric("Provider", status.provider),
    metric("Model", status.model),
    metric("Tracing", status.langsmith_tracing ? "Enabled" : "Disabled"),
    metric("API Ready", status.ready ? "Yes" : "Missing key"),
  ].join("");
};

const tokensText = (tokens) =>
  `prompt ${tokens.prompt} / completion ${tokens.completion} / total ${tokens.total}`;

const renderLab = (data) => {
  const rows = data.results
    .map(
      (item) => `
        <tr>
          <td>${item.scenario}</td>
          <td>${item.estimated_input_tokens}</td>
          <td>${item.tokens.prompt}</td>
          <td>${item.tokens.completion}</td>
          <td>${item.tokens.total}</td>
          <td>${item.latency_seconds.toFixed(2)}s</td>
        </tr>
      `,
    )
    .join("");

  resultArea.innerHTML = `
    <table class="metrics-table">
      <thead>
        <tr>
          <th>Scenario</th>
          <th>Estimated Input</th>
          <th>Prompt Tokens</th>
          <th>Completion Tokens</th>
          <th>Total Tokens</th>
          <th>Latency</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="response-card">
      <h3>LangSmith Filters</h3>
      <pre>Project: Venkat
Tags: observability, tokens, latency
Trace: ${data.trace_name}
Total tokens: ${data.totals.total}
Wall time: ${data.totals.latency_seconds.toFixed(2)}s</pre>
    </div>
  `;
};

const renderChat = (data) => {
  resultArea.innerHTML = `
    <div class="response-card">
      <h3>${data.trace_name}</h3>
      <pre>${data.content}</pre>
    </div>
    <div class="response-card">
      <h3>Metrics</h3>
      <pre>${tokensText(data.tokens)}
latency ${data.latency_seconds.toFixed(2)}s</pre>
    </div>
  `;
};

const renderCompare = (data) => {
  resultArea.innerHTML = data.results
    .map(
      (item) => `
        <div class="response-card">
          <h3>${item.prompt}</h3>
          <pre>${item.content}</pre>
          <p>${tokensText(item.tokens)} / latency ${item.latency_seconds.toFixed(2)}s</p>
        </div>
      `,
    )
    .join("");
};

const renderError = (data) => {
  resultArea.innerHTML = `
    <div class="response-card">
      <h3>${data.trace_name}</h3>
      <pre>${data.error}

${data.message}</pre>
    </div>
  `;
};

const runAction = async (message, callback) => {
  try {
    setBusy(message);
    await callback();
    setBusy("Done");
  } catch (error) {
    resultArea.innerHTML = `<div class="response-card"><h3>Error</h3><pre>${error.message}</pre></div>`;
    setBusy("Error");
  }
};

document.querySelector("#runLabBtn").addEventListener("click", () =>
  runAction("Running token lab...", async () => {
    const topic = document.querySelector("#topicInput").value;
    renderLab(await api("/api/observability-lab", { topic }));
  }),
);

document.querySelector("#chatBtn").addEventListener("click", () =>
  runAction("Running chat trace...", async () => {
    const message = document.querySelector("#chatInput").value;
    renderChat(await api("/api/chat", { message }));
  }),
);

document.querySelector("#compareBtn").addEventListener("click", () =>
  runAction("Comparing prompts...", async () => {
    const question = document.querySelector("#compareInput").value;
    renderCompare(await api("/api/compare-prompts", { question }));
  }),
);

document.querySelector("#errorBtn").addEventListener("click", () =>
  runAction("Simulating error...", async () => {
    renderError(await api("/api/simulate-error"));
  }),
);

loadStatus().catch((error) => {
  statusGrid.innerHTML = metric("Backend", error.message);
});
