export interface StockEntry {
  rank: number;
  name: string;
  ticker: string;
  exchange: string;
  country: string;
  sector: string;
  market_cap_usd: number;
  market_cap_krw: number;
  price_usd: number;
  change_1d_pct: number;
  collected_at: string;
}

export interface DayData {
  date: string;
  rate: number;
  data: StockEntry[];
}

export interface MetaData {
  lastCollected: string | null;
  lastRate: number | null;
  count: number;
}

export type Sector = 'All' | 'Technology' | 'Finance' | 'Healthcare' | 'Energy' | 'Consumer' | 'Industrial' | 'Other';

export const SECTORS: Sector[] = [
  'All', 'Technology', 'Finance', 'Healthcare', 'Energy', 'Consumer', 'Industrial', 'Other',
];
