const money = new Intl.NumberFormat("nl-BE", { style: "currency", currency: "EUR" });
const moneyRound = new Intl.NumberFormat("nl-BE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Belgian money format: € 2.450,00 */
export const eur = (x: number, round = false) => (round ? moneyRound : money).format(x);

export function day(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

export function month(iso: string) {
  const [y, m] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

export const TODAY = "2026-09-30";
