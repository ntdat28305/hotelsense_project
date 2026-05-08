import { useState, useEffect } from "react";
import Home    from "./pages/Home";
import Results from "./pages/Results";
import Detail  from "./pages/Detail";
import { useAuth } from "./hooks/useAuth";
import "./index.css";

export default function App() {
  const [page,          setPage]          = useState("home");
  const [results,       setResults]       = useState(null);
  const [selectedHotel, setSelectedHotel] = useState(null);
  const [searchMeta,    setSearchMeta]    = useState(null);
  const auth = useAuth();

  useEffect(() => {
    window.history.replaceState({ page: "home" }, "");
    const handlePop = (e) => {
      const p = e.state?.page || "home";
      setPage(p);
    };
    window.addEventListener("popstate", handlePop);
    return () => window.removeEventListener("popstate", handlePop);
  }, []);

  function goResults(data, meta) {
    setResults(data); setSearchMeta(meta);
    setPage("results");
    window.history.pushState({ page: "results" }, "");
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

  return (
    <>
      {page === "home"    && <Home    onSearch={goResults} auth={auth} />}
      {page === "results" && <Results results={results} meta={searchMeta} onSelect={goDetail} onBack={goHome} auth={auth} />}
      {page === "detail"  && <Detail  hotel={selectedHotel} onBack={goBack} onGoHome={goHome} auth={auth} />}
    </>
  );
}