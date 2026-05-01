import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import Anthropic from '@anthropic-ai/sdk';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');
const INDEX_FILE = path.join(DATA_DIR, 'index.json');

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(INDEX_FILE)) {
  fs.writeFileSync(INDEX_FILE, JSON.stringify({ dates: [], lastCollected: null, lastRate: null }));
}

interface IndexData {
  dates: string[];
  lastCollected: string | null;
  lastRate: number | null;
}

function readIndex(): IndexData {
  return JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8'));
}

function writeIndex(data: IndexData) {
  fs.writeFileSync(INDEX_FILE, JSON.stringify(data, null, 2));
}

// Built-in web_search tool — not yet in the SDK's type definitions
const WEB_SEARCH_TOOL = [
  { type: 'web_search_20250305', name: 'web_search' },
] as unknown as Anthropic.Tool[];

const app = express();
app.use(cors());
app.use(express.json());

app.get('/api/dates', (_req, res) => {
  res.json(readIndex().dates);
});

app.get('/api/data/:date', (req, res) => {
  const filePath = path.join(DATA_DIR, `marketcap-${req.params.date}.json`);
  if (!fs.existsSync(filePath)) return res.status(404).json({ error: '데이터가 없습니다' });
  res.json(JSON.parse(fs.readFileSync(filePath, 'utf-8')));
});

app.get('/api/meta', (_req, res) => {
  const idx = readIndex();
  res.json({ lastCollected: idx.lastCollected, lastRate: idx.lastRate, count: idx.dates.length });
});

app.post('/api/collect', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const send = (data: object) => res.write(`data: ${JSON.stringify(data)}\n\n`);

  const today = new Date().toISOString().split('T')[0];
  const force = req.query.force === 'true';

  if (!force && fs.existsSync(path.join(DATA_DIR, `marketcap-${today}.json`))) {
    send({ status: 'exists', date: today });
    return res.end();
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    send({ status: 'error', message: 'ANTHROPIC_API_KEY가 설정되지 않았습니다.' });
    return res.end();
  }

  try {
    send({ status: 'starting', message: 'Anthropic API 연결 중...' });

    const client = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
      defaultHeaders: { 'anthropic-beta': 'web-search-2025-03-05' },
    });

    const systemPrompt =
      'You are a financial data API. You must return ONLY a valid JSON object. ' +
      'Never write explanations, markdown, bullet points, or any text outside the JSON. ' +
      'If you cannot find exact data, use your best estimate. Always return the complete JSON.';

    const userPrompt =
      `Return ONLY this JSON structure with no other text:\n` +
      `{"rate": 1380, "data": [{"rank": 1, "name": "Apple", "ticker": "AAPL", ` +
      `"exchange": "NASDAQ", "country": "US", "sector": "Technology", ` +
      `"market_cap_usd": 3200000000000, "market_cap_krw": 4416000000000000, ` +
      `"price_usd": 213.5, "change_1d_pct": 1.2}]}\n\n` +
      `Today is ${today}. Fill in real data for top 200 companies by market cap worldwide. ` +
      `Use web search to get current data. Return 200 companies. No text outside JSON.`;

    const messages: Anthropic.MessageParam[] = [{ role: 'user', content: userPrompt }];
    let finalText = '';

    for (let turn = 0; turn < 15; turn++) {
      // ── 스트리밍 API 호출 ──────────────────────────────────────────────
      const stream = client.messages.stream({
        model: 'claude-sonnet-4-5',
        max_tokens: 32000,
        system: systemPrompt,
        tools: WEB_SEARCH_TOOL,
        messages,
      });

      // 텍스트 청크를 실시간으로 프론트에 전달
      stream.on('text', (chunk: string) => {
        send({ status: 'streaming', chunk });
      });

      // tool_use 블록 시작 시 즉시 알림
      stream.on('streamEvent', (event) => {
        if (
          event.type === 'content_block_start' &&
          'content_block' in event &&
          event.content_block.type === 'tool_use'
        ) {
          send({ status: 'searching', message: '웹 검색 중...' });
        }
      });

      const message = await stream.finalMessage();

      if (message.stop_reason === 'end_turn') {
        // 최종 텍스트 수집
        for (const block of message.content) {
          if (block.type === 'text') { finalText = block.text; break; }
        }
        break;
      }

      if (message.stop_reason === 'tool_use') {
        messages.push({ role: 'assistant', content: message.content });

        const toolResults: Anthropic.ToolResultBlockParam[] = [];
        for (const block of message.content) {
          if (block.type === 'tool_use') {
            const q = (block.input as { query?: string })?.query;
            if (q) send({ status: 'searching', message: `검색: ${q}` });
            toolResults.push({
              type: 'tool_result',
              tool_use_id: block.id,
              content: 'Search results retrieved.',
            });
          }
        }
        messages.push({ role: 'user', content: toolResults });
        continue;
      }

      throw new Error(`예상치 못한 stop_reason: ${message.stop_reason}`);
    }

    if (!finalText) throw new Error('AI 응답에서 텍스트를 찾을 수 없습니다');

    send({ status: 'processing', message: 'JSON 파싱 중...' });

    const first = finalText.indexOf('{');
    const last = finalText.lastIndexOf('}');
    if (first === -1 || last === -1 || last <= first) throw new Error('응답에서 JSON을 찾을 수 없습니다');

    const parsed: { rate: number; data: unknown[] } = JSON.parse(finalText.slice(first, last + 1));
    const { rate, data } = parsed;

    if (!Array.isArray(data) || data.length === 0) throw new Error('데이터 배열이 비어있습니다');

    fs.writeFileSync(
      path.join(DATA_DIR, `marketcap-${today}.json`),
      JSON.stringify({ date: today, rate, data }, null, 2),
    );

    const index = readIndex();
    if (!index.dates.includes(today)) index.dates.push(today);
    index.dates.sort((a, b) => b.localeCompare(a));
    index.lastCollected = new Date().toISOString();
    index.lastRate = rate;
    writeIndex(index);

    send({ status: 'done', message: `수집 완료! ${data.length}개 기업 저장`, date: today, count: data.length, rate });
  } catch (err) {
    send({ status: 'error', message: err instanceof Error ? err.message : String(err) });
  } finally {
    res.end();
  }
});

const PORT = process.env.PORT ? Number(process.env.PORT) : 3001;
app.listen(PORT, () => {
  console.log(`\n서버 실행 중 → http://localhost:${PORT}`);
  console.log(`API KEY: ${process.env.ANTHROPIC_API_KEY ? '설정됨' : '미설정'}\n`);
});
