import { useEffect, useMemo, useState } from 'react'
import { api, createDataSource, updateDataSourceApi, deleteDataSourceApi, testConnectionApi, syncTablesApi, syncMetadataApi, getMetadataLastSyncApi } from '../api/client'
import './Playground.css'

type DataSource = {
  id: number
  name: string
  type: string
  host: string
  port: number
  database_name: string
  is_active: boolean
}

export default function DataSources() {
  const hasToken = !!localStorage.getItem('token')
  const [items, setItems] = useState<DataSource[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<keyof DataSource>('id')
  const [sortAsc, setSortAsc] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newDs, setNewDs] = useState({
    name: '', type: 'MySQL', host: '', port: 3306,
    database_name: '', username: '', password: '', description: ''
  })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editPatch, setEditPatch] = useState<{ name?: string; host?: string; port?: number; database_name?: string; username?: string; password?: string; description?: string; is_active?: boolean }>({})
  const typeOptions = ['MySQL', 'PostgreSQL']
  const [testingId, setTestingId] = useState<number | null>(null)
  const [syncingId, setSyncingId] = useState<number | null>(null)
  const [syncingMeta, setSyncingMeta] = useState<boolean>(false)
  const [lastSync, setLastSync] = useState<any | null>(null)
  useEffect(() => { reload() }, [])
  useEffect(() => { fetchLastSync() }, [])

  const sorted = useMemo(() => {
    const arr = [...items]
    arr.sort((a, b) => {
      const va = a[sortBy]
      const vb = b[sortBy]
      if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va
      return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va))
    })
    return arr
  }, [items, sortBy, sortAsc])

  function toggleSort(field: keyof DataSource) {
    if (sortBy === field) setSortAsc(!sortAsc)
    else { setSortBy(field); setSortAsc(true) }
  }
  async function handleCreate() {
    if (!newDs.name || !newDs.host || !newDs.port || !newDs.database_name) {
      alert('请填写名称、地址、端口和数据库名');
      return
    }
    try {
      setCreating(true)
      await createDataSource({
        name: newDs.name,
        type: newDs.type as any,
        host: newDs.host,
        port: Number(newDs.port),
        database_name: newDs.database_name,
        username: newDs.username || undefined,
        password: newDs.password || undefined,
        description: newDs.description || undefined,
      })
      setNewDs({ name: '', type: 'MySQL', host: '', port: 3306, database_name: '', username: '', password: '', description: '' })
      const { data } = await api.get('/v1/data-sources/?limit=50')
      setItems(data?.data || [])
      alert('创建成功')
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '创建失败（需要管理员权限）')
    } finally {
      setCreating(false)
    }
  }

  function startEdit(i: DataSource) {
    setEditingId(i.id)
    setEditPatch({ name: i.name, host: i.host, port: i.port, database_name: i.database_name })
  }
  function cancelEdit() { setEditingId(null); setEditPatch({}) }
  async function saveEdit(id: number) {
    try {
      await updateDataSourceApi(id, { ...editPatch })
      const { data } = await api.get('/v1/data-sources/?limit=50')
      setItems(data?.data || [])
      setEditingId(null)
      setEditPatch({})
      alert('更新成功')
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '更新失败（需要管理员权限）')
    }
  }
  async function handleDelete(id: number) {
    if (!confirm('确认删除该数据源？')) return
    try {
      await deleteDataSourceApi(id)
      const { data } = await api.get('/v1/data-sources/?limit=50')
      setItems(data?.data || [])
      alert('删除成功')
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '删除失败（需要管理员权限）')
    }
  }

  async function reload() {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await api.get('/v1/data-sources/?limit=50')
      setItems(data?.data || [])
    } catch {
      setError('加载失败，请检查后端服务或网络')
      setItems([])
    } finally {
      setIsLoading(false)
    }
  }
  async function fetchLastSync() {
    try {
      const { data } = await getMetadataLastSyncApi()
      setLastSync(data?.summary || null)
    } catch (e) {
      // 保持静默，不影响主要功能
    }
  }
  async function handleTest(id: number) {
    try {
      setTestingId(id)
      const resp = await testConnectionApi(id)
      const ok = resp?.data?.success
      alert(ok ? '连接正常' : (resp?.data?.message || '连接失败'))
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '连接测试失败')
    } finally { setTestingId(null) }
  }
  async function handleSync(id: number) {
    try {
      setSyncingId(id)
      const resp = await syncTablesApi(id)
      const info = resp?.data
      alert(`同步完成：表${info?.tables_synced ?? '-'}，列${info?.columns_synced ?? '-'}`)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '同步失败（需要管理员权限）')
    } finally { setSyncingId(null) }
  }
  async function handleSyncMetadata() {
    try {
      setSyncingMeta(true)
      const resp = await syncMetadataApi()
      const s = resp?.data?.summary || resp?.data
      const msg = s ? `元数据同步完成：数据源${s.sources_total ?? '-'}，表${s.tables_total ?? '-'}，列${s.columns_total ?? '-'}；新增/更新${s.upserted_count ?? '-'}，删除${s.deleted_count ?? '-'}` : '同步完成'
      alert(msg)
      await fetchLastSync()
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '元数据同步失败（需要管理员权限）')
    } finally { setSyncingMeta(false) }
  }
  return (
    <div className="pg-card">
      <div className="section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>数据源管理</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={reload}>刷新列表</button>
          <button className="btn" onClick={handleSyncMetadata} disabled={syncingMeta}>{syncingMeta ? '同步中…' : '同步元数据'}</button>
        </div>
      </div>
      {/* 最近同步摘要 */}
      {lastSync ? (
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
          <span className="badge">最近同步时间：{lastSync.last_sync_time ? String(lastSync.last_sync_time) : '—'}</span>
          <span className="badge success">数据源：{lastSync.sources_total ?? 0}</span>
          <span className="badge success">表：{lastSync.tables_total ?? 0}</span>
          <span className="badge success">列：{lastSync.columns_total ?? 0}</span>
          <span className="badge ghost">新增/更新：{(lastSync.upserted_sources ?? 0) + (lastSync.upserted_tables ?? 0) + (lastSync.upserted_columns ?? 0)}</span>
          <span className="badge ghost">删除：{(lastSync.deleted_sources ?? 0) + (lastSync.deleted_tables ?? 0) + (lastSync.deleted_columns ?? 0)}</span>
        </div>
      ) : null}
      {error ? <div className="badge error" style={{ marginBottom: 8 }}>{error}</div> : null}
      {/* 新增数据源 */}
      <div className="controls" style={{ marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
        <input className="pg-input" placeholder="名称" value={newDs.name} onChange={e => setNewDs(v => ({ ...v, name: e.target.value }))} />
        <select className="pg-input" value={newDs.type} onChange={e => setNewDs(v => ({ ...v, type: e.target.value }))}>
          {typeOptions.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input className="pg-input" placeholder="主机" value={newDs.host} onChange={e => setNewDs(v => ({ ...v, host: e.target.value }))} />
        <input className="pg-input" placeholder="端口" type="number" value={newDs.port} onChange={e => setNewDs(v => ({ ...v, port: Number(e.target.value) || 0 }))} style={{ width: 100 }} />
        <input className="pg-input" placeholder="数据库名" value={newDs.database_name} onChange={e => setNewDs(v => ({ ...v, database_name: e.target.value }))} />
        <input className="pg-input" placeholder="用户名(可选)" value={newDs.username} onChange={e => setNewDs(v => ({ ...v, username: e.target.value }))} />
        <input className="pg-input" placeholder="密码(可选)" type="password" value={newDs.password} onChange={e => setNewDs(v => ({ ...v, password: e.target.value }))} />
        <input className="pg-input" placeholder="描述(可选)" value={newDs.description} onChange={e => setNewDs(v => ({ ...v, description: e.target.value }))} />
        <button className="btn primary" onClick={handleCreate} disabled={creating}>{creating ? '创建中…' : '创建数据源'}</button>
      </div>
      <div className="table-wrap">
      <table className="pg-table">
        <thead>
          <tr>
            <th onClick={() => toggleSort('id')}>ID</th>
            <th onClick={() => toggleSort('name')}>名称</th>
            <th onClick={() => toggleSort('type')}>类型</th>
            <th>地址</th>
            <th onClick={() => toggleSort('database_name')}>库</th>
            <th onClick={() => toggleSort('is_active')}>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr><td colSpan={7}>
              <div className="loading">加载中…</div>
            </td></tr>
          ) : sorted.length ? sorted.map(i => (
            <tr key={i.id}>
              <td>{i.id}</td>
              <td>{editingId === i.id ? (<input className="pg-input" value={editPatch.name || ''} onChange={e => setEditPatch(v => ({ ...v, name: e.target.value }))} />) : i.name}</td>
              <td>{i.type}</td>
              <td>
                {editingId === i.id ? (
                  <>
                    <input className="pg-input" value={editPatch.host || ''} onChange={e => setEditPatch(v => ({ ...v, host: e.target.value }))} style={{ width: 160 }} />
                    :
                    <input className="pg-input" type="number" value={editPatch.port ?? i.port} onChange={e => setEditPatch(v => ({ ...v, port: Number(e.target.value) || 0 }))} style={{ width: 90 }} />
                  </>
                ) : (
                  <span>{i.host}:{i.port}</span>
                )}
              </td>
              <td>{editingId === i.id ? (<input className="pg-input" value={editPatch.database_name || ''} onChange={e => setEditPatch(v => ({ ...v, database_name: e.target.value }))} />) : i.database_name}</td>
              <td>{i.is_active ? <span className="badge success">启用</span> : <span className="badge error">停用</span>}</td>
              <td>
                {editingId === i.id ? (
                  <>
                    <button className="btn primary" onClick={() => saveEdit(i.id)}>保存</button>
                    <button className="btn ghost" onClick={cancelEdit}>取消</button>
                  </>
                ) : (
                  <>
                    <button className="btn" onClick={() => startEdit(i)}>编辑</button>
                    <button className="btn" onClick={() => handleTest(i.id)} disabled={testingId === i.id || syncingId === i.id}>{testingId === i.id ? '测试中…' : '测试连接'}</button>
                    <button className="btn" onClick={() => handleSync(i.id)} disabled={syncingId === i.id || testingId === i.id}>{syncingId === i.id ? '同步中…' : '同步表结构'}</button>
                    <button className="btn error" onClick={() => handleDelete(i.id)}>删除</button>
                  </>
                )}
              </td>
            </tr>
          )) : (
            <tr><td colSpan={7}><div className="empty">暂无数据</div></td></tr>
          )}
        </tbody>
      </table>
      </div>
    </div>
  )
}