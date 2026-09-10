// A persistent per-browser device identifier, sent as the X-Device-Id
// header on every API request (see api.ts) so Event Logs can show
// "which device did this" alongside the actor and IP address.
//
// Note: a web browser cannot expose a real hardware/PC serial number --
// that information is deliberately blocked from web pages for security
// and privacy reasons. This identifies "this browser on this machine"
// (it resets if the user clears site data or uses a different browser/
// profile), which is the closest equivalent a web app can capture.
const STORAGE_KEY = 'websoft_device_id'

function randomId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  // Fallback for older browsers without crypto.randomUUID.
  return `dev-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getDeviceId(): string {
  try {
    let id = localStorage.getItem(STORAGE_KEY)
    if (!id) {
      id = randomId()
      localStorage.setItem(STORAGE_KEY, id)
    }
    return id
  } catch {
    // Private browsing / storage blocked -- fall back to a per-session
    // (non-persistent) id rather than sending nothing.
    return randomId()
  }
}
