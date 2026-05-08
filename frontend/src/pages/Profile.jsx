import { useState, useEffect } from "react";
import { getHistory, getBookmarks } from "../api";

const ASPECT_LABELS = {
  Room_Facilities: "Phòng ốc", Service_Staff: "Nhân viên",
  Location: "Vị trí", Food_Beverage: "Ăn uống",
  Price_Value: "Giá cả", General: "Tổng thể",
};

const page = {
  minHeight: "100vh",
  background: "linear-gradient(135deg, #0f0c29 0%, #1a1a4e 50%, #24243e 100%)",
  fontFamily: "'Segoe UI', system-ui, sans-serif",
};

export default function Profile({ auth, onGoHome, onSelectHotel }) {
  const [tab,       setTab]       = useState("history");
  const [history,   setHistory]   = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    if (!auth.user) return;
    Promise.all([getHistory(), getBookmarks()])
      .then(([h, b]) => {
        setHistory(h.history || []);
        setBookmarks(b.bookmarks || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [auth.user]);

  const tabBtn = (id, label) => (
    <button onClick={() => setTab(id)} style={{
      padding: "8px 20px", borderRadius: 99, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, transition: "all 0.2s",
      background: tab === id ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "rgba(255,255,255,0.06)",
      color: tab === id ? "#fff" : "rgba(255,255,255,0.5)",
      boxShadow: tab === id ? "0 4px 12px rgba(124,58,237,0.3)" : "none",
    }}>{label}</button>
  );

  return (
    <div style={page}>
      {/* Navbar */}
      <nav style={{ padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div onClick={onGoHome} style={{ display: "flex", alignItems: "center", gap: 8, color: "#fff", fontWeight: 700, fontSize: 16, cursor: "pointer" }}>
          <img src="/logo.png" style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover" }} alt="logo" />
          HotelSense
        </div>
        <button onClick={auth.logout} style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 99, padding: "6px 16px", color: "rgba(255,255,255,0.6)", fontSize: 12, cursor: "pointer" }}>
          Đăng xuất
        </button>
      </nav>

      <div style={{ maxWidth: 700, margin: "0 auto", padding: "32px 20px" }}>
        {/* User info */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          {auth.user?.avatar && (
            <img src={auth.user.avatar} style={{ width: 64, height: 64, borderRadius: "50%", border: "3px solid rgba(124,58,237,0.5)" }} alt="avatar" />
          )}
          <div>
            <h2 style={{ color: "#fff", margin: "0 0 4px", fontSize: 20, fontWeight: 800 }}>{auth.user?.name}</h2>
            <p style={{ color: "rgba(255,255,255,0.45)", margin: 0, fontSize: 13 }}>{auth.user?.email}</p>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24, background: "rgba(255,255,255,0.04)", borderRadius: 99, padding: 4, width: "fit-content", border: "1px solid rgba(255,255,255,0.08)" }}>
          {tabBtn("history",   "🕐 Lịch sử tìm kiếm")}
          {tabBtn("bookmarks", "🔖 KS yêu thích")}
        </div>

        {loading ? (
          <div style={{ textAlign: "center", color: "rgba(255,255,255,0.3)", padding: "48px 0" }}>⏳ Đang tải...</div>
        ) : tab === "history" ? (
          history.length === 0 ? (
            <div style={{ textAlign: "center", color: "rgba(255,255,255,0.3)", padding: "48px 0" }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
              <p>Chưa có lịch sử tìm kiếm</p>
            </div>
          ) : (
            history.map((h, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 14, padding: "14px 18px", marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <span style={{ color: "#a78bfa", fontSize: 12, fontWeight: 600 }}>
                    {h.mode === "db" ? "🗄 Tìm từ database" : "🔗 Phân tích theo link"}
                  </span>
                  <span style={{ color: "rgba(255,255,255,0.25)", fontSize: 11 }}>{h.created_at?.slice(0, 16)}</span>
                </div>
                {h.city && <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, margin: "0 0 6px" }}>📍 {h.city}{h.district ? ` — ${h.district}` : ""}</p>}
                {h.aspects?.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {h.aspects.map(a => (
                      <span key={a} style={{ background: "rgba(124,58,237,0.2)", color: "#c4b5fd", fontSize: 11, padding: "2px 8px", borderRadius: 99 }}>
                        {ASPECT_LABELS[a] || a}
                      </span>
                    ))}
                  </div>
                )}
                {h.urls?.length > 0 && <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 11, margin: "6px 0 0" }}>{h.urls.length} link đã phân tích</p>}
              </div>
            ))
          )
        ) : (
          bookmarks.length === 0 ? (
            <div style={{ textAlign: "center", color: "rgba(255,255,255,0.3)", padding: "48px 0" }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔖</div>
              <p>Chưa có khách sạn yêu thích</p>
            </div>
          ) : (
            bookmarks.map((b, i) => (
              <div key={i} onClick={() => b.hotel_id && onSelectHotel({ id: b.hotel_id, name: b.hotel_name, city: b.city, url: b.hotel_url, match_score: b.match_score })}
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 14, padding: "14px 18px", marginBottom: 10, cursor: b.hotel_id ? "pointer" : "default", transition: "all 0.2s" }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.07)"}
                onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.04)"}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <p style={{ color: "#fff", fontWeight: 600, fontSize: 14, margin: "0 0 4px" }}>{b.hotel_name}</p>
                    <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, margin: 0 }}>📍 {b.city}</p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ color: "#4ade80", fontWeight: 700, fontSize: 18 }}>{Math.round(b.match_score)}%</div>
                    <div style={{ color: "rgba(255,255,255,0.25)", fontSize: 11 }}>{b.created_at?.slice(0, 10)}</div>
                  </div>
                </div>
              </div>
            ))
          )
        )}
      </div>
    </div>
  );
}