// api.js — Gọi HuggingFace Spaces backend

const API_BASE = import.meta.env.VITE_API_URL || "https://ntdat232-hotel-absa-api.hf.space";

const HF_TOKEN = import.meta.env.VITE_HF_TOKEN || "";

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (HF_TOKEN) headers["Authorization"] = `Bearer ${HF_TOKEN}`;
  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// Chế độ 1 — Tìm từ database sẵn
export async function searchHotels({ city, district, userRequest, priorityAspects, minScore = 0 }) {
  const params = new URLSearchParams({ city, min_score: minScore });
  if (district)         params.append("district", district);
  if (userRequest)      params.append("user_request", userRequest);
  if (priorityAspects?.length) params.append("priority_aspects", priorityAspects.join(","));
  return request(`/hotels/search?${params}`);
}

// Chế độ 2 — Phân tích URLs tùy chọn
export async function analyzeUrls({ urls, maxReviews, models, userRequest, priorityAspects }) {
  return request("/hotels/analyze-urls", {
    method: "POST",
    body: JSON.stringify({
      urls,
      max_reviews:      maxReviews,
      model_type:       models?.[0] || "phobert",
      models:           models || [],
      user_request:     userRequest,
      priority_aspects: priorityAspects || [],
    }),
  });
}

// Chi tiết khách sạn
export async function getHotelDetail(hotelId) {
  return request(`/hotels/${hotelId}`);
}

// Reviews của khách sạn
export async function getHotelReviews(hotelId, { aspect, sentiment, limit = 50 } = {}) {
  const params = new URLSearchParams({ limit });
  if (aspect)    params.append("aspect", aspect);
  if (sentiment) params.append("sentiment", sentiment);
  return request(`/hotels/${hotelId}/reviews?${params}`);
}

// Danh sách thành phố
export async function getCities() {
  return request("/cities");
}

// Danh sách quận theo thành phố
export async function getDistricts(city) {
  return request(`/districts/${encodeURIComponent(city)}`);
}

// Thống kê DB
export async function getStats() {
  return request("/stats");
}

// ── Auth header helper ───────────────────────────────────────────────
function authHeaders() {
  const token = localStorage.getItem("hs_token");
  return token ? { "Content-Type": "application/json", "Authorization": `Bearer ${token}` } : { "Content-Type": "application/json" };
}

async function authRequest(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ── History ──────────────────────────────────────────────────────────
export async function saveHistory(meta) {
  return authRequest("/user/history", { method: "POST", body: JSON.stringify(meta) });
}

export async function getHistory() {
  return authRequest("/user/history");
}

// ── Bookmarks ────────────────────────────────────────────────────────
export async function addBookmark(hotel) {
  return authRequest("/user/bookmarks", { method: "POST", body: JSON.stringify({
    hotel_id:    hotel.id || 0,
    hotel_name:  hotel.name || "",
    hotel_url:   hotel.url || "",
    city:        hotel.city || "",
    match_score: hotel.match_score || 0,
  })});
}

export async function removeBookmark(hotelId) {
  return authRequest(`/user/bookmarks/${hotelId}`, { method: "DELETE" });
}

export async function getBookmarks() {
  return authRequest("/user/bookmarks");
}

export async function checkBookmark(hotelId) {
  return authRequest(`/user/bookmarks/${hotelId}/check`);
}