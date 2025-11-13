import { useEffect, useMemo, useState } from 'react'
import { api, executeQuery, saveQuery, shareQuery, listTablesApi, listColumnsByTableApi, createTemplateApi } from '../api/client'
import './Playground.css'

export default function Playground() {
  const [query, setQuery] = useState('统计近7天订单数量与GMV')
  const [useRag, setUseRag] = useState(true)
  const [reply, setReply] = useState<string>('')
  const [sql, setSql] = useState<string>('')
  const [ragContext, setRagContext] = useState<string>('')
  const [ragChunks, setRagChunks] = useState<Array<{ source?: string; text?: string }>>([])
  const [dataSources, setDataSources] = useState<Array<{ id: number; name: string; type?: string }>>([])
  const [selectedDsId, setSelectedDsId] = useState<number | null>(null)
  const [maxRows, setMaxRows] = useState<number>(1000)
  const [execLoading, setExecLoading] = useState(false)
  const [columns, setColumns] = useState<string[]>([])
  const [rows, setRows] = useState<any[]>([])
  const [execInfo, setExecInfo] = useState<{ ms?: number; count?: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [histories, setHistories] = useState<Array<{ id: number; generated_sql: string; status: string; row_count?: number; execution_time_ms?: number; created_at?: string; query_name?: string; is_shared?: boolean; is_saved?: boolean; tags?: string[] }>>([])
  const [historyPage, setHistoryPage] = useState<number>(1)
  const [historyPageSize, setHistoryPageSize] = useState<number>(5)
  const [historyTotalPages, setHistoryTotalPages] = useState<number>(0)
  const [historyTotal, setHistoryTotal] = useState<number>(0)
  const [lastQueryId, setLastQueryId] = useState<number | null>(null)
  const [queryName, setQueryName] = useState<string>('')
  const [tagsInput, setTagsInput] = useState<string>('')
  const [vizColumn, setVizColumn] = useState<string | null>(null)
  // 选择器相关状态
  type TableColumn = { id: number; name: string; display_name?: string; data_type?: string; is_dimension?: boolean; is_metric?: boolean }
  type DataTableItem = { id: number; table_name: string; display_name?: string; columns?: TableColumn[] }
  const [tables, setTables] = useState<DataTableItem[]>([])
  const [selectedTableId, setSelectedTableId] = useState<number | null>(null)
  const [dimensionCandidates, setDimensionCandidates] = useState<TableColumn[]>([])
  const [metricCandidates, setMetricCandidates] = useState<TableColumn[]>([])
  const [selectedDimensions, setSelectedDimensions] = useState<string[]>([])
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([])
  const [selectedFilters, setSelectedFilters] = useState<Array<{ column: string; op: string; value: any }>>([])
  const [selectedSorts, setSelectedSorts] = useState<Array<{ column: string; direction: 'ASC' | 'DESC' }>>([])
  // 模板应用相关
  const [tplAutoExecute, setTplAutoExecute] = useState<boolean>(false)
  // 查询模板与场景选择
  type Template = { id: number; name: string; description?: string; category?: string; natural_language_template?: string; sql_template?: string; parameters?: Record<string, any> | null }
  const [templates, setTemplates] = useState<Template[]>([])
  const categories = useMemo(() => {
    const set = new Set<string>()
    templates.forEach(t => { if (t.category) set.add(t.category) })
    return Array.from(set)
  }, [templates])
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [tplParams, setTplParams] = useState<Record<string, any>>({})
  // 保存场景弹窗
  const [saveModalOpen, setSaveModalOpen] = useState<boolean>(false)
  const [saving, setSaving] = useState<boolean>(false)
  const [saveForm, setSaveForm] = useState<{ name: string; category?: string; description?: string; natural_language_template?: string; is_public?: boolean }>({ name: '', category: '', description: '', natural_language_template: '', is_public: false })

  function buildTemplatePayloadFromSelector() {
    const params: Record<string, any> = {
      data_source_id: selectedDsId,
      table_id: selectedTableId,
      dimensions: selectedDimensions,
      metrics: selectedMetrics,
      filters: selectedFilters,
      sorts: selectedSorts,
    }
    return {
      name: saveForm.name,
      description: saveForm.description || '',
      category: saveForm.category || '',
      natural_language_template: saveForm.natural_language_template || '',
      sql_template: sql || '',
      parameters: params,
      is_public: !!saveForm.is_public,
    }
  }

  // 将模板的场景条件应用到左侧选择器
  function applyScenarioToSelectorFromTemplate(tpl?: Template | null) {
    if (!tpl) return
    const params = (tpl.parameters && typeof tpl.parameters === 'object') ? (tpl.parameters as Record<string, any>) : {}
    const pick = (k: string) => (params[k] ?? params[k.toLowerCase()] ?? params[k.toUpperCase()])
    const dims = pick('dimensions') ?? pick('dimension')
    const mets = pick('metrics') ?? pick('metric')
    const filters = pick('filters') ?? pick('filter')
    const sorts = pick('sorts') ?? pick('sort')
    const tableId = pick('table_id')
    const tableName = pick('table_name') ?? pick('table')

    // 选表：优先按id，其次按表名/显示名
    if (tableId) {
      try { setSelectedTableId(Number(tableId)) } catch {}
    } else if (tableName) {
      const t = tables.find(x => x.table_name === tableName || (x.display_name && x.display_name === tableName))
      if (t) setSelectedTableId(t.id)
    }

    // 维度/指标：支持数组或逗号分隔字符串
    if (Array.isArray(dims)) {
      setSelectedDimensions(dims.filter((n: any) => typeof n === 'string'))
    } else if (typeof dims === 'string') {
      setSelectedDimensions(String(dims).split(',').map(s => s.trim()).filter(Boolean))
    }
    if (Array.isArray(mets)) {
      setSelectedMetrics(mets.filter((n: any) => typeof n === 'string'))
    } else if (typeof mets === 'string') {
      setSelectedMetrics(String(mets).split(',').map(s => s.trim()).filter(Boolean))
    }

    // 筛选：支持 [{column, op, value}] 简单对象数组
    if (Array.isArray(filters)) {
      const norm = filters.map((f: any) => {
        const col = f?.column ?? f?.col ?? f?.[0] ?? ''
        const op = f?.op ?? f?.operator ?? f?.[1] ?? '='
        const val = (f?.value ?? f?.[2] ?? '')
        return { column: String(col), op: String(op), value: val }
      }).filter((x: any) => !!x.column)
      setSelectedFilters(norm)
    }

    // 排序：支持 [{column, direction}] 简单对象数组
    if (Array.isArray(sorts)) {
      const norm = sorts.map((s: any) => {
        const col = s?.column ?? s?.col ?? s?.[0] ?? ''
        const dir = (s?.direction ?? s?.dir ?? s?.[1] ?? 'ASC')
        const d = String(dir).toUpperCase() === 'DESC' ? 'DESC' : 'ASC'
        return { column: String(col), direction: d as ('ASC' | 'DESC') }
      }).filter((x: any) => !!x.column)
      setSelectedSorts(norm)
    }
  }

  function applyTemplate(sqlText: string, params?: Record<string, any> | null): string {
    if (!sqlText || !params) return sqlText
    let out = sqlText
    try {
      Object.entries(params).forEach(([k, v]) => {
        const re = new RegExp(`{{\\s*${k}\\s*}}`, 'g')
        // 支持类型化参数对象：{ type: 'date'|'select'|'number'|'text'|'daterange', value?: any, start?: any, end?: any }
        let raw: any = v
        if (v && typeof v === 'object') {
          if ('value' in (v as any)) raw = (v as any).value
          else if ('start' in (v as any) && 'end' in (v as any)) raw = `${(v as any).start}`
        }
        const val = typeof raw === 'number' ? String(raw) : `'${String(raw).replace(/'/g, "''")}'`
        out = out.replace(re, val)
      })
    } catch {}
    return out
  }

  async function handleAsk() {
    const { data } = await api.post('/v1/ai/query', { query, use_rag: useRag })
    setReply(data?.data?.reply || '')
    setSql(data?.data?.generated_sql || '')
    // 接收RAG引用上下文与片段
    setRagContext(String(data?.data?.rag_context || ''))
    setRagChunks(Array.isArray(data?.data?.rag_chunks) ? data?.data?.rag_chunks : [])
    // 解析AI返回的结构化选择器信息并填充到左侧选择器
    try {
      const selTableName: string | undefined = data?.data?.selected_table
      const dims: string[] = data?.data?.dimensions || []
      const mets: string[] = data?.data?.metrics || []
      const filts: Array<{ column: string; op: string; value: any }> = data?.data?.filters || []
      const sorts: Array<{ column: string; direction: 'ASC' | 'DESC' }> = data?.data?.sorts || []
      if (selTableName) {
        const table = tables.find(t => (t.table_name === selTableName || t.display_name === selTableName))
        if (table) setSelectedTableId(table.id)
      }
      setSelectedDimensions(dims)
      setSelectedMetrics(mets)
      setSelectedFilters(filts)
      setSelectedSorts(sorts)
    } catch {}
  }

  useEffect(() => {
    // 累加分页加载数据源，避免只展示部分选项
    (async () => {
      // 后端限制数据源列表 limit <= 100
      const pageSize = 100
      let offset = 0
      const all: Array<{ id: number; name: string; type?: string }> = []
      try {
        while (true) {
          const { data } = await api.get('/v1/data-sources/', { params: { limit: pageSize, offset } })
          const list = data?.data || []
          if (!Array.isArray(list) || list.length === 0) break
          all.push(...list.map((d: any) => ({ id: d.id, name: d.name, type: d.type })))
          if (list.length < pageSize) break
          offset += pageSize
          // 防御性上限，避免异常情况下无限循环
          if (offset > 5000) break
        }
      } catch {
        // 回退：若接口异常，保持已有数据
      }
      setDataSources(all)
      if (all.length > 0) setSelectedDsId(all[0].id)
    })()
    // 加载查询模板用于场景选择
    api.get('/v1/queries/templates', { params: { limit: 50 } })
      .then(({ data }) => {
        const items: Template[] = data?.data || []
        setTemplates(items)
        const firstCat = items.find(t => !!t.category)?.category || ''
        setSelectedCategory(firstCat || '')
      })
      .catch(() => setTemplates([]))
    // 加载历史（分页）
    loadHistories(1, historyPageSize)
    // 读取从模板应用的SQL
    try {
      const raw = localStorage.getItem('tpl_apply')
      if (raw) {
        localStorage.removeItem('tpl_apply')
        const payload = JSON.parse(raw)
        const sqlText = applyTemplate(String(payload?.sql || ''), payload?.parameters || null)
        if (sqlText) {
          setSql(sqlText)
          setTplAutoExecute(!!payload?.autoExecute)
          alert(`已应用模板：${payload?.name || ''}`)
        }
      }
    } catch {}
  }, [])

  // 当选择数据源变化时，加载该数据源下的表及字段
  useEffect(() => {
    async function loadTables() {
      if (!selectedDsId) { setTables([]); setSelectedTableId(null); setDimensionCandidates([]); setMetricCandidates([]); return }
      try {
        // 累加分页加载表，避免只展示部分选项
        const pageSize = 200
        let offset = 0
        const allTables: DataTableItem[] = []
        while (true) {
          const resp = await listTablesApi(selectedDsId, pageSize, offset)
          const batch: DataTableItem[] = (resp?.data || []).map((t: any) => ({
            id: t.id,
            table_name: t.table_name || t.name,
            display_name: t.display_name,
            columns: (t.columns || []).map((c: any) => ({
              id: c.id,
              name: c.name || c.column_name,
              display_name: c.display_name,
              data_type: c.data_type,
              is_dimension: !!c.is_dimension,
              is_metric: !!c.is_metric,
            })),
          }))
          if (!batch.length) break
          allTables.push(...batch)
          if (batch.length < pageSize) break
          offset += pageSize
          if (offset > 10000) break
        }
        setTables(allTables)
        const firstTable = allTables[0]
        setSelectedTableId(firstTable ? firstTable.id : null)
        const cols = firstTable?.columns || []
        setDimensionCandidates(cols.filter(c => c.is_dimension))
        setMetricCandidates(cols.filter(c => c.is_metric))
        setSelectedDimensions([])
        setSelectedMetrics([])
        setSelectedFilters([])
        setSelectedSorts([])
      } catch (e) {
        console.error('Failed to load tables:', e)
        setTables([])
      }
    }
    loadTables()
  }, [selectedDsId])

  // 当数据源准备好且来自模板的自动执行标记存在时触发执行
  useEffect(() => {
    if (tplAutoExecute && selectedDsId && sql) {
      setTplAutoExecute(false)
      handleExecute()
    }
  }, [tplAutoExecute, selectedDsId, sql])

  // 当选中表变化时，拉取并刷新候选维度/指标
  useEffect(() => {
    const table = tables.find(t => t.id === selectedTableId)
    const hasCols = !!(table?.columns && table.columns.length)
    if (!selectedTableId) {
      setDimensionCandidates([])
      setMetricCandidates([])
      return
    }
    if (hasCols) {
      const cols = table!.columns || []
      setDimensionCandidates(cols.filter(c => c.is_dimension))
      setMetricCandidates(cols.filter(c => c.is_metric))
      return
    }
    // 若当前表尚未包含字段，调用字段接口加载
    (async () => {
      try {
        const resp = await listColumnsByTableApi(selectedTableId)
        const cols: TableColumn[] = (resp?.data || []).map((c: any) => ({
          id: c.id,
          name: c.name || c.column_name,
          display_name: c.display_name,
          data_type: c.data_type,
          is_dimension: !!c.is_dimension,
          is_metric: !!c.is_metric,
        }))
        setTables(prev => prev.map(t => (t.id === selectedTableId ? { ...t, columns: cols } : t)))
        setDimensionCandidates(cols.filter(c => c.is_dimension))
        setMetricCandidates(cols.filter(c => c.is_metric))
      } catch (e) {
        console.error('Failed to load columns:', e)
        setDimensionCandidates([])
        setMetricCandidates([])
      }
    })()
  }, [selectedTableId, tables])

  async function handleExecute() {
    setError(null)
    setExecLoading(true)
    setColumns([])
    setRows([])
    setExecInfo(null)
    try {
      if (!selectedDsId) throw new Error('请选择数据源')
      if (!sql?.trim()) throw new Error('请先生成或输入SQL')
      const resp = await executeQuery(selectedDsId, sql, maxRows)
      const payload = resp?.data || {}
      const cols = (payload.columns || []).map((c: any) => c?.name || c)
      setColumns(cols)
      setRows(payload.data || [])
      setExecInfo({ ms: payload.execution_time_ms, count: payload.row_count })
      setLastQueryId(payload.query_id || null)
      // 设置默认可视化列（首个数值型列）
      const firstRow = (payload.data || [])[0]
      if (firstRow) {
        const nc = cols.find((c: string) => typeof firstRow?.[c] === 'number') || null
        setVizColumn(nc)
      } else {
        setVizColumn(null)
      }
      // 执行成功后刷新当前页历史
      loadHistories(historyPage, historyPageSize)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || '执行失败')
    } finally {
      setExecLoading(false)
    }
  }

  async function handleSave() {
    try {
      if (!lastQueryId) throw new Error('请先执行SQL以获得查询ID')
      const name = queryName?.trim()
      if (!name) throw new Error('请输入查询名称')
      const tags = tagsInput
        .split(/[，,\s]/)
        .map(t => t.trim())
        .filter(t => !!t)
      await saveQuery(lastQueryId, name, tags.length ? tags : undefined)
      alert('保存成功')
      // 刷新当前页历史
      loadHistories(historyPage, historyPageSize)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '保存失败')
    }
  }

  async function handleToggleShare(historyId: number, currentShared?: boolean) {
    try {
      const target = !currentShared
      await shareQuery(historyId, target)
      // 刷新当前页历史
      loadHistories(historyPage, historyPageSize)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '更新分享状态失败')
    }
  }

  function handleCopySql() {
    if (!sql) return
    navigator.clipboard.writeText(sql).then(() => {
      alert('SQL已复制到剪贴板')
    }).catch(() => alert('复制失败，请手动复制'))
  }

  function handleExportCSV() {
    if (!rows.length) {
      alert('暂无数据可导出')
      return
    }
    const header = columns.join(',')
    const body = rows.map(r => columns.map(c => {
      const v = r?.[c]
      if (v === null || v === undefined) return ''
      const s = String(v).replace(/"/g, '""')
      return /[",\n]/.test(s) ? `"${s}"` : s
    }).join(',')).join('\n')
    const csv = header + '\n' + body
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'query_result.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function loadHistories(page: number, pageSize: number) {
    try {
      const { data } = await api.get('/v1/queries/history', { params: { page, page_size: pageSize } })
      const list = data?.data || []
      const pg = data?.pagination || {}
      setHistories(list)
      setHistoryPage(pg?.page ?? page)
      setHistoryPageSize(pg?.page_size ?? pageSize)
      setHistoryTotal(pg?.total ?? list.length)
      const totalPages = (pg?.total_pages ?? Math.max(1, Math.ceil(((pg?.total ?? list.length) / (pg?.page_size ?? pageSize)))))
      setHistoryTotalPages(totalPages)
    } catch (e) {
      setHistories([])
      setHistoryTotal(0)
      setHistoryTotalPages(0)
    }
  }

  function handlePrevPage() {
    const p = Math.max(1, historyPage - 1)
    if (p !== historyPage) loadHistories(p, historyPageSize)
  }

  function handleNextPage() {
    const p = (historyTotalPages && historyTotalPages > 0) ? Math.min(historyTotalPages, historyPage + 1) : (historyPage + 1)
    if (p !== historyPage) loadHistories(p, historyPageSize)
  }

  function handlePageSizeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const size = parseInt(e.target.value || '5', 10)
    loadHistories(1, size)
  }

  const numericColumns = useMemo(() => {
    const r = rows?.[0]
    if (!r) return [] as string[]
    return columns.filter(c => typeof r?.[c] === 'number')
  }, [rows, columns])

  return (
    <div className="pg-container" style={{ display: 'flex', gap: 16 }}>
      <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* 场景设置（独立卡片） */}
        <div className="pg-card">
          <div className="section-title">场景设置</div>
          <div className="controls" style={{ gap: 8 }}>
            <span className="chip">场景</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {(categories.length ? categories : ['全部']).map(cat => (
                <button
                  key={cat}
                  className={`btn ghost${selectedCategory === cat ? ' active' : ''}`}
                  onClick={() => setSelectedCategory(cat === '全部' ? '' : cat)}
                >{cat}</button>
              ))}
            </div>
            <span className="chip">模板</span>
            <select
              className="pg-input"
              style={{ width: '100%' }}
              value={selectedTemplateId ?? ''}
              onChange={e => {
                const id = Number(e.target.value)
                setSelectedTemplateId(id)
                const tpl = templates.find(t => t.id === id)
                const params = (tpl?.parameters && typeof tpl.parameters === 'object') ? tpl.parameters as Record<string, any> : {}
                setTplParams(params || {})
              }}
            >
              <option value="">选择模板</option>
              {templates.filter(t => selectedCategory ? (t.category === selectedCategory) : true).map(t => (
                <option key={t.id} value={t.id}>
                  {t.name}{t.category ? `（${t.category}）` : ''}
                </option>
              ))}
            </select>
            {selectedTemplateId ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.keys(tplParams || {}).length ? (
                  Object.entries(tplParams).map(([k, v]) => {
                    const isObj = v && typeof v === 'object'
                    const type = isObj ? (v as any).type : undefined
                    const label = k
                    const value = isObj && 'value' in (v as any) ? (v as any).value : v
                    const options = isObj && Array.isArray((v as any).options) ? (v as any).options : undefined
                    const start = isObj && (v as any).start
                    const end = isObj && (v as any).end
                    return (
                      <div key={k} style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                        <span className="chip" style={{ minWidth: 80 }}>{label}</span>
                        {type === 'select' && options ? (
                          <select
                            className="pg-input"
                            value={String(value ?? '')}
                            onChange={e => setTplParams(p => ({ ...p, [k]: { ...(p[k] || {}), type: 'select', value: e.target.value, options } }))}
                          >
                            {options.map((opt: any, idx: number) => (
                              <option key={`${k}-opt-${idx}`} value={String(opt)}>{String(opt)}</option>
                            ))}
                          </select>
                        ) : type === 'number' || typeof value === 'number' ? (
                          <input
                            className="pg-input"
                            type="number"
                            value={Number(value ?? 0)}
                            onChange={e => setTplParams(p => ({ ...p, [k]: isObj ? { ...(p[k] || {}), type: 'number', value: Number(e.target.value) } : Number(e.target.value) }))}
                          />
                        ) : type === 'date' ? (
                          <input
                            className="pg-input"
                            type="date"
                            value={String(value ?? '')}
                            onChange={e => setTplParams(p => ({ ...p, [k]: { ...(p[k] || {}), type: 'date', value: e.target.value } }))}
                          />
                        ) : type === 'daterange' ? (
                          <div style={{ display: 'flex', gap: 6 }}>
                            <input
                              className="pg-input"
                              type="date"
                              value={String(start ?? '')}
                              onChange={e => setTplParams(p => ({ ...p, [k]: { ...(p[k] || {}), type: 'daterange', start: e.target.value, end } }))}
                            />
                            <input
                              className="pg-input"
                              type="date"
                              value={String(end ?? '')}
                              onChange={e => setTplParams(p => ({ ...p, [k]: { ...(p[k] || {}), type: 'daterange', start, end: e.target.value } }))}
                            />
                          </div>
                        ) : (
                          <input
                            className="pg-input"
                            value={String(value ?? '')}
                            onChange={e => setTplParams(p => ({ ...p, [k]: isObj ? { ...(p[k] || {}), type: (p[k] as any)?.type || 'text', value: e.target.value } : e.target.value }))}
                          />
                        )}
                      </div>
                    )
                  })
                ) : (
                  <div className="empty">该模板暂无参数</div>
                )}
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="btn primary"
                    onClick={() => {
                      const tpl = templates.find(t => t.id === selectedTemplateId)
                      if (!tpl?.sql_template) { alert('该模板暂无SQL'); return }
                      const sqlText = applyTemplate(tpl.sql_template, tplParams)
                      setSql(sqlText)
                    }}
                  >应用模板到SQL</button>
                  <button
                    className="btn"
                    onClick={() => {
                      const tpl = templates.find(t => t.id === selectedTemplateId)
                      applyScenarioToSelectorFromTemplate(tpl)
                    }}
                  >应用场景到选择器</button>
                  <label className="switch">
                    <input type="checkbox" checked={tplAutoExecute} onChange={e => setTplAutoExecute(e.target.checked)} /> 自动执行
                  </label>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {/* 选择器 */}
        <div className="pg-card">
          <div className="section-title">选择器</div>
          <div className="controls" style={{ gap: 8 }}>
            <span className="chip">数据源</span>
            <select className="pg-input" style={{ width: '100%' }} value={selectedDsId ?? ''} onChange={e => setSelectedDsId(Number(e.target.value))}>
              {dataSources.map(ds => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} {ds.type ? `(${ds.type})` : ''}
                </option>
              ))}
            </select>
            <span className="chip">数据表</span>
            <select className="pg-input" style={{ width: '100%' }} value={selectedTableId ?? ''} onChange={e => setSelectedTableId(Number(e.target.value))}>
              {tables.map(t => (
                <option key={t.id} value={t.id}>
                  {t.display_name || t.table_name}
                </option>
              ))}
            </select>
          </div>

        {/* 维度/指标/筛选/排序 */}
        <div className="controls" style={{ marginTop: 12, gap: 10, flexDirection: 'column', alignItems: 'stretch' }}>
          <span className="chip">维度</span>
          <div style={{ width: '100%', maxHeight: 200, overflowY: 'auto', border: '1px solid var(--pg-card-border)', borderRadius: 12, padding: 8 }}>
            {(dimensionCandidates.length ? dimensionCandidates : []).map(c => (
              <label key={`dim-${c.name}`} className="checkbox" style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '4px 0' }}>
                <input
                  type="checkbox"
                  checked={selectedDimensions.includes(c.name)}
                  onChange={() => {
                    setSelectedDimensions(prev => prev.includes(c.name) ? prev.filter(n => n !== c.name) : [...prev, c.name])
                  }}
                />{c.display_name || c.name}
              </label>
            ))}
          </div>
          {(!dimensionCandidates.length) ? <div className="empty">暂无维度（可直接选择列作为维度）</div> : null}

          <span className="chip" style={{ marginTop: 6 }}>指标</span>
          <div style={{ width: '100%', maxHeight: 200, overflowY: 'auto', border: '1px solid var(--pg-card-border)', borderRadius: 12, padding: 8 }}>
            {(metricCandidates.length ? metricCandidates : []).map(c => (
              <label key={`met-${c.name}`} className="checkbox" style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '4px 0' }}>
                <input
                  type="checkbox"
                  checked={selectedMetrics.includes(c.name)}
                  onChange={() => {
                    setSelectedMetrics(prev => prev.includes(c.name) ? prev.filter(n => n !== c.name) : [...prev, c.name])
                  }}
                />{c.display_name || c.name}
              </label>
            ))}
          </div>
          {(!metricCandidates.length) ? <div className="empty">暂无指标（可直接选择列作为指标）</div> : null}

          <span className="chip" style={{ marginTop: 6 }}>筛选</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(selectedFilters.length ? selectedFilters : []).map((f, i) => (
              <div key={`f-${i}`} style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                <select className="pg-input" style={{ flex: '1 1 140px' }} value={f.column} onChange={e => {
                  const v = e.target.value
                  setSelectedFilters(prev => prev.map((x, idx) => idx === i ? { ...x, column: v } : x))
                }}>
                  {(tables.find(t => t.id === selectedTableId)?.columns || []).map(c => (
                    <option key={`fc-${c.name}`} value={c.name}>{c.display_name || c.name}</option>
                  ))}
                </select>
                <select className="pg-input" style={{ width: 90 }} value={f.op} onChange={e => {
                  const v = e.target.value
                  setSelectedFilters(prev => prev.map((x, idx) => idx === i ? { ...x, op: v } : x))
                }}>
                  {['=', '!=', '<', '<=', '>', '>=', 'LIKE'].map(op => (<option key={`op-${op}`} value={op}>{op}</option>))}
                </select>
                <input className="pg-input" style={{ flex: '1 1 120px' }} value={String(f.value ?? '')} onChange={e => {
                  const v = e.target.value
                  setSelectedFilters(prev => prev.map((x, idx) => idx === i ? { ...x, value: v } : x))
                }} />
                <button className="btn ghost" onClick={() => setSelectedFilters(prev => prev.filter((_, idx) => idx !== i))}>删除</button>
              </div>
            ))}
            <button className="btn" onClick={() => {
              const cols = tables.find(t => t.id === selectedTableId)?.columns || []
              const first = cols[0]?.name || ''
              setSelectedFilters(prev => [...prev, { column: first, op: '=', value: '' }])
            }}>新增筛选条件</button>
          </div>

          <span className="chip" style={{ marginTop: 6 }}>排序</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(selectedSorts.length ? selectedSorts : []).map((s, i) => (
              <div key={`s-${i}`} style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                <select className="pg-input" style={{ flex: '1 1 140px' }} value={s.column} onChange={e => {
                  const v = e.target.value
                  setSelectedSorts(prev => prev.map((x, idx) => idx === i ? { ...x, column: v } : x))
                }}>
                  {(tables.find(t => t.id === selectedTableId)?.columns || []).map(c => (
                    <option key={`sc-${c.name}`} value={c.name}>{c.display_name || c.name}</option>
                  ))}
                </select>
                <select className="pg-input" style={{ width: 100 }} value={s.direction} onChange={e => {
                  const v = e.target.value as ('ASC' | 'DESC')
                  setSelectedSorts(prev => prev.map((x, idx) => idx === i ? { ...x, direction: v } : x))
                }}>
                  {['ASC', 'DESC'].map(d => (<option key={`dir-${d}`} value={d}>{d}</option>))}
                </select>
                <button className="btn ghost" onClick={() => setSelectedSorts(prev => prev.filter((_, idx) => idx !== i))}>删除</button>
              </div>
            ))}
            <button className="btn" onClick={() => {
              const cols = tables.find(t => t.id === selectedTableId)?.columns || []
              const first = cols[0]?.name || ''
              setSelectedSorts(prev => [...prev, { column: first, direction: 'ASC' }])
            }}>新增排序条件</button>
          </div>
        </div>
        <div className="controls" style={{ marginTop: 12, gap: 8 }}>
          <button className="btn ghost" onClick={() => { setSelectedDimensions([]); setSelectedMetrics([]); setSelectedFilters([]); setSelectedSorts([]) }}>重置选择</button>
          <button className="btn primary" onClick={() => {
            const table = tables.find(t => t.id === selectedTableId)
            if (!table) { alert('请先选择表'); return }
            const selCols = [...selectedDimensions, ...selectedMetrics]
            // 列名不加双引号，避免被当作字符串字面量（兼容 MySQL 等）
            const colsSql = selCols.length ? selCols.join(', ') : '*'
            const whereSql = selectedFilters.length ? ' WHERE ' + selectedFilters.map(f => {
              const val = typeof f.value === 'number' ? f.value : `'${String(f.value).replace(/'/g, "''")}'`
              const op = String(f.op).replace(/&lt;/g, '<').replace(/&gt;/g, '>')
              // 过滤条件中字段同样不加双引号
              return `${f.column} ${op} ${val}`
            }).join(' AND ') : ''
            // 排序字段不加双引号
            const orderSql = selectedSorts.length ? ' ORDER BY ' + selectedSorts.map(s => `${s.column} ${s.direction}`).join(', ') : ''
            const text = `SELECT ${colsSql} FROM ${table.table_name}${whereSql}${orderSql}`
            setSql(text)
          }}>生成SQL</button>
          <button className="btn" onClick={handleExecute}>查询</button>
          <button className="btn" onClick={() => setSaveModalOpen(true)}>保存场景</button>
        </div>
        </div>
        {/* 保存场景弹窗 */}
        {saveModalOpen ? (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
            <div className="pg-card" style={{ width: 520 }}>
              <div className="section-title">保存为查询模板</div>
              <div className="controls" style={{ gap: 8 }}>
                <input className="pg-input" placeholder="模板名称" value={saveForm.name} onChange={e => setSaveForm(v => ({ ...v, name: e.target.value }))} />
                <input className="pg-input" placeholder="分类(可选)" value={saveForm.category} onChange={e => setSaveForm(v => ({ ...v, category: e.target.value }))} />
                <input className="pg-input" placeholder="描述(可选)" value={saveForm.description} onChange={e => setSaveForm(v => ({ ...v, description: e.target.value }))} />
                <textarea className="pg-input" placeholder="自然语言模板(必填)" value={saveForm.natural_language_template} onChange={e => setSaveForm(v => ({ ...v, natural_language_template: e.target.value }))} />
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <input type="checkbox" checked={!!saveForm.is_public} onChange={e => setSaveForm(v => ({ ...v, is_public: e.target.checked }))} /> 公开
                </label>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button className="btn ghost" onClick={() => setSaveModalOpen(false)}>取消</button>
                  <button className="btn primary" disabled={saving || !saveForm.name.trim() || !saveForm.natural_language_template?.trim() || !sql?.trim()} onClick={async () => {
                    try {
                      setSaving(true)
                      // 前端必填校验，避免后端422导致不友好错误对象
                      if (!saveForm.name?.trim()) { alert('请填写模板名称'); return }
                      if (!saveForm.natural_language_template?.trim()) { alert('请填写自然语言模板'); return }
                      if (!sql?.trim()) { alert('请先生成或输入SQL'); return }
                      const payload = buildTemplatePayloadFromSelector()
                      await createTemplateApi(payload)
                      alert('模板已保存')
                      setSaveModalOpen(false)
                      // 重新加载模板列表，便于立即使用
                      const { data } = await api.get('/v1/queries/templates', { params: { limit: 50 } })
                      setTemplates(data?.data || [])
                    } catch (e: any) {
                      const d = e?.response?.data?.detail
                      const msg = typeof d === 'string'
                        ? d
                        : Array.isArray(d)
                          ? d.map((x: any) => x?.msg || JSON.stringify(x)).join('; ')
                          : (d?.msg || (d ? JSON.stringify(d) : ''))
                      alert(msg || '保存失败')
                    } finally {
                      setSaving(false)
                    }
                  }}>保存</button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
      <div style={{ flex: 1 }}>
        <div className="pg-card">
          <div className="section-title">智能问答</div>
          <div className="controls">
            <input className="pg-input" style={{ flex: 1, minWidth: 280 }} value={query} onChange={e => setQuery(e.target.value)} />
            <label className="switch">
              <input type="checkbox" checked={useRag} onChange={e => setUseRag(e.target.checked)} /> 使用RAG
            </label>
            <button className="btn primary" onClick={handleAsk}>生成SQL</button>
        </div>
      </div>

        {/* RAG引用来源与片段 */}
        <div className="pg-card" style={{ marginTop: 12 }}>
          <div className="section-title">引用来源与片段</div>
          <div className="controls" style={{ flexDirection: 'column', gap: 8, alignItems: 'stretch' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="chip">检索上下文</span>
              <button className="btn" onClick={() => navigator.clipboard.writeText(ragContext || '')} disabled={!ragContext}>复制上下文</button>
            </div>
            {ragContext ? (
              <textarea className="pg-input" rows={6} style={{ resize: 'vertical', width: '100%' }} readOnly value={ragContext} />
            ) : (
              <div className="empty">暂无检索上下文</div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
              <span className="chip">检索片段</span>
              <span className="chip">{ragChunks?.length || 0} 条</span>
            </div>
            {(ragChunks && ragChunks.length) ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {ragChunks.map((c, i) => (
                  <div key={`rag-${i}`} className="pg-card" style={{ padding: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span className="chip">来源</span>
                        <span>{String(c?.source || '未知')}</span>
                      </div>
                      <button className="btn ghost" onClick={() => navigator.clipboard.writeText(String(c?.text || ''))} disabled={!c?.text}>复制片段</button>
                    </div>
                    <div style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
                      {String(c?.text || '').slice(0, 600)}{String(c?.text || '').length > 600 ? '…' : ''}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty">暂无检索片段</div>
            )}
          </div>
        </div>

        {/* SQL编辑与执行 */}
        <div className="pg-card" style={{ marginTop: 12 }}>
          <div className="section-title">SQL编辑</div>
          <div className="controls" style={{ flexDirection: 'column', gap: 8, alignItems: 'stretch' }}>
            <textarea
              className="pg-input"
              rows={14}
              style={{ minHeight: 240, resize: 'vertical', width: '100%' }}
              placeholder="在此查看或编辑生成的SQL"
              value={sql}
              onChange={e => setSql(e.target.value)}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button className="btn" onClick={handleCopySql} disabled={!sql?.trim()}>复制SQL</button>
              <button className="btn primary" onClick={handleExecute} disabled={execLoading || !sql?.trim()}>查询</button>
              <span className="chip">返回行数上限</span>
              <input className="pg-input" type="number" style={{ width: 120 }} value={maxRows} onChange={e => {
                const v = Number(e.target.value)
                setMaxRows(Number.isFinite(v) && v > 0 ? v : 1000)
              }} />
            </div>
            {error ? (<div className="empty" style={{ color: '#f87171' }}>{error}</div>) : null}
          </div>
        </div>

        {/* 执行结果 */}
        <div className="pg-card" style={{ marginTop: 12 }}>
          <div className="section-title">执行结果</div>
          <div className="controls" style={{ gap: 8 }}>
            {execInfo?.ms !== undefined ? (<span className="chip">耗时 {execInfo.ms} ms</span>) : null}
            {execInfo?.count !== undefined ? (<span className="chip">行数 {execInfo.count}</span>) : null}
            <button className="btn" onClick={handleExportCSV} disabled={!rows.length}>导出CSV</button>
          </div>
          <div className="table-wrap">
            <table className="pg-table">
              <thead>
                <tr>
                  {columns.map(c => (<th key={`h-${c}`}>{c}</th>))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`r-${i}`}>
                    {columns.map(c => (<td key={`c-${i}-${c}`}>{String(r?.[c] ?? '')}</td>))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 历史记录（点击可填充SQL） */}
        <div className="pg-card" style={{ marginTop: 12 }}>
          <div className="section-title">历史</div>
          <ul className="history-list">
            {(histories || []).map(h => (
              <li key={h.id} className="history-item" onClick={() => setSql(h.generated_sql || '')}>
                <div className="title">{h.query_name || `查询 ${h.id}`}</div>
                <div className="meta">行数 {h.row_count ?? '-'} | 耗时 {h.execution_time_ms ?? '-'} ms | {h.created_at || ''}</div>
                <div className="meta">{(h.tags || []).join(', ')}</div>
                <div className="controls" style={{ gap: 8 }}>
                  <button className="btn" onClick={(e) => { e.stopPropagation(); handleToggleShare(h.id, h.is_shared) }}>{h.is_shared ? '取消分享' : '分享'}</button>
                </div>
              </li>
            ))}
            {(!histories || !histories.length) ? (<li className="history-item">暂无历史</li>) : null}
          </ul>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
            <div>第 {historyPage} / {Math.max(1, historyTotalPages)} 页（共 {historyTotal} 条）</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button className="btn" onClick={handlePrevPage} disabled={historyPage <= 1}>上一页</button>
              <button className="btn" onClick={handleNextPage} disabled={historyTotalPages ? historyPage >= historyTotalPages : (histories.length < historyPageSize)}>下一页</button>
              <select value={historyPageSize} onChange={handlePageSizeChange}>
                <option value={5}>每页 5 条</option>
                <option value={10}>每页 10 条</option>
                <option value={20}>每页 20 条</option>
                <option value={50}>每页 50 条</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}