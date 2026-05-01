import { useEffect, useState } from 'react';
import { StockEntry, Sector, SECTORS } from '../types';
import { fmtUSD, fmtKRW, fmtChange, countryFlag } from '../utils';
import CollectButton from './CollectButton';

interface Props {
  onDataChange: () => void;
}

export default function TodayTab({ onDataChange }: Props) {
  const [data, setData] = useState<StockEntry[]>([]);
  const [rate, setRate] = useState<number | null>(null);
  const [sector, setSector] = useState<Sector>('All');
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState<string>('');

  const today = new Date().toISOString().split('T')[0];

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`/api/data/${today}`);
      if (res.ok) {
        const json = await res.json();
        setData(json.data ?? []);
        setRate(json.rate ?? null);
        setDate(json.date ?? today);
      } else {
        setData([]);
      }
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const handleDone = () => { load(); onDataChange(); };

  const filtered = sector === 'All' ? data : data.filter(d => d.sector === sector);

  const totalUSD = data.reduce((s, d) => s + (d.market_cap_usd || 0), 0);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
            오늘 데이터
            {date && <span style={{ color: 'var(--text2)', fontSize: 13, marginLeft: 8, fontWeight: 400 }}>{date}</span>}
          </h2>
          {rate && <span style={{ color: 'var(--text3)', fontSize: 12 }}>환율 {rate.toLocaleString()} KRW/USD</span>}
        </div>
        <CollectButton onDone={handleDone} />
      </div>

      {!loading && data.length > 0 && (
        <div className="cards-row">
          <div className="card">
            <div className="card-label">기업 수</div>
            <div className="card-value">{data.length}</div>
            <div className="card-sub">Top {data.length}</div>
          </div>
          <div className="card">
            <div className="card-label">총 시가총액</div>
            <div className="card-value">{fmtUSD(totalUSD)}</div>
            <div className="card-sub">{fmtKRW(totalUSD * (rate ?? 1350))}</div>
          </div>
          <div className="card">
            <div className="card-label">환율</div>
            <div className="card-value">{rate ? rate.toLocaleString() : '—'}</div>
            <div className="card-sub">KRW / USD</div>
          </div>
        </div>
      )}

      <div className="sector-filters">
        {SECTORS.map(s => (
          <button
            key={s}
            className={`sector-pill${sector === s ? ' active' : ''}`}
            onClick={() => setSector(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="empty">로딩 중...</div>
      ) : filtered.length === 0 ? (
        <div className="empty">
          {data.length === 0
            ? '아직 수집된 데이터가 없습니다. "오늘 데이터 수집" 버튼을 눌러 수집하세요.'
            : `${sector} 섹터 데이터가 없습니다.`}
        </div>
      ) : (
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
              {filtered.map(row => {
                const chg = Number(row.change_1d_pct);
                return (
                  <tr key={row.rank}>
                    <td><span className="rank">{row.rank}</span></td>
                    <td><span className="company-name">{row.name}</span></td>
                    <td><span className="ticker">{row.ticker}</span></td>
                    <td style={{ color: 'var(--text2)' }}>{row.exchange}</td>
                    <td>
                      <span title={row.country}>
                        {countryFlag(row.country)} {row.country}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        background: 'var(--bg3)',
                        border: '1px solid var(--border)',
                        borderRadius: 4,
                        fontSize: 11,
                        padding: '2px 6px',
                        color: 'var(--text2)',
                        whiteSpace: 'nowrap',
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
      )}
    </div>
  );
}
