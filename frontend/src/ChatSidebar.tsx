import { useEffect, useRef, useState } from 'react';
import { Button, Drawer, Input, Tag } from 'antd';
import './ChatSidebar.css';
import type { TrendAttachment } from './trendReference';

type Citation = { doc_id: string; quote: string; chunk_id?: unknown; metadata?: { title?: unknown; effective_from?: unknown; stores?: unknown }; scope?: { as_of?: unknown } };
const field = (v: unknown) => typeof v === 'string' ? v : '';
type Response = { answer: string; answer_type: 'data' | 'doc' | 'hybrid' | 'refusal' | 'clarify'; citations: Citation[]; data_evidence: { tool?: string; params?: unknown; sql?: string; result: unknown }[]; trace_id: string };
type Turn = { id: string; question: string; attachment: TrendAttachment | null; response?: Response; error?: string };
const labels = { data: '数据回答', doc: '文档回答', hybrid: '综合回答', refusal: '暂时无法回答', clarify: '需要补充信息' };
function parse(value: unknown): Response {
  const r = value as Response;
  if (!r || typeof r.answer !== 'string' || !r.answer.trim() || !(r.answer_type in labels) || typeof r.trace_id !== 'string' ||
      !Array.isArray(r.citations) || !Array.isArray(r.data_evidence) ||
      r.citations.some(c => !c || typeof c.doc_id !== 'string' || typeof c.quote !== 'string') ||
      r.data_evidence.some(e => !e || !('result' in e))) throw new Error('回答格式不完整，请重试');
  return r;
}

function ReferenceCard({ attachment, onRemove }: { attachment: TrendAttachment; onRemove?: () => void }) {
  const { context, storeLabel } = attachment;
  return <div className="trend-reference" data-testid="trend-reference">
    <strong>引用 · 每日净营业额趋势</strong>
    <span>{context.start} 至 {context.end} · {storeLabel} · 净营业额</span>
    {onRemove && <Button size="small" aria-label="移除趋势引用" onClick={onRemove}>移除</Button>}
  </div>;
}

/** Chat owns its session and requests. A trend range enters only by explicit attachment. */
export function ChatSidebar({ incoming }: { incoming: TrendAttachment | null }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState<TrendAttachment | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [waiting, setWaiting] = useState(false);
  const session = useRef(crypto.randomUUID());
  const request = useRef<AbortController | null>(null);
  const history = useRef<HTMLDivElement>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if (incoming) { setPending(incoming); setOpen(true); } }, [incoming]);
  useEffect(() => { history.current?.scrollTo({ top: history.current.scrollHeight }); }, [turns, waiting, open]);
  function newSession() {
    request.current?.abort();
    request.current = null;
    session.current = crypto.randomUUID();
    setTurns([]); setDraft(''); setPending(null); setWaiting(false);
  }
  async function send(question: string, attachment: TrendAttachment | null = pending, retryId?: string) {
    if (request.current || !question.trim()) return;
    const id = retryId || crypto.randomUUID();
    const sentSession = session.current;
    const controller = new AbortController();
    request.current = controller;
    setWaiting(true); if (!retryId) { setDraft(''); setPending(null); }
    setTurns(old => retryId ? old.map(t => t.id === id ? { id, question, attachment } : t) : [...old, { id, question, attachment }]);
    const timeout = window.setTimeout(() => controller.abort(), 185000);
    const current = () => session.current === sentSession && request.current === controller;
    try {
      const result = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sentSession, question, ...(attachment ? { context: attachment.context } : {}) }), signal: controller.signal });
      if (!result.ok) throw new Error(`服务返回 ${result.status}，请稍后重试`);
      const response = parse(await result.json());
      if (current()) setTurns(old => old.map(t => t.id === id ? { ...t, response } : t));
    } catch (error) {
      if (current()) setTurns(old => old.map(t => t.id === id ? { ...t, error: controller.signal.aborted ? '等待回答超时，请重试' : error instanceof Error ? error.message : '连接失败，请重试' } : t));
    } finally {
      window.clearTimeout(timeout);
      if (current()) { request.current = null; setWaiting(false); }
    }
  }
  return <>
    <Button className="chat-launcher" type="primary" onClick={() => setOpen(true)}>经营助手</Button>
    <Drawer title="经营助手" open={open} onClose={() => setOpen(false)} width="min(480px, 100vw)" className="chat-drawer"
      extra={<Button onClick={newSession}>新建对话</Button>}>
      <div className="chat-layout">
        <div className="chat-history" ref={history} role="log" aria-label="聊天记录" aria-live="polite">
          {turns.length === 0 && <div className="chat-welcome"><h2>从一个经营问题开始</h2><p>写明日期、门店和想了解的指标或制度，回答后可展开数据证据与原文核对。</p><Button onClick={() => setDraft('S02 六月的净营业额是多少？')}>S02 六月的净营业额是多少？</Button><p className="chat-hint">请在问题中说明查询范围；看板筛选不会自动带入。新建对话可重新开始。</p></div>}
          {turns.map(turn => <article className="chat-turn" key={turn.id}>
            <div className="chat-question"><span>你</span><p>{turn.question}</p>{turn.attachment && <ReferenceCard attachment={turn.attachment} />}</div>
            {(turn.response || turn.error) && <div className="chat-answer">
              {turn.response && <><Tag color={turn.response.answer_type === 'refusal' ? 'orange' : 'green'}>{labels[turn.response.answer_type]}</Tag><p>{turn.response.answer}</p>
                {turn.response.data_evidence.length > 0 && <details><summary>展开数据证据（{turn.response.data_evidence.length}）</summary>{turn.response.data_evidence.map((e, i) => <section className="chat-evidence" key={i}><strong>{e.tool || '只读查询'}</strong><h4>查询条件</h4><pre>{JSON.stringify(e.params ?? e.sql, null, 2)}</pre><h4>实际结果</h4><pre>{JSON.stringify(e.result, null, 2)}</pre></section>)}</details>}
                {turn.response.citations.length > 0 && <details><summary>展开文档引用（{turn.response.citations.length}）</summary>{turn.response.citations.map((c, i) => <blockquote key={i}><strong>{c.doc_id}{field(c.metadata?.title) && ` · ${field(c.metadata?.title)}`}</strong>
                  {(field(c.metadata?.effective_from) || field(c.scope?.as_of)) && <div className="citation-meta">{field(c.metadata?.effective_from) && `生效日期：${field(c.metadata?.effective_from)}`}{field(c.scope?.as_of) && ` · 核对时点：${field(c.scope?.as_of)}`}</div>}
                  <p>{c.quote}</p>{field(c.chunk_id) && <small>来源片段：{field(c.chunk_id)}</small>}</blockquote>)}</details>}
                <small>追踪编号：{turn.response.trace_id}</small></>}
              {turn.error && <p role="alert">{turn.error}</p>}
              {(turn.error || turn.response?.answer_type === 'refusal') && <Button disabled={waiting} onClick={() => void send(turn.question, turn.attachment, turn.id)}>重试这条问题</Button>}
            </div>}
          </article>)}
          {waiting && <p className="chat-waiting" role="status">正在查询并核对依据，请稍候…</p>}
        </div>
        <form className="chat-composer" onSubmit={event => { event.preventDefault(); void send(draft.trim()); }}>
          {pending && <ReferenceCard attachment={pending} onRemove={() => setPending(null)} />}
          <Input.TextArea aria-label="经营问题" placeholder="例如：S02 六月牛肉poke卖了多少份？" value={draft} maxLength={2000} autoSize={{ minRows: 3, maxRows: 6 }}
            onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); void send(draft.trim()); } }} />
          <div><small>Ctrl / ⌘ + Enter 发送</small><Button aria-label="发送" type="primary" htmlType="submit" loading={waiting} disabled={waiting || !draft.trim()}>发送</Button></div>
        </form>
      </div>
    </Drawer>
  </>;
}
