export function fmtUSD(usd: number): string {
  if (usd >= 1e12) return `$${(usd / 1e12).toFixed(2)}T`;
  if (usd >= 1e9) return `$${(usd / 1e9).toFixed(1)}B`;
  if (usd >= 1e6) return `$${(usd / 1e6).toFixed(0)}M`;
  return `$${usd.toFixed(0)}`;
}

export function fmtKRW(krw: number): string {
  if (krw >= 1e16) return `₩${(krw / 1e16).toFixed(0)}경`;
  if (krw >= 1e12) return `₩${(krw / 1e12).toFixed(0)}조`;
  if (krw >= 1e8) return `₩${(krw / 1e8).toFixed(0)}억`;
  return `₩${krw.toLocaleString()}`;
}

export function fmtChange(pct: number): string {
  if (isNaN(pct)) return '—';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

export function fmtDate(iso: string): string {
  return iso.replace(/-/g, '.');
}

export function countryFlag(iso2: string): string {
  if (!iso2 || iso2.length !== 2) return '';
  const base = 0x1f1e6;
  return String.fromCodePoint(base + iso2.toUpperCase().charCodeAt(0) - 65) +
    String.fromCodePoint(base + iso2.toUpperCase().charCodeAt(1) - 65);
}
