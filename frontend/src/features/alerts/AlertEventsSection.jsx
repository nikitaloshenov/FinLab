import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function AlertEventsSection({ alertEvents }) {
  return (
    <section className="card">
      <div className="cardHeader">
        <div>
          <h2>Alert Events</h2>
          <p>История срабатываний alert’ов.</p>
        </div>
      </div>

      {alertEvents.length === 0 && (
        <p className="status">Событий пока нет.</p>
      )}

      {alertEvents.length > 0 && (
        <div className="tableWrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Alert</th>
                <th>Ticker</th>
                <th>Price</th>
                <th>Target</th>
                <th>Condition</th>
                <th>Created</th>
              </tr>
            </thead>

            <tbody>
              {alertEvents.map((event) => (
                <tr key={event.id}>
                  <td>#{event.id}</td>
                  <td>#{event.alert_id}</td>
                  <td className="ticker">{event.secid}</td>
                  <td>{formatPrice(event.price)}</td>
                  <td>{formatPrice(event.target_price)}</td>
                  <td>{event.condition}</td>
                  <td>{formatDate(event.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
