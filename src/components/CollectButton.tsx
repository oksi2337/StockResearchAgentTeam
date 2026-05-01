import { useState, useRef, useEffect } from 'react';

interface StreamEvent {
  status: 'starting' | 'searching' | 'processing' | 'streaming' | 'done' | 'error' | 'exists';
  message?: string;
  chunk?: string;
  date?: string;
  count?: number;
  rate?: number;
}

interface Props {
  onDone: () => void;
}

export default function CollectButton({ onDone }: Props) {
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<StreamEvent['status'] | null>(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [searchLog, setSearchLog] = useState<string[]>([]);
  const [streamText, setStreamText] = useState('');
  const [result, setResult] = useState<{ count: number; rate: number } | null>(null);
  const [showModal, setShowModal] = useState(false);

  const streamRef = useRef<HTMLPreElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // 스트리밍 텍스트가 쌓일 때마다 스크롤 아래로
  useEffect(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight;
  }, [streamText]);

  useEffect(() => {
    if (searchRef.current) searchRef.current.scrollTop = searchRef.current.scrollHeight;
  }, [searchLog]);

  async function startCollect(force: boolean) {
    setShowModal(false);
    setLoading(true);
    setPhase('starting');
    setStatusMsg('');
    setSearchLog([]);
    setStreamText('');
    setResult(null);

    try {
      const res = await fetch(`/api/collect${force ? '?force=true' : ''}`, { method: 'POST' });
      if (!res.body) throw new Error('응답 스트림 없음');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        const lines = buf.split('\n');
        buf = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let evt: StreamEvent;
          try { evt = JSON.parse(line.slice(6)); } catch { continue; }

          if (evt.status === 'exists') {
            setLoading(false);
            setPhase(null);
            setShowModal(true);
            return;
          }

          setPhase(evt.status);

          if (evt.status === 'streaming' && evt.chunk) {
            setStreamText(prev => prev + evt.chunk);
            continue;
          }

          if (evt.status === 'searching' && evt.message) {
            setSearchLog(prev => [...prev, evt.message!]);
          }

          if (evt.message && evt.status !== 'streaming') {
            setStatusMsg(evt.message);
          }

          if (evt.status === 'done') {
            setResult({ count: evt.count ?? 0, rate: evt.rate ?? 0 });
            setLoading(false);
            onDone();
          }

          if (evt.status === 'error') {
            setLoading(false);
          }
        }
      }
    } catch (err) {
      setPhase('error');
      setStatusMsg(String(err));
      setLoading(false);
    }
  }

  const isRunning = loading;
  const hasOutput = phase !== null || streamText.length > 0;

  return (
    <>
      <button className="btn" onClick={() => startCollect(false)} disabled={isRunning}>
        {isRunning
          ? <><span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: '#fff' }} /> 수집 중...</>
          : '▶ 오늘 데이터 수집'}
      </button>

      {hasOutput && (
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>

          {/* 상태 표시줄 */}
          <div style={{
            background: 'var(--bg3)',
            border: `1px solid ${phase === 'done' ? 'var(--green)' : phase === 'error' ? 'var(--red)' : 'var(--border)'}`,
            borderRadius: 'var(--radius)',
            padding: '9px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: 13,
          }}>
            {isRunning && <span className="spinner" />}
            <span className={phase === 'done' ? 'status-done' : phase === 'error' ? 'status-error' : 'status-info'}>
              {phase === 'done' && '✓ '}
              {phase === 'error' && '✗ '}
              {statusMsg || (phase === 'starting' ? 'API 연결 중...' : phase === 'streaming' ? 'AI 응답 수신 중...' : '')}
            </span>
            {phase === 'done' && result && (
              <span style={{ color: 'var(--text3)', fontSize: 12, marginLeft: 'auto' }}>
                {result.count}개 기업 · 환율 {result.rate.toLocaleString()} KRW
              </span>
            )}
          </div>

          {/* 검색 로그 */}
          {searchLog.length > 0 && (
            <div style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              overflow: 'hidden',
            }}>
              <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--border)', fontSize: 11, color: 'var(--text3)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                웹 검색 로그
              </div>
              <div ref={searchRef} style={{ maxHeight: 100, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 3 }}>
                {searchLog.map((q, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--text2)', display: 'flex', gap: 6 }}>
                    <span style={{ color: 'var(--accent)', flexShrink: 0 }}>›</span>
                    {q}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 스트리밍 텍스트 패널 */}
          {streamText && (
            <div style={{
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              overflow: 'hidden',
            }}>
              <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--border)', fontSize: 11, color: 'var(--text3)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>AI 응답 스트림</span>
                <span style={{ color: 'var(--text3)', fontWeight: 400 }}>
                  {streamText.length.toLocaleString()} chars
                  {isRunning && <span className="spinner" style={{ marginLeft: 8, width: 10, height: 10, borderWidth: 1.5 }} />}
                </span>
              </div>
              <pre ref={streamRef} style={{
                maxHeight: 200,
                overflowY: 'auto',
                padding: '10px 12px',
                margin: 0,
                fontSize: 11,
                lineHeight: 1.6,
                color: 'var(--text2)',
                fontFamily: "'SF Mono', Consolas, monospace",
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}>
                {streamText}
              </pre>
            </div>
          )}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>오늘 데이터가 이미 존재합니다</h3>
            <p>오늘({new Date().toISOString().split('T')[0]}) 데이터가 이미 저장되어 있습니다. 덮어쓰시겠습니까?</p>
            <div className="modal-actions">
              <button className="btn secondary" onClick={() => setShowModal(false)}>취소</button>
              <button className="btn danger" onClick={() => startCollect(true)}>덮어쓰기</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
