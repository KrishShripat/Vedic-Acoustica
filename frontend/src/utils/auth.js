const TOKEN_KEY = 'va_token'
const USER_KEY = 'va_user'

export const getToken = () => localStorage.getItem(TOKEN_KEY)

export const getUser = () => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY))
  } catch {
    return null
  }
}

export const setAuth = ({ token, user }) => {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export const clearAuth = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// fetch() wrapper that attaches the DRF token header when present.
export const authFetch = (path, options = {}) => {
  const headers = new Headers(options.headers || {})
  const token = getToken()
  if (token) headers.set('Authorization', `Token ${token}`)
  return fetch(path, { ...options, headers })
}

const isNetworkError = (err) =>
  err instanceof TypeError ||
  err?.name === 'TypeError' ||
  /failed to fetch/i.test(err?.message || '')

// Retries transient network failures (HF Space cold start / dropped proxy
// connection). Only retries when the request never produced an HTTP response,
// so non-idempotent requests are still safe to repeat.
export const authFetchWithRetry = async (path, options = {}, { attempts = 3, baseDelayMs = 1500 } = {}) => {
  let lastErr
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      return await authFetch(path, options)
    } catch (err) {
      lastErr = err
      if (!isNetworkError(err) || attempt === attempts) break
      await new Promise(resolve => setTimeout(resolve, baseDelayMs * attempt))
    }
  }
  throw lastErr
}