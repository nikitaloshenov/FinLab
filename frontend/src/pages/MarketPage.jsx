import { useEffect, useState } from "react";

import { getWatchlist } from "../features/watchlist/api.js";

export function MarketPage() {
  const [watchlist, setWatchlist] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function loadWatchlist() {
      try {
        setIsLoading(true);
        setErrorMessage("");

        const data = await getWatchlist();

        setWatchlist(data);
      } catch (error) {
        setErrorMessage(error.message);
      } finally {
        setIsLoading(false);
      }
    }

    loadWatchlist();
  }, []);

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">FinLab</p>
        <h1>Market Watchlist</h1>
        <p className="heroText">
          Первый frontend-экран: React получает watchlist из FastAPI backend.
        </p>
      </section>

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2>Watchlist</h2>
            <p>Тикеры, которые сейчас отслеживаются в системе.</p>
          </div>
        </div>

        {isLoading && <p className="status">Загрузка watchlist...</p>}

        {errorMessage && (
          <div className="error">
            <strong>Ошибка загрузки</strong>
            <p>{errorMessage}</p>
          </div>
        )}

        {!isLoading && !errorMessage && watchlist.length === 0 && (
          <p className="status">Watchlist пока пустой.</p>
        )}

        {!isLoading && !errorMessage && watchlist.length > 0 && (
          <div className="tableWrapper">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Name</th>
                  <th>Last price</th>
                  <th>Added at</th>
                </tr>
              </thead>

              <tbody>
                {watchlist.map((item) => (
                  <tr key={item.id}>
                    <td className="ticker">{item.secid}</td>
                    <td>{item.short_name || "—"}</td>
                    <td>{item.latest_price || "—"}</td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString("ru-RU");
}