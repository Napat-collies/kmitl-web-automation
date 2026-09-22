// Tiny API helpers. The search agent streams Server-Sent Events over a POST, so
// we read the response body ourselves (EventSource only supports GET).

export async function streamSearchAgent(question, defended, onEvent) {
  const resp = await fetch('/api/search-agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, defended }),
  });
  if (!resp.ok || !resp.body) throw new Error(`agent request failed (${resp.status})`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n'); // SSE events are separated by a blank line
    buffer = chunks.pop() ?? '';
    for (const chunk of chunks) {
      const line = chunk.split('\n').find((l) => l.startsWith('data: '));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
  }
}

export async function postJSON(path, body) {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    // Surface the server's actionable message (e.g. "run playwright install"), not just a status code.
    let detail = '';
    try {
      detail = (await resp.json()).detail ?? '';
    } catch {
      /* non-JSON body */
    }
    throw new Error(detail || `${path} failed (${resp.status})`);
  }
  return resp.json();
}

export async function getHealth() {
  const resp = await fetch('/api/health');
  return resp.json();
}
