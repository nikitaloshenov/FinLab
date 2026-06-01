import { useMemo, useState } from "react";

import {
  MARKET_UNIVERSE,
  MARKET_UNIVERSE_SECTORS,
} from "../../shared/lib/marketUniverse.js";

export function MarketUniverseQuickAdd({
  watchlist,
  onAddTicker,
  isDisabled,
}) {
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("All");

  const addedTickers = useMemo(
    () => new Set(watchlist.map((item) => item.secid)),
    [watchlist]
  );

  const filteredTickers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return MARKET_UNIVERSE.filter((item) => {
      const matchesSector = sector === "All" || item.sector === sector;

      if (!matchesSector) {
        return false;
      }

      if (!normalizedQuery) {
        return true;
      }

      return [item.secid, item.name, item.sector]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    });
  }, [query, sector]);

  return (
    <div className="universePanel">
      <div className="universeHeader">
        <div>
          <h3>Market universe</h3>
          <p>Быстро добавь популярный MOEX ticker.</p>
        </div>
      </div>

      <div className="universeToolbar">
        <input
          className="universeSearch"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search ticker, name, sector"
        />

        <select
          className="universeSectorSelect"
          value={sector}
          onChange={(event) => setSector(event.target.value)}
        >
          <option value="All">All sectors</option>
          {MARKET_UNIVERSE_SECTORS.map((sectorName) => (
            <option key={sectorName} value={sectorName}>
              {sectorName}
            </option>
          ))}
        </select>
      </div>

      {filteredTickers.length === 0 ? (
        <div className="emptyState compact">
          <strong>No tickers found</strong>
          <p>Попробуй другой запрос или сектор.</p>
        </div>
      ) : (
        <div className="universeList">
          {filteredTickers.map((item) => {
            const isAdded = addedTickers.has(item.secid);

            return (
              <article className="universeItem" key={item.secid}>
                <div className="universeInfo">
                  <strong className="universeTicker">{item.secid}</strong>
                  <span className="universeName">{item.name}</span>
                  <span className="universeSector">{item.sector}</span>
                </div>

                <button
                  className={isAdded ? "universeAddedState" : "universeAddButton"}
                  type="button"
                  disabled={isDisabled || isAdded}
                  onClick={() => onAddTicker(item.secid)}
                >
                  {isAdded ? "Added" : "Add"}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
