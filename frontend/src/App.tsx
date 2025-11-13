import { NavLink, Route, Routes, Navigate } from 'react-router-dom'
import { useState } from 'react'
import Login from './pages/Login'
import { setToken } from './api/client'
import Playground from './pages/Playground'
import DataSources from './pages/DataSources'
import QueryTemplates from './pages/QueryTemplates'
import Users from './pages/Users'
import RAGDocs from './pages/RAGDocs'
import './pages/Playground.css'

export default function App() {
  const [dark, setDark] = useState(true)
  return (
    <div className={dark ? 'pg-root theme-dark' : 'pg-root'}>
      <div className="pg-container">
        <div className="pg-header">
          <div className="pg-title">AI智能自助取数平台</div>
          <div className="pg-actions">
            <label className="switch">
              <input type="checkbox" checked={dark} onChange={e => setDark(e.target.checked)} /> 暗黑模式
            </label>
          </div>
        </div>
        <div className="pg-card" style={{ marginBottom: 16 }}>
          <nav style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <NavLink className={({ isActive }) => `btn ghost${isActive ? ' active' : ''}`} to="/playground">练习场</NavLink>
            <NavLink className={({ isActive }) => `btn ghost${isActive ? ' active' : ''}`} to="/data-sources">数据源管理</NavLink>
            <NavLink className={({ isActive }) => `btn ghost${isActive ? ' active' : ''}`} to="/query-templates">查询模板</NavLink>
            <NavLink className={({ isActive }) => `btn ghost${isActive ? ' active' : ''}`} to="/users">用户管理</NavLink>
            <NavLink className={({ isActive }) => `btn ghost${isActive ? ' active' : ''}`} to="/rag-docs">RAG文档</NavLink>
            <span style={{ flex: 1 }} />
            {localStorage.getItem('token') ? (
              <button className="btn" onClick={() => setToken(null)}>退出登录</button>
            ) : (
              <NavLink className={({ isActive }) => `btn primary${isActive ? ' active' : ''}`} to="/login">登录</NavLink>
            )}
          </nav>
        </div>
        <Routes>
          <Route path="/" element={<Navigate to="/playground" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/data-sources" element={<DataSources />} />
          <Route path="/query-templates" element={<QueryTemplates />} />
          <Route path="/users" element={<Users />} />
          <Route path="/rag-docs" element={<RAGDocs />} />
        </Routes>
      </div>
    </div>
  )
}