import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, createTemplateApi, updateTemplateApi, deleteTemplateApi } from '../api/client'
import './Playground.css'

type Template = {
  id: number
  name: string
  description?: string
  category?: string
  natural_language_template?: string
  sql_template?: string
  parameters?: any
  is_public?: boolean
}

export default function QueryTemplates() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Template[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [newTpl, setNewTpl] = useState({
    name: '', category: '', description: '', natural_language_template: '', sql_template: '', parametersText: '', is_public: false
  })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editPatch, setEditPatch] = useState<{ name?: string; category?: string; description?: string; natural_language_template?: string; sql_template?: string; parametersText?: string; is_public?: boolean }>({})
  async function loadTemplates() {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await api.get('/v1/queries/templates', { params: { limit: 50 } })
      setItems(data?.data || [])
    } catch {
      setError('加载失败，请检查后端服务或网络')
      setItems([])
    } finally {
      setIsLoading(false)
    }
  }
  useEffect(() => { loadTemplates() }, [])
  return (
    <div className="pg-card">
      <div className="section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>查询模板</span>
        <button className="btn" onClick={loadTemplates}>刷新列表</button>
      </div>
      {error ? <div className="badge error" style={{ marginBottom: 8 }}>{error}</div> : null}
      {/* 新增模板 */}
      <div className="controls" style={{ marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
        <input className="pg-input" placeholder="模板名称" value={newTpl.name} onChange={e => setNewTpl(v => ({ ...v, name: e.target.value }))} />
        <input className="pg-input" placeholder="分类(可选)" value={newTpl.category} onChange={e => setNewTpl(v => ({ ...v, category: e.target.value }))} />
        <input className="pg-input" placeholder="描述(可选)" value={newTpl.description} onChange={e => setNewTpl(v => ({ ...v, description: e.target.value }))} />
        <textarea className="pg-input" placeholder="自然语言模板(例如：统计近7天GMV)" value={newTpl.natural_language_template} onChange={e => setNewTpl(v => ({ ...v, natural_language_template: e.target.value }))} />
        <textarea className="pg-input" placeholder="SQL模板(例如：SELECT ... WHERE ... )" value={newTpl.sql_template} onChange={e => setNewTpl(v => ({ ...v, sql_template: e.target.value }))} />
        <textarea className="pg-input" placeholder={'参数定义(JSON，可选)，例如：{ "start_days": 7 }'} value={newTpl.parametersText} onChange={e => setNewTpl(v => ({ ...v, parametersText: e.target.value }))} />
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={newTpl.is_public} onChange={e => setNewTpl(v => ({ ...v, is_public: e.target.checked }))} /> 公开
        </label>
        <button className="btn primary" disabled={creating} onClick={async () => {
          if (!newTpl.name || !newTpl.natural_language_template || !newTpl.sql_template) { alert('请填写名称、自然语言模板与SQL模板'); return }
          let params: any = undefined
          if (newTpl.parametersText?.trim()) {
            try {
              params = JSON.parse(newTpl.parametersText)
            } catch {
              alert('参数定义需为合法的JSON');
              return
            }
          }
          try {
            setCreating(true)
            await createTemplateApi({
              name: newTpl.name,
              category: newTpl.category || undefined,
              description: newTpl.description || undefined,
              natural_language_template: newTpl.natural_language_template,
              sql_template: newTpl.sql_template,
              parameters: params,
              is_public: !!newTpl.is_public,
            })
            const { data } = await api.get('/v1/queries/templates', { params: { limit: 50 } })
            setItems(data?.data || [])
            setNewTpl({ name: '', category: '', description: '', natural_language_template: '', sql_template: '', parametersText: '', is_public: false })
            alert('创建成功')
          } catch (e: any) {
            alert(e?.response?.data?.detail || e?.message || '创建失败（需要管理员权限）')
          } finally { setCreating(false) }
        }}>{creating ? '创建中…' : '创建模板'}</button>
      </div>
      <div className="table-wrap">
        <table className="pg-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>分类</th>
              <th>描述</th>
              <th>自然语言模板</th>
              <th>SQL模板</th>
              <th>公开</th>
              <th>参数定义</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={9}><div className="loading">加载中…</div></td></tr>
            ) : items.length ? items.map(i => (
              <tr key={i.id}>
                <td>{i.id}</td>
                <td>{editingId === i.id ? (<input className="pg-input" value={editPatch.name || ''} onChange={e => setEditPatch(v => ({ ...v, name: e.target.value }))} />) : i.name}</td>
                <td>{editingId === i.id ? (<input className="pg-input" value={editPatch.category || ''} onChange={e => setEditPatch(v => ({ ...v, category: e.target.value }))} />) : (i.category || '-')}</td>
                <td>{editingId === i.id ? (<input className="pg-input" value={editPatch.description || ''} onChange={e => setEditPatch(v => ({ ...v, description: e.target.value }))} />) : (i.description || '-')}</td>
                <td>{editingId === i.id ? (<textarea className="pg-input" value={editPatch.natural_language_template || ''} onChange={e => setEditPatch(v => ({ ...v, natural_language_template: e.target.value }))} />) : (i.natural_language_template || '-')}</td>
                <td>{editingId === i.id ? (<textarea className="pg-input" value={editPatch.sql_template || ''} onChange={e => setEditPatch(v => ({ ...v, sql_template: e.target.value }))} />) : ((i.sql_template && i.sql_template.length > 120) ? (i.sql_template.slice(0, 120) + '…') : (i.sql_template || '-'))}</td>
                <td>{editingId === i.id ? (
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <input type="checkbox" checked={!!editPatch.is_public} onChange={e => setEditPatch(v => ({ ...v, is_public: e.target.checked }))} /> 公开
                  </label>
                ) : (i.is_public ? <span className="badge success">公开</span> : <span className="badge">私有</span>)}</td>
                <td>{editingId === i.id ? (
                  <textarea className="pg-input" placeholder="参数定义JSON(可选)" value={editPatch.parametersText || ''} onChange={e => setEditPatch(v => ({ ...v, parametersText: e.target.value }))} />
                ) : (
                  (() => {
                    const txt = i.parameters ? JSON.stringify(i.parameters) : ''
                    return txt ? ((txt.length > 80) ? (txt.slice(0, 80) + '…') : txt) : '-'
                  })()
                )}</td>
                <td>
                  {editingId === i.id ? (
                    <>
                      <button className="btn primary" onClick={async () => {
                        try {
                          if (!editPatch.name || !editPatch.natural_language_template || !editPatch.sql_template) { alert('请填写名称、自然语言模板与SQL模板'); return }
                          let params: any = undefined
                          if (editPatch.parametersText?.trim()) {
                            try {
                              params = JSON.parse(editPatch.parametersText)
                            } catch {
                              alert('参数定义需为合法的JSON');
                              return
                            }
                          }
                          await updateTemplateApi(i.id, { name: editPatch.name, category: editPatch.category, description: editPatch.description, natural_language_template: editPatch.natural_language_template, sql_template: editPatch.sql_template, is_public: editPatch.is_public, parameters: params })
                          const { data } = await api.get('/v1/queries/templates', { params: { limit: 50 } })
                          setItems(data?.data || [])
                          setEditingId(null)
                          setEditPatch({})
                          alert('更新成功')
                        } catch (e: any) {
                          alert(e?.response?.data?.detail || e?.message || '更新失败（需要管理员权限）')
                        }
                      }}>保存</button>
                      <button className="btn ghost" onClick={() => { setEditingId(null); setEditPatch({}) }}>取消</button>
                    </>
                  ) : (
                    <>
                      <button className="btn" onClick={() => { setEditingId(i.id); setEditPatch({ name: i.name, category: i.category, description: i.description, natural_language_template: i.natural_language_template, sql_template: i.sql_template, parametersText: i.parameters ? JSON.stringify(i.parameters, null, 2) : '', is_public: !!i.is_public }) }}>编辑</button>
                      <button className="btn primary" onClick={() => {
                        if (!i.sql_template) { alert('该模板暂无SQL'); return }
                        try {
                          const payload = { sql: i.sql_template, parameters: i.parameters || null, name: i.name, autoExecute: true }
                          localStorage.setItem('tpl_apply', JSON.stringify(payload))
                          navigate('/playground')
                        } catch {
                          alert('应用失败，请重试')
                        }
                      }}>应用到练习场</button>
                      <button className="btn error" onClick={async () => {
                        if (!confirm('确认删除该模板？')) return
                        try {
                          await deleteTemplateApi(i.id)
                          const { data } = await api.get('/v1/queries/templates', { params: { limit: 50 } })
                          setItems(data?.data || [])
                          alert('删除成功')
                        } catch (e: any) {
                          alert(e?.response?.data?.detail || e?.message || '删除失败（需要管理员权限）')
                        }
                      }}>删除</button>
                    </>
                  )}
                </td>
              </tr>
            )) : (
              <tr><td colSpan={9}><div className="empty">暂无模板</div></td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}