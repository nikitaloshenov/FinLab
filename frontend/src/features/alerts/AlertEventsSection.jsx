import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function AlertEventsSection({ alertEvents }) {
  return (
    <section className="card eventsCard">
      <div className="cardHeader">
        <div>
          <h2>Alert Events</h2>
          <p>История срабатываний alert’ов.</p>
        </div>
      </div>

      {alertEvents.length === 0 && (
        <div className="emptyState compact">
          <strong>Событий пока нет</strong>
          <p>Когда alert сработает, событие появится в этом журнале.</p>
        </div>
      )}

      {alertEvents.length > 0 && (
        <div className="eventLog">
          {alertEvents.map((event) => (
            <article className="eventItem" key={event.id}>
              <div className="eventMain">
                <span className="eventTicker">{event.secid}</span>
                <strong>
                  {formatPrice(event.price)} / target {formatPrice(event.target_price)}
                </strong>
                <p>{event.message || `${event.condition} alert triggered.`}</p>
              </div>

              <div className="eventMeta">
                <span>#{event.id}</span>
                <span>Alert #{event.alert_id}</span>
                <span>{formatDate(event.created_at)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
