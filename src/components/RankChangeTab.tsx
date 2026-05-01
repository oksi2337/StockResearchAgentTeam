import { useEffect, useState } from 'react';
import { StockEntry } from '../types';
import { fmtUSD, fmtChange, fmtDate, countryFlag } from '../utils';

interface Props {
  dates: string[];
}

interface CompareRow {
  ticker: string;
  name: string;
  country: string;
  sector: string;
  rankA: number;
  rankB: number;
  rankDiff: number;
  capA: number;
  capB: number;
  capChangePct: number;
}

export default function RankChangeTab({ dates }: Props) {
  const [dateA, setDateA] = useState<string>('');
  const [dateB, setDateB] = useState<string>('');
  const [dataA, setDataA] = useState<StockEntry[]>([]);
  const [dataB, setDataB] = useState<StockEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState<'rank' | 'diff' | 'cap'>('rank');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    if (dates.length >= 2) { setDateA(dates[1]); setDateB(dates[0]); }
    else if (dates.length === 1) { setDateA(dates[0]); setDateB(dates[0]); }
  }, [dates]);

  async function fetchDate(date: string): Promise<StockEntry[]> {
    if (!date) return [];
    const res = await fetch(`/api/data/${date}`);
    if (!res.ok) return [];
    const json = await res.json();
    return json.data ?? [];
  }

  useEffect(() => {
    if (!dateA || !dateB) return;
    setLoading(true);
    Promise.all([fetchDate(dateA), fetchDate(dateB)])
      .then(([a, b]) => { setDataA(a); setDataB(b); })
      .finally(() => setLoading(false));
  }, [dateA, dateB]);

  if (dates.length < 2) {
    return <div className="empty">순위 변동 비교를 위해 최소 2일 이상의 데이터가 필요합니다.</div>;
  }

  const mapA = new Map(dataA.map(d => [d.ticker, d]));
  const mapB = new Map(dataB.map(d => [d.ticker, d]));

  const allTickers = [...new Set([...mapA.keys(), ...mapB.keys()])];

  const rows: CompareRow[] = allTickers
    .filter(t => mapA.has(t) && mapB.has(t))
    .map(t => {
      const a = mapA.get(t)!;
      const b = mapB.get(t)!;
      const capChangePct = a.market_cap_usd > 0
        ? ((b.market_cap_usd - a.market_cap_usd) / a.market_cap_usd) * 100
        : 0;
      return {
        ticker: t,
        name: b.name,
        country: b.country,
        sector: b.sector,
        rankA: a.rank,
        rankB: b.rank,
        rankDiff: a.rank - b.rank,
        capA: a.market_cap_usd,
        capB: b.market_cap_usd,
        capChangePct,
      };
    });

  const sorted = [...rows].sort((x, y) => {
    let v = 0;
    if (sortBy === 'rank') v = x.rankB - y.rankB;
    else if (sortBy === 'diff') v = Math.abs(y.rankDiff) - Math.abs(x.rankDiff);
    else v = Math.abs(y.capChangePct) - Math.abs(x.capChangePct);
    return sortDir === 'asc' ? v : -v;
  });

  function toggleSort(col: 'rank' | 'diff' | 'cap') {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('asc'); }
  }

  function SortIcon({ col }: { col: 'rank' | 'diff' | 'cap' }) {
    if (sortBy !== col) return <span style={{ color: 'var(--text3)' }}> ⇅</span>;
    return <span style={{ color: 'var(--accent-hover)' }}> {sortDir === 'asc' ? '↑' : '↓'}</span>;
  }

  const bigMovers = rows.filter(r => Math.abs(r.rankDiff) >= 10).length;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>순위 변동 비교</h2>

        <div className="date-select-row">
          <label>기준일</label>
          <select value={dateA} onChange={e => setDateA(e.target.value)}>
            {dates.map(d => <option key={d} value={d}>{fmtDate(d)}</option>)}
          </select>
          <span style={{ color: 'var(--text3)' }}>→</span>
          <label>비교일</label>
          <select value={dateB} onChange={e => setDateB(e.target.value)}>
            {dates.map(d => <option key={d} value={d}>{fmtDate(d)}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="empty">로딩 중...</div>
      ) : rows.length === 0 ? (
        <div className="empty">두 날짜 모두에 있는 기업 데이터가 없습니다.</div>
      ) : (
        <>
          <div className="cards-row" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="card-label">공통 기업</div>
              <div className="card-value">{rows.length}</div>
            </div>
            <div className="card">
              <div className="card-label">10위 이상 변동</div>
              <div className="card-value">{bigMovers}</div>
            </div>
            <div className="card">
              <div className="card-label">순위 상승</div>
              <div className="card-value green">{rows.filter(r => r.rankDiff > 0).length}</div>
            </div>
            <div className="card">
              <div className="card-label">순위 하락</div>
              <div className="card-value red">{rows.filter(r => r.rankDiff < 0).length}</div>
            </div>
          </div>

          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th onClick={() => toggleSort('rank')} style={{ cursor: 'pointer' }}>
                    비교일 순위 <SortIcon col="rank" />
                  </th>
                  <th>기업명</th>
                  <th>티커</th>
                  <th>국가</th>
                  <th>섹터</th>
                  <th>기준일 순위</th>
                  <th onClick={() => toggleSort('diff')} style={{ cursor: 'pointer', textAlign: 'center' }}>
                    순위 변동 <SortIcon col="diff" />
                  </th>
                  <th className="num-right">기준일 시총</th>
                  <th className="num-right">비교일 시총</th>
                  <th onClick={() => toggleSort('cap')} style={{ cursor: 'pointer', textAlign: 'right' }}>
                    시총 변화율 <SortIcon col="cap" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {sorted.map(row => (
                  <tr key={row.ticker}>
                    <td><span className="rank">{row.rankB}</span></td>
                    <td><span className="company-name">{row.name}</span></td>
                    <td><span className="ticker">{row.ticker}</span></td>
                    <td>{countryFlag(row.country)} {row.country}</td>
                    <td>
                      <span style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 4, fontSize: 11, padding: '2px 6px', color: 'var(--text2)' }}>
                        {row.sector}
                      </span>
                    </td>
                    <td><span className="rank">{row.rankA}</span></td>
                    <td style={{ textAlign: 'center' }}>
                      {row.rankDiff > 0 ? (
                        <span className="rank-up">▲ {row.rankDiff}</span>
                      ) : row.rankDiff < 0 ? (
                        <span className="rank-down">▼ {Math.abs(row.rankDiff)}</span>
                      ) : (
                        <span className="rank-same">—</span>
                      )}
                    </td>
                    <td className="num-right">{fmtUSD(row.capA)}</td>
                    <td className="num-right">{fmtUSD(row.capB)}</td>
                    <td className={`num-right ${row.capChangePct > 0 ? 'green' : row.capChangePct < 0 ? 'red' : 'neutral'}`}>
                      {fmtChange(row.capChangePct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
