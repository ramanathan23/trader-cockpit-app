/**
 * Read an SSE stream to completion.
 * Resolves with the final `ok` message, or rejects on error/close.
 * Calls `onProgress` for each intermediate `running` event.
 */
export async function readSSE(
  endpoint: string,
  method: string,
  onProgress: (msg: string) => void,
): Promise<string> {
  const res = await fetch(endpoint, { method });
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail ?? data?.message ?? `HTTP ${res.status}`);
  }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) throw new Error('SSE stream closed without completion event');
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      let evt: { status: string; message?: string };
      try { evt = JSON.parse(line.slice(6)); } catch { continue; }
      if (evt.status === 'running' && evt.message) onProgress(evt.message);
      else if (evt.status === 'ok')    return evt.message ?? 'done';
      else if (evt.status === 'error') throw new Error(evt.message ?? 'failed');
    }
  }
}
