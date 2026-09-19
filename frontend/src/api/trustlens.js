const API_BASE = "http://127.0.0.1:8000"

export async function analyzeProfile(username) {
  const response = await fetch(`${API_BASE}/analyze-live`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  })

  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`)
  }

  const data = await response.json()

  if (data.error) {
    throw new Error(data.error)
  }

  return data
}

export async function transcribeUrl(url) {
  const response = await fetch(`${API_BASE}/transcribe/url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || `Server error: ${response.status}`)
  }
  if (data.error) throw new Error(data.error)
  return data
}

export async function transcribeFile(file) {
  const form = new FormData()
  form.append("file", file)
  form.append("run_misinfo", "true")

  const response = await fetch(`${API_BASE}/transcribe/upload`, {
    method: "POST",
    body: form,
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || `Server error: ${response.status}`)
  }
  if (data.error) throw new Error(data.error)
  return data
}