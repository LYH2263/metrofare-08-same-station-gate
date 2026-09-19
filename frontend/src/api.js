export async function getJSON(path) {
  const r = await fetch(path)
  if (!r.ok) throw await toError(r)
  return r.json()
}
export async function postJSON(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw await toError(r)
  return r.json()
}

async function toError(r) {
  // 后端结构化错误体：{ error, message, ... }；解析失败时退回纯文本。
  let data = null
  const text = await r.text()
  try { data = text ? JSON.parse(text) : null } catch { data = null }
  const message = (data && data.message) || text || `请求失败 (${r.status})`
  const err = new Error(message)
  err.status = r.status
  err.data = data
  return err
}
