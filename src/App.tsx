import { useEffect, useState } from 'react';
import { MetaData } from './types';
import TodayTab from './components/TodayTab';
import DateTab from './components/DateTab';
import RankChangeTab from './components/RankChangeTab';
import CountryTab from './components/CountryTab';

type Tab = 'today' | 'date' | 'rank' | 'country';

const TABS: { id: Tab; label: string }[] = [
  { id: 'today', label: '📊 오늘 데이터' },
  { id: 'date', label: '📅 날짜별 조회' },
  { id: 'rank', label: '📈 순위 변동' },
  { id: 'country', label: '🌏 국가별 분포' },
];

export default function App() {
  const [tab, setTab] = useState<Tab>('today');
  const [dates, setDates] = useState<string[]>([]);
  const [meta, setMeta] = useState<MetaData | null>(null);

  async function loadMeta() {
    try {
      const [dRes, mRes] = await Promise.all([fetch('/api/dates'), fetch('/api/meta')]);
      if (dRes.ok) setDates(await dRes.json());
      if (mRes.ok) setMeta(await mRes.json());
    } catch { /* ignore */ }
  }

  useEffect(() => { loadMeta(); }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header className="app-header">
        <div className="app-title">
          <span>🌐</span>
          Global Market Cap
          <span style={{ color: 'var(--text3)', fontSize: 13, fontWeight: 400 }}>Top 200</span>
        </div>
        <div className="meta-info">
          {meta?.lastCollected && (
            <span>
              마지막 수집:{' '}
              <span>{new Date(meta.lastCollected).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
            </span>
          )}
          {meta?.lastRate && (
            <span>
              환율: <span>{meta.lastRate.toLocaleString()} KRW</span>
            </span>
          )}
          <span>
            누적: <span>{meta?.count ?? 0}일</span>
          </span>
        </div>
      </header>

      <nav className="tabs-bar">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab-btn${tab === t.id ? ' active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="tab-content">
        {tab === 'today' && <TodayTab onDataChange={loadMeta} />}
        {tab === 'date' && <DateTab dates={dates} />}
        {tab === 'rank' && <RankChangeTab dates={dates} />}
        {tab === 'country' && <CountryTab dates={dates} />}
      </main>
    </div>
  );
}
