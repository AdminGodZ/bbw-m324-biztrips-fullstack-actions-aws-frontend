const baseUrl = (import.meta.env.VITE_API_BASE_URL || "/").replace(/\/$/, "");

export async function getBusinessTrips() {
  const response = await fetch(`${baseUrl}/v1/trips`);
  if (response.ok) return response.json();
  throw response;
}

export const getWishlistItems = getBusinessTrips;
