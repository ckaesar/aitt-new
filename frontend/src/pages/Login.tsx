import { useState } from 'react'
import { login, api } from '../api/client'
import { useNavigate } from 'react-router-dom'
import './Playground.css'

export default function Login() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('password')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleLogin() {
    setLoading(true)
    try {
      const resp = await login(username, password)
      const saved = localStorage.getItem('token')
      if (!saved) {
        // 登录接口返回成功但未写入令牌的情况，给出明确提示，便于定位后端或代理问题
        alert('登录成功但未收到令牌，请检查后端返回结构或代理配置\n响应示例：' + JSON.stringify(resp))
        return
      }
      navigate('/playground', { replace: true })
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || '登录失败，请检查用户名或密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pg-card">
      <div className="section-title">登录</div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <input className="pg-input" placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)} />
        <input className="pg-input" placeholder="密码" type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <button className="btn primary" onClick={handleLogin} disabled={loading}>{loading ? '登录中...' : '登录'}</button>
      </div>
    </div>
  )
}