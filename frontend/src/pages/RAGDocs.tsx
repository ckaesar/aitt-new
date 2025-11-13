import { useState } from 'react'
import { searchRagDocs, upsertRagDocs } from '../api/client'

export default function RAGDocs() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(4)
  const [results, setResults] = useState<Array<{ text: string; source?: string }>>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState('')

  const [newText, setNewText] = useState('')
  const [newSource, setNewSource] = useState('')
  const [upserting, setUpserting] = useState(false)
  const [upsertMsg, setUpsertMsg] = useState('')

  async function handleSearch() {
    setLoading(true)
    setErrMsg('')
    try {
      const resp = await searchRagDocs(query, topK)
      const chunks = resp?.data || []
      setResults(chunks)
    } catch (e: any) {
      setErrMsg(e?.message || '查询失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpsert() {
    if (!newText.trim()) {
      setUpsertMsg('请输入文档内容')
      return
    }
    setUpserting(true)
    setUpsertMsg('')
    try {
      const resp = await upsertRagDocs([{ text: newText, source: newSource || undefined }])
      const cnt = resp?.data?.inserted_count ?? 0
      setUpsertMsg(`已写入 ${cnt} 条文档片段`)
      setNewText('')
      setNewSource('')
    } catch (e: any) {
      setUpsertMsg(e?.message || '写入失败')
    } finally {
      setUpserting(false)
    }
  }

  function copy(text: string) {
    navigator.clipboard?.writeText(text)
  }

  return (
    <div className="pg-grid">
      <div className="pg-card" style={{ gridColumn: '1 / span 2' }}>
        <div className="pg-card-title">RAG 文档查询</div>
        <div className="pg-row" style={{ gap: 8, alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>检索关键词（例如：退货政策、产品规格）</div>
            <input className="input" placeholder="输入查询关键词" value={query} onChange={e => setQuery(e.target.value)} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: 160 }}>
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>返回片段数（1–20，默认4）</div>
            <input className="input" type="number" min={1} max={20} value={topK} onChange={e => setTopK(Number(e.target.value))} />
          </div>
          <button className="btn primary" onClick={handleSearch} disabled={loading} style={{ alignSelf: 'end' }}>查询</button>
        </div>
        {errMsg && <div style={{ color: 'var(--color-error)', marginTop: 8 }}>{errMsg}</div>}
        <div style={{ marginTop: 12 }}>
          {loading ? <div>加载中...</div> : (
            results.length === 0 ? <div>暂无结果</div> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {results.map((c, idx) => (
                  <div key={idx} className="pg-sub-card" style={{ padding: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>来源：{c.source || 'unknown'}</div>
                      <span style={{ flex: 1 }} />
                      <button className="btn ghost" onClick={() => copy(c.text)}>复制</button>
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', marginTop: 6 }}>
                      {(c.text || '').length > 1000 ? (c.text || '').slice(0, 1000) + '…' : c.text}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>

      <div className="pg-card" style={{ gridColumn: '3 / span 1' }}>
        <div className="pg-card-title">新增文档片段</div>
        <div className="pg-row" style={{ flexDirection: 'column', gap: 8 }}>
          <input className="input" placeholder="来源（可选）" value={newSource} onChange={e => setNewSource(e.target.value)} />
          <textarea className="input" placeholder="输入文档内容" value={newText} onChange={e => setNewText(e.target.value)} rows={10} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" onClick={handleUpsert} disabled={upserting}>写入</button>
            {upsertMsg && <div style={{ alignSelf: 'center', color: 'var(--color-text-secondary)' }}>{upsertMsg}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}