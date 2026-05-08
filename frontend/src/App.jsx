import { useState, useEffect } from "react";
import Home    from "./pages/Home";
import Results from "./pages/Results";
import Detail  from "./pages/Detail";
import Profile from "./pages/Profile";
import { useAuth } from "./hooks/useAuth";
import { saveHistory } from "./api";
import "./index.css";

export default function App() {
  const [page,          setPage]          = useState("home");
  const [results,       setResults]       = useState(null);
  const [selectedHotel, setSelectedHotel] = useState(null);
  const [searchMeta,    setSearchMeta]    = useState(null);
  const auth = useAuth();

  useEffect(() => {
    window.history.replaceState({ page: "home" }, "");
    const handlePop = (e) => setPage(e.state?.page || "home");
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  function goResults(data, meta) {
    setResults(data); setSearchMeta(meta);
    setPage("results");
    window.history.pushState({ page: "results" }, "");
    // Luu lich su neu da dang nhap
    if (auth.user) saveHistory(meta).catch(() => {});
  }

  function goDetail(hotel) {
    setSelectedHotel(hotel);
    setPage("detail");
    window.history.pushState({ page: "detail" }, "");
  }

  function goHome() {
    setPage("home");
    window.history.pushState({ page: "home" }, "");
  }

  function goBack() {
    setPage("results");
    window.history.pushState({ page: "results" }, "");
  }

  function goProfile() {
    setPage("profile");
    window.history.pushState({ page: "profile" }, "");
  }

  return (
    <>
      {page === "home"    && <Home    onSearch={goResults} auth={auth} onProfile={goProfile} />}
      {page === "results" && <Results results={results} meta={searchMeta} onSelect={goDetail} onBack={goHome} auth={auth} onProfile={goProfile} />}
      {page === "detail"  && <Detail  hotel={selectedHotel} onBack={goBack} onGoHome={goHome} auth={auth} />}
      {page === "profile" && <Profile auth={auth} onGoHome={goHome} onSelectHotel={goDetail} />}
    </>
  );
}