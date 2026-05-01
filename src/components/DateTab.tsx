import { useEffect, useState } from 'react';
import { StockEntry } from '../types';
import { fmtUSD, fmtKRW, fmtChange, fmtDate, countryFlag } from '../utils';

interface Props {
  dates: string[];
}

export default function DateTab({ dates }: Props) {
  const [selected, setSelected] = useState<string>('');
  const [data, setData] = useState<StockEntry[]>([]);
  const [rate, setRate] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (dates.length > 0 && !selected) setSelected(dates[0]);
  }, [dates]);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetch(`/api/data/${selected}`)
      .then(r => r.json())
      .then(json => { setData(json.data ?? []); setRate(json.rate ?? null); })
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [selected]);

  if (dates.length === 0) {
    return <div className="empty">저장된 날짜 데이터가 없습니다. 먼저 데이터를 수집하세요.</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>날짜별 조회</h2>
        <div className="date-grid">
          {dates.map(d => (
            <button
              key={d}
              className={`date-btn${selected === d ? ' active' : ''}`}
              onClick={() => setSelected(d)}
            >
              {fmtDate(d)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="empty">로딩 중...</div>
      ) : data.length === 0 ? (
        <div className="empty">데이터가 없습니다.</div>
      ) : (
        <>
          <div className="cards-row" style={{ marginBottom: 16 }}>
            <div className="card">
              <div className="card-label">날짜</div>
              <div className="card-value" style={{ fontSize: 16 }}>{fmtDate(selected)}</div>
            </div>
            <div className="card">
              <div className="card-label">기업 수</div>
              <div className="card-value">{data.length}</div>
            </div>
            <div className="card">
              <div className="card-label">총 시총</div>
              <div className="card-value">{fmtUSD(data.reduce((s, d) => s + (d.market_cap_usd || 0), 0))}</div>
            </div>
            {rate && (
              <div className="card">
                <div className="card-label">환율</div>
                <div className="card-value">{rate.toLocaleString()}</div>
                <div className="card-sub">KRW / USD</div>
              </div>
            )}
          </div>

          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 40 }}>#</th>
                  <th>기업명</th>
                  <th>티커</th>
                  <th>거래소</th>
                  <th>국가</th>
                  <th>섹터</th>
                  <th className="num-right">시총 (USD)</th>
                  <th className="num-right">시총 (KRW)</th>
                  <th className="num-right">주가 (USD)</th>
                  <th className="num-right">등락률</th>
                </tr>
              </thead>
              <tbody>
                {data.map(row => {
                  const chg = Number(row.change_1d_pct);
                  return (
                    <tr key={row.rank}>
                      <td><span className="rank">{row.rank}</span></td>
                      <td><span className="company-name">{row.name}</span></td>
                      <td><span className="ticker">{row.ticker}</span></td>
                      <td style={{ color: 'var(--text2)' }}>{row.exchange}</td>
                      <td>{countryFlag(row.country)} {row.country}</td>
                      <td>
                        <span style={{
                          background: 'var(--bg3)',
                          border: '1px solid var(--border)',
                          borderRadius: 4,
                          fontSize: 11,
                          padding: '2px 6px',
                          color: 'var(--text2)',
                        }}>
                          {row.sector}
                        </span>
                      </td>
                      <td className="num-right">{fmtUSD(row.market_cap_usd)}</td>
                      <td className="num-right">{fmtKRW(row.market_cap_krw)}</td>
                      <td className="num-right">${Number(row.price_usd).toFixed(2)}</td>
                      <td className={`num-right ${chg > 0 ? 'green' : chg < 0 ? 'red' : 'neutral'}`}>
                        {fmtChange(chg)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
