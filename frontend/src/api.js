export class ApiError extends Error {
  constructor(status, body, text) {
    const detail = body && typeof body === 'object' ? body.detail : null
    super(detail ? (detail.message || JSON.stringify(detail)) : text)
    this.status = status
    this.body = body
  }
}

async function parseJSON(r) {
  const text = await r.text()
  let body = null
  if (text) {
    try { body = JSON.parse(text) } catch { body = null }
  }
  if (!r.ok) throw new ApiError(r.status, body, text)
  return body
}

export async function getJSON(path) {
  return parseJSON(await fetch(path))
}
export async function postJSON(path, body) {
  return parseJSON(await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }))
}
