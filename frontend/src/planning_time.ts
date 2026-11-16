export function localDateTime(value: string, timezone: string) {
  if (!value || !/(Z|[+-]\d\d:\d\d)$/.test(value)) return value;
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(value));
  const get = (name: string) =>
    parts.find((item) => item.type === name)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}
export function dayInZone(timezone: string) {
  try {
    return new Intl.DateTimeFormat("sv-SE", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}
export function addDays(day: string, amount: number) {
  const value = new Date(day + "T12:00:00Z");
  value.setUTCDate(value.getUTCDate() + amount);
  return value.toISOString().slice(0, 10);
}
export function weekStart(day: string) {
  return addDays(day, -(new Date(day + "T12:00:00Z").getUTCDay() + 6) % 7);
}
export function displayTime(value: string, timezone: string) {
  try {
    return new Date(value).toLocaleString("pt-BR", {
      timeZone: timezone,
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return value + " · fuso inválido, corrija nas configurações";
  }
}
