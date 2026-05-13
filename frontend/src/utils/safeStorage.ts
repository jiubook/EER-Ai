export function safeLoadJson<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key)
  if (!raw) return fallback

  try {
    return JSON.parse(raw) as T
  } catch (error) {
    console.warn(`Invalid localStorage value for ${key}; resetting`, error)
    localStorage.removeItem(key)
    return fallback
  }
}

export function safeSetJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.warn(`Failed to write localStorage value for ${key}`, error)
  }
}
