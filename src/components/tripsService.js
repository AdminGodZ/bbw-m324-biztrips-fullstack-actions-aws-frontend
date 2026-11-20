// Base URL of the backend service:
//   build time:  VITE_API_BASE_URL - on ECS the URL of the backend service behind the ALB
//                (GitHub Actions variable VITE_API_BASE_URL)
//   run time:    optional override from /config.js (container env API_BASE_URL), used by
//                Docker Compose ("/" -> nginx proxies /v1 and /actuator to the backend container)
const runtimeBaseUrl = globalThis.window?.__BIZTRIPS_CONFIG__?.apiBaseUrl;
export const baseUrl = (runtimeBaseUrl || import.meta.env.VITE_API_BASE_URL || "/").replace(/\/$/, "");

async function json(path) {
  const response = await fetch(`${baseUrl}${path}`);
  if (response.ok) return response.json();
  throw response;
}

export const getBusinessTrips = () => json("/v1/trips");
export const getWishlistItems = getBusinessTrips;
export const getEmployees = () => json("/v1/employees");
export const getBackendInfo = () => json("/actuator/info");

export function employeePhotoUrl(id, cacheBuster = "") {
  return `${baseUrl}/v1/employees/${id}/photo${cacheBuster ? `?v=${cacheBuster}` : ""}`;
}

export async function uploadEmployeePhoto(id, file) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${baseUrl}/v1/employees/${id}/photo`, {method: "POST", body});
  if (response.ok) return;
  let message = `Upload fehlgeschlagen (HTTP ${response.status})`;
  try {
    const problem = await response.json();
    if (problem?.detail) message = problem.detail;
  } catch {
    // body is not JSON - keep the generic message
  }
  throw new Error(message);
}
