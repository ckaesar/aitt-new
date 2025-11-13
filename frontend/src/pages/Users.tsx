import { useEffect, useMemo, useState } from 'react'
import { api, registerUser, updateUserApi, deleteUserApi } from '../api/client'
import './Playground.css'

type User = {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
}

export default function Users() {
  const [items, setItems] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<keyof User>('id')
  const [sortAsc, setSortAsc] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newUser, setNewUser] = useState({
    username: '', email: '', password: '', full_name: '', department: '', role: 'viewer'
  })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editPatch, setEditPatch] = useState<{ email?: string; full_name?: string; department?: string; role?: string; is_active?: boolean }>({})
  const roleOptions = ['admin', 'analyst', 'user', 'viewer']

  async function loadUsers() {
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await api.get('/v1/users/?limit=50')
      setItems(data?.data || [])
    } catch (e) {
      setError('加载失败或无权限，请检查后端服务与配置')
      setItems([])
    } finally {
      setIsLoading(false)
    }
  }
  useEffect(() => {
    loadUsers()
  }, [])

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

  function toggleSort(field: keyof User) {
    if (sortBy === field) setSortAsc(!sortAsc)
    else { setSortBy(field); setSortAsc(true) }
  }
  async function handleCreate() {
    if (!newUser.username || !newUser.email || !newUser.password) {
      alert('请填写用户名、邮箱和密码');
      return
    }
    try {
      setCreating(true)
      await registerUser({
        username: newUser.username,
        email: newUser.email,
        password: newUser.password,
        full_name: newUser.full_name || undefined,
        department: newUser.department || undefined,
        role: newUser.role,
      })
      setNewUser({ username: '', email: '', password: '', full_name: '', department: '', role: 'viewer' })
      await loadUsers()
      alert('用户创建成功')
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  function startEdit(u: User) {
    setEditingId(u.id)
    setEditPatch({ email: u.email, role: u.role, is_active: u.is_active })
  }

  function cancelEdit() {
    setEditingId(null)
    setEditPatch({})
  }

  async function saveEdit(id: number) {
    try {
      const payload = { ...editPatch }
      await updateUserApi(id, payload)
      await loadUsers()
      setEditingId(null)
      setEditPatch({})
      alert('更新成功')
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '更新失败')
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('确认删除该用户？')) return
    try {
      await deleteUserApi(id)
      await loadUsers()
      alert('删除成功')
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '删除失败')
    }
  }
  return (
    <div className="pg-card">
      <div className="section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>用户管理</span>
        <button className="btn" onClick={loadUsers}>刷新列表</button>
      </div>
      {error ? <div className="badge error" style={{ marginBottom: 8 }}>{error}</div> : null}
      {/* 新增用户 */}
      <div className="controls" style={{ marginBottom: 12, gap: 8 }}>
        <input className="pg-input" placeholder="用户名" value={newUser.username} onChange={e => setNewUser(v => ({ ...v, username: e.target.value }))} />
        <input className="pg-input" placeholder="邮箱" value={newUser.email} onChange={e => setNewUser(v => ({ ...v, email: e.target.value }))} />
        <input className="pg-input" placeholder="密码" type="password" value={newUser.password} onChange={e => setNewUser(v => ({ ...v, password: e.target.value }))} />
        <input className="pg-input" placeholder="全名" value={newUser.full_name} onChange={e => setNewUser(v => ({ ...v, full_name: e.target.value }))} />
        <input className="pg-input" placeholder="部门" value={newUser.department} onChange={e => setNewUser(v => ({ ...v, department: e.target.value }))} />
        <select className="pg-input" value={newUser.role} onChange={e => setNewUser(v => ({ ...v, role: e.target.value }))}>
          {roleOptions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <button className="btn primary" onClick={handleCreate} disabled={creating}>{creating ? '创建中…' : '创建用户'}</button>
      </div>
      <div className="table-wrap">
      <table className="pg-table">
        <thead>
          <tr>
            <th onClick={() => toggleSort('id')}>ID</th>
            <th onClick={() => toggleSort('username')}>用户名</th>
            <th onClick={() => toggleSort('email')}>邮箱</th>
            <th onClick={() => toggleSort('role')}>角色</th>
            <th onClick={() => toggleSort('is_active')}>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr><td colSpan={6}><div className="loading">加载中…</div></td></tr>
          ) : sorted.length ? sorted.map(i => (
            <tr key={i.id}>
              <td>{i.id}</td>
              <td>{i.username}</td>
              <td>
                {editingId === i.id ? (
                  <input className="pg-input" value={editPatch.email || ''} onChange={e => setEditPatch(v => ({ ...v, email: e.target.value }))} />
                ) : i.email}
              </td>
              <td>
                {editingId === i.id ? (
                  <select className="pg-input" value={editPatch.role || i.role} onChange={e => setEditPatch(v => ({ ...v, role: e.target.value }))}>
                    {roleOptions.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                ) : i.role}
              </td>
              <td>
                {editingId === i.id ? (
                  <label className="switch">
                    <input type="checkbox" checked={!!editPatch.is_active} onChange={e => setEditPatch(v => ({ ...v, is_active: e.target.checked }))} /> 启用
                  </label>
                ) : (i.is_active ? <span className="badge success">启用</span> : <span className="badge error">停用</span>)}
              </td>
              <td>
                {editingId === i.id ? (
                  <>
                    <button className="btn primary" onClick={() => saveEdit(i.id)}>保存</button>
                    <button className="btn ghost" onClick={cancelEdit}>取消</button>
                  </>
                ) : (
                  <>
                    <button className="btn" onClick={() => startEdit(i)}>编辑</button>
                    <button className="btn error" onClick={() => handleDelete(i.id)}>删除</button>
                  </>
                )}
              </td>
            </tr>
          )) : (
            <tr><td colSpan={6}><div className="empty">暂无数据</div></td></tr>
          )}
        </tbody>
      </table>
      </div>
    </div>
  )
}