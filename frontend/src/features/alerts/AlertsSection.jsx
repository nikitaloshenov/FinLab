import { formatDate, formatPrice } from "../../shared/lib/formatters.js";

export function AlertsSection({
  alerts,
  alertTicker,
  alertCondition,
  alertTargetPrice,
  onAlertTickerChange,
  onAlertConditionChange,
  onAlertTargetPriceChange,
  onCreateAlert,
  onCheckAlert,
  onCheckAllActiveAlerts,
  onDeleteAlert,
  isLoading,
  isActionLoading,
  isCheckingAllAlerts,
  checkingAlerts,
}) {
  const activeAlertsCount = alerts.filter((alert) => alert.is_active).length;

  return (
    <section className="card alertsCard">
      <div className="cardHeader">
        <div>
          <h2>Price Alerts</h2>
          <p>Создай правило: цена выше или ниже заданного уровня.</p>
        </div>

        <button
          className="secondaryButton"
          type="button"
          disabled={
            isLoading ||
            isActionLoading ||
            isCheckingAllAlerts ||
            activeAlertsCount === 0
          }
          onClick={onCheckAllActiveAlerts}
        >
          {isCheckingAllAlerts ? "Checking..." : "Check all active alerts"}
        </button>
      </div>

      <form className="alertForm" onSubmit={onCreateAlert}>
        <input
          value={alertTicker}
          onChange={(event) => onAlertTickerChange(event.target.value)}
          placeholder="Ticker: SBER"
          disabled={isActionLoading}
        />

        <select
          value={alertCondition}
          onChange={(event) => onAlertConditionChange(event.target.value)}
          disabled={isActionLoading}
        >
          <option value="above">above</option>
          <option value="below">below</option>
        </select>

        <input
          value={alertTargetPrice}
          onChange={(event) => onAlertTargetPriceChange(event.target.value)}
          placeholder="Target price"
          disabled={isActionLoading}
        />

        <button className="primaryButton" type="submit" disabled={isActionLoading}>
          {isActionLoading ? "Loading..." : "Create alert"}
        </button>
      </form>

      {alerts.length === 0 && (
        <div className="emptyState compact">
          <strong>Alert'ов пока нет</strong>
          <p>Создай alert, чтобы отслеживать price events по тикеру.</p>
        </div>
      )}

      {alerts.length > 0 && (
        <div className="tableWrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Ticker</th>
                <th>Condition</th>
                <th>Target</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {alerts.map((alert) => {
                const isChecking = checkingAlerts.includes(alert.id);

                return (
                  <tr key={alert.id}>
                    <td>#{alert.id}</td>
                    <td className="ticker">{alert.secid}</td>
                    <td>{alert.condition}</td>
                    <td>{formatPrice(alert.target_price)}</td>
                    <td>
                      <span
                        className={
                          alert.is_active ? "statusBadge" : "statusBadge muted"
                        }
                      >
                        {alert.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                    <td>{formatDate(alert.created_at)}</td>
                    <td>
                      <div className="rowActions">
                        <button
                          className="subtleButton"
                          type="button"
                          disabled={
                            isActionLoading ||
                            isCheckingAllAlerts ||
                            isChecking ||
                            !alert.is_active
                          }
                          onClick={() => onCheckAlert(alert.id)}
                        >
                          {isChecking ? "..." : "Check"}
                        </button>

                        <button
                          className="dangerButton"
                          type="button"
                          disabled={
                            isActionLoading ||
                            isCheckingAllAlerts ||
                            isChecking
                          }
                          onClick={() => onDeleteAlert(alert.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
