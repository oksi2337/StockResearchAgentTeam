import { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts';
import { StockEntry } from '../types';
import { fmtUSD, fmtDate, countryFlag } from '../utils';

interface Props {
  dates: string[];
}

interface CountryStat {
  country: string;
  flag: string;
  count: number;
  totalUSD: number;
  share: number;
}

const COLORS = [
  '#388bfd', '#3fb950', '#d29922', '#f85149', '#bc8cff',
  '#58a6ff', '#56d364', '#e3b341', '#ff7b72', '#d2a8ff',
  '#79c0ff', '#7ee787', '#f0883e', '#ffa657', '#a5d6ff',
];

export default function CountryTab({ dates }: Props) {
  const [selected, setSelected] = useState<string>('');
  const [data, setData] = useState<StockEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (dates.length > 0 && !selected) setSelected(dates[0]);
  }, [dates]);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetch(`/api/data/${selected}`)
      .then(r => r.json())
      .then(json => setData(json.data ?? []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [selected]);

  if (dates.length === 0) {
    return <div className="empty">저장된 데이터가 없습니다.</div>;
  }

  const totalUSD = data.reduce((s, d) => s + (d.market_cap_usd || 0), 0);

  const countryMap = new Map<string, CountryStat>();
  for (const row of data) {
    const c = row.country || 'XX';
    const existing = countryMap.get(c);
    if (existing) {
      existing.count++;
      existing.totalUSD += row.market_cap_usd || 0;
    } else {
      countryMap.set(c, { country: c, flag: countryFlag(c), count: 1, totalUSD: row.market_cap_usd || 0, share: 0 });
    }
  }

  const stats: CountryStat[] = [...countryMap.values()]
    .map(s => ({ ...s, share: totalUSD > 0 ? (s.totalUSD / totalUSD) * 100 : 0 }))
    .sort((a, b) => b.totalUSD - a.totalUSD);

  const top15 = stats.slice(0, 15);
  const others = stats.slice(15);
  const otherTotal = others.reduce((s, d) => s + d.totalUSD, 0);

  const pieData = [
    ...top15.map(s => ({ name: `${s.flag} ${s.country}`, value: s.totalUSD, share: s.share })),
    ...(otherTotal > 0 ? [{ name: '기타', value: otherTotal, share: (otherTotal / totalUSD) * 100 }] : []),
  ];

  const barData = top15.map(s => ({
    name: `${s.flag} ${s.country}`,
    시총: Math.round(s.totalUSD / 1e9),
    기업수: s.count,
  }));

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { name: string; value: number; payload: { share: number } }[] }) => {
    if (!active || !payload?.length) return null;
    const { name, value, payload: p } = payload[0];
    return (
      <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 4 }}>{name}</div>
        <div style={{ color: 'var(--text2)' }}>{fmtUSD(value * 1e9)}</div>
        <div style={{ color: 'var(--text3)' }}>{p.share?.toFixed(1)}%</div>
      </div>
    );
  };

  const PieTooltip = ({ active, payload }: { active?: boolean; payload?: { name: string; value: number; payload: { share: number } }[] }) => {
    if (!active || !payload?.length) return null;
    const { name, value, payload: p } = payload[0];
    return (
      <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 4 }}>{name}</div>
        <div style={{ color: 'var(--text2)' }}>{fmtUSD(value)}</div>
        <div style={{ color: 'var(--text3)' }}>{p.share?.toFixed(1)}%</div>
      </div>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>국가별 분포</h2>
        <div className="date-grid">
          {dates.map(d => (
            <button key={d} className={`date-btn${selected === d ? ' active' : ''}`} onClick={() => setSelected(d)}>
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
          <div className="cards-row" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="card-label">국가 수</div>
              <div className="card-value">{stats.length}</div>
            </div>
            <div className="card">
              <div className="card-label">상위 국가</div>
              <div className="card-value" style={{ fontSize: 16 }}>{stats[0]?.flag} {stats[0]?.country}</div>
              <div className="card-sub">{stats[0]?.share.toFixed(1)}% 비중</div>
            </div>
            <div className="card">
              <div className="card-label">상위 3개국 비중</div>
              <div className="card-value">{stats.slice(0, 3).reduce((s, d) => s + d.share, 0).toFixed(1)}%</div>
            </div>
          </div>

          <div className="charts-row">
            <div className="chart-box" style={{ minHeight: 360 }}>
              <div className="chart-title">국가별 시총 비중 (파이차트)</div>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={120}
                    paddingAngle={1}
                    dataKey="value"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="var(--bg)" strokeWidth={1} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 12px', marginTop: 8 }}>
                {pieData.slice(0, 12).map((d, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text2)' }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: COLORS[i % COLORS.length], display: 'inline-block', flexShrink: 0 }} />
                    {d.name} ({d.share.toFixed(1)}%)
                  </div>
                ))}
              </div>
            </div>

            <div className="chart-box" style={{ minHeight: 360 }}>
              <div className="chart-title">Top 15 국가 시총 (단위: 십억 USD)</div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={barData} margin={{ top: 0, right: 10, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: 'var(--text3)', fontSize: 11 }}
                    angle={-35}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fill: 'var(--text3)', fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text2)' }} />
                  <Bar dataKey="시총" fill="#388bfd" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ marginTop: 20 }}>
            <div className="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>#</th>
                    <th>국가</th>
                    <th className="num-right">기업 수</th>
                    <th className="num-right">총 시총 (USD)</th>
                    <th className="num-right">비중 (%)</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.map((s, i) => (
                    <tr key={s.country}>
                      <td><span className="rank">{i + 1}</span></td>
                      <td>
                        <span style={{ fontSize: 18, marginRight: 6 }}>{s.flag}</span>
                        <span style={{ fontWeight: 600 }}>{s.country}</span>
                      </td>
                      <td className="num-right">{s.count}</td>
                      <td className="num-right">{fmtUSD(s.totalUSD)}</td>
                      <td className="num-right">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                          <div style={{
                            height: 4,
                            width: Math.max(4, s.share * 2),
                            background: COLORS[i % COLORS.length],
                            borderRadius: 2,
                          }} />
                          {s.share.toFixed(2)}%
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
