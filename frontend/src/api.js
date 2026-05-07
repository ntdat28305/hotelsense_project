// api.js — Gọi HuggingFace Spaces backend

const API_BASE = import.meta.env.VITE_API_URL || "https://ntdat232-hotel-absa-api.hf.space";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
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