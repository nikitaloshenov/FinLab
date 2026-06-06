import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function AlertEventsSection({ alertEvents }) {
  return (
    <section className="card eventsCard">
      <div className="cardHeader">
        <div>
          <h2>История алертов</h2>
          <p>Журнал срабатываний ценовых алертов.</p>
        </div>
      </div>

      {alertEvents.length === 0 && (
        <div className="emptyState compact">
          <strong>Событий пока нет</strong>
          <p>Когда алерт сработает, событие появится в этом журнале.</p>
        </div>
      )}

      {alertEvents.length > 0 && (
        <div className="eventLog">
          {alertEvents.map((event) => (
            <article className="eventItem" key={event.id}>
              <div className="eventMain">
                <span className="eventTicker">{event.secid}</span>
                <strong>
                  {formatPrice(event.price)} / цель {formatPrice(event.target_price)}
                </strong>
                <p>
                  {event.message ||
                    `Алерт с условием ${event.condition} сработал.`}
                </p>
              </div>

              <div className="eventMeta">
                <span>#{event.id}</span>
                <span>Алерт #{event.alert_id}</span>
                <span>{formatDate(event.created_at)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
