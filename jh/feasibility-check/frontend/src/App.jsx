import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";

const categories = [
  { value: "movie", label: "영화" },
  { value: "series", label: "시리즈" },
  { value: "music", label: "음악" },
];

function App() {
  const [serverStatus, setServerStatus] = useState("checking");
  const [category, setCategory] = useState("movie");
  const [query, setQuery] = useState("test");
  const [items, setItems] = useState([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function checkServer() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        if (!response.ok) throw new Error("서버 상태 확인에 실패했습니다.");
        setServerStatus("connected");
      } catch {
        setServerStatus("disconnected");
      }
    }

    checkServer();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setItems([]);

    if (!query.trim()) {
      setError("검색어를 입력해 주세요.");
      return;
    }

    setIsLoading(true);

    try {
      const params = new URLSearchParams({ category, q: query.trim() });
      const response = await fetch(`${API_BASE_URL}/api/search?${params}`);
      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.error?.message ?? "검색 요청에 실패했습니다.");
      }

      setItems(body.items ?? []);
      setNotice(body.meta?.notice ?? "");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "알 수 없는 오류가 발생했습니다.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  const statusText = {
    checking: "서버 확인 중",
    connected: "Flask 연결됨",
    disconnected: "Flask 연결 안 됨",
  }[serverStatus];

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#f0e7ff,_transparent_38%),linear-gradient(180deg,#fcfbfe_0%,#f5f1fa_100%)]">
      <header className="border-b border-violet-100 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-violet-600 text-xl text-white shadow-lg shadow-violet-200">
              ◌
            </div>
            <div>
              <p className="text-xs font-semibold tracking-[0.22em] text-violet-500">TASTE RADIUS</p>
              <h1 className="text-xl font-black text-slate-900">취향 반경</h1>
            </div>
          </div>
          <span
            className={`rounded-full px-3 py-1.5 text-xs font-bold ${
              serverStatus === "connected"
                ? "bg-emerald-50 text-emerald-700"
                : serverStatus === "disconnected"
                  ? "bg-rose-50 text-rose-700"
                  : "bg-slate-100 text-slate-600"
            }`}
          >
            ● {statusText}
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-12 sm:py-16">
        <section className="max-w-3xl">
          <span className="rounded-full border border-violet-200 bg-white px-3 py-1 text-xs font-bold text-violet-700">
            모의 개발 화면
          </span>
          <h2 className="mt-5 text-4xl font-black leading-tight text-slate-950 sm:text-5xl">
            좋아하는 작품을
            <br />
            검색해 보세요.
          </h2>
          <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
            Flask 검색 엔드포인트를 통해 Apple iTunes Search API와 한국어
            Wikipedia API의 실제 작품 정보를 조회합니다. 가격은 제공되는 경우의
            Apple Store 구매 가격입니다.
          </p>
        </section>

        <form
          onSubmit={handleSubmit}
          className="mt-9 grid gap-3 rounded-3xl border border-white bg-white/90 p-4 shadow-xl shadow-violet-100/70 sm:grid-cols-[150px_1fr_auto]"
        >
          <label className="sr-only" htmlFor="category">
            콘텐츠 분야
          </label>
          <select
            id="category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 font-bold text-slate-800 outline-none transition focus:border-violet-400 focus:ring-4 focus:ring-violet-100"
          >
            {categories.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>

          <label className="sr-only" htmlFor="query">
            작품 검색어
          </label>
          <input
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="작품 제목을 입력하세요"
            className="rounded-2xl border border-slate-200 px-4 py-3.5 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-100"
          />

          <button
            type="submit"
            disabled={isLoading}
            className="rounded-2xl bg-violet-600 px-6 py-3.5 font-bold text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300"
          >
            {isLoading ? "검색 중…" : "검색"}
          </button>
        </form>

        <section aria-live="polite" className="mt-7">
          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-700">
              {error}
            </div>
          )}

          {notice && (
            <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
              <strong>외부 데이터 안내:</strong> {notice}
            </div>
          )}

          {items.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <article
                  key={item.id}
                  className="overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-lg shadow-slate-200/60"
                >
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={`${item.title} 이미지`}
                      className="aspect-[16/10] w-full object-cover"
                    />
                  ) : (
                    <div className="grid aspect-[16/10] place-items-center bg-gradient-to-br from-violet-100 to-fuchsia-50 text-5xl">
                      {item.category === "music" ? "♪" : item.category === "series" ? "▣" : "▶"}
                    </div>
                  )}
                  <div className="p-5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-bold text-violet-700">
                        {categories.find((entry) => entry.value === item.category)?.label ?? item.category}
                      </span>
                      <span className="text-xs font-semibold text-emerald-700">실제 API 데이터</span>
                    </div>
                    <h3 className="mt-4 text-xl font-black text-slate-900">{item.title}</h3>
                    {item.creator && <p className="mt-2 text-sm text-slate-600">{item.creator}</p>}
                    {item.genre && <p className="mt-1 text-xs text-slate-500">{item.genre}</p>}
                    {item.summary && (
                      <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-600">{item.summary}</p>
                    )}
                    {item.price_amount != null && (
                      <p className="mt-3 text-sm font-bold text-slate-800">
                        {item.price_amount} {item.currency ?? ""}
                      </p>
                    )}
                    {item.source_url && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-4 inline-block text-sm font-bold text-violet-700 hover:underline"
                      >
                        {item.source_name} 페이지 열기 →
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}

          {!error && notice && items.length === 0 && (
            <div className="rounded-3xl border border-dashed border-violet-200 bg-white/60 px-6 py-12 text-center text-sm text-slate-500">
              검색 결과가 없습니다. 다른 제목으로 다시 검색해 주세요.
            </div>
          )}

          {!error && !notice && items.length === 0 && (
            <div className="rounded-3xl border border-dashed border-violet-200 bg-white/60 px-6 py-12 text-center text-sm text-slate-500">
              분야와 검색어를 선택한 뒤 검색 버튼을 눌러 주세요.
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
