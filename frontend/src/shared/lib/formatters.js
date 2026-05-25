export function formatDate(value) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString("ru-RU");
}

export function formatPrice(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return value;
  }

  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numberValue);
}
