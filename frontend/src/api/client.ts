import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
})

// 载入本地token
const savedToken = localStorage.getItem('token')
if (savedToken) {
  api.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`
}

// 总是从 localStorage 注入最新的 Authorization 头，避免默认头不同步的问题
api.interceptors.request.use((config) => {
  try {
    const t = localStorage.getItem('token')
    if (t) {
      if (!config.headers) config.headers = {}
      config.headers['Authorization'] = `Bearer ${t}`
    }
  } catch {}
  return config
})

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem('token', token)
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
  }
}

export async function login(username: string, password: string) {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)
  // 兼容 OAuth2PasswordRequestForm 的标准字段
  form.set('grant_type', 'password')
  const { data } = await api.post('/v1/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  // 兼容不同后端返回结构：优先 DataResponse.data.access_token，其次顶层或其它字段名
  const token = data?.data?.access_token || data?.access_token || data?.token
  if (token) setToken(token)
  return data
}

export async function executeQuery(dataSourceId: number, sql: string, maxRows: number = 1000) {
  const payload = { data_source_id: dataSourceId, sql, max_rows: maxRows }
  const { data } = await api.post('/v1/queries/execute', payload)
  return data
}

export async function saveQuery(queryId: number, queryName: string, tags?: string[]) {
  const payload = { query_id: queryId, query_name: queryName, tags }
  const { data } = await api.post('/v1/queries/save', payload)
  return data
}

export async function shareQuery(queryId: number, isShared: boolean) {
  const payload = { query_id: queryId, is_shared: isShared }
  const { data } = await api.post('/v1/queries/share', payload)
  return data
}

// ---- 用户管理 ----
export async function registerUser(payload: {
  username: string; email: string; password: string;
  full_name?: string; department?: string; role?: string;
}) {
  const { data } = await api.post('/v1/auth/register', payload)
  return data
}

export async function updateUserApi(userId: number, payload: {
  email?: string; full_name?: string; department?: string; role?: string; is_active?: boolean
}) {
  const { data } = await api.patch(`/v1/users/${userId}`, payload)
  return data
}

export async function deleteUserApi(userId: number) {
  const { data } = await api.delete(`/v1/users/${userId}`)
  return data
}

// ---- 数据源管理 ----
export async function createDataSource(payload: {
  name: string; type: string; host: string; port: number;
  database_name: string; username?: string; password?: string; description?: string
}) {
  const { data } = await api.post('/v1/data-sources', payload)
  return data
}

export async function updateDataSourceApi(id: number, payload: {
  name?: string; host?: string; port?: number; database_name?: string;
  username?: string; password?: string; description?: string; is_active?: boolean
}) {
  const { data } = await api.patch(`/v1/data-sources/${id}`, payload)
  return data
}

export async function deleteDataSourceApi(id: number) {
  const { data } = await api.delete(`/v1/data-sources/${id}`)
  return data
}

export async function testConnectionApi(id: number) {
  const { data } = await api.post(`/v1/data-sources/${id}/test-connection`)
  return data
}

export async function syncTablesApi(id: number) {
  const { data } = await api.post(`/v1/data-sources/${id}/sync-tables`)
  return data
}

// ---- 元数据同步 ----
export async function syncMetadataApi() {
  const { data } = await api.post('/v1/metadata/sync')
  return data
}

export async function getMetadataLastSyncApi() {
  const { data } = await api.get('/v1/metadata/last-sync')
  return data
}

// ---- 表与字段查询 ----
export async function listTablesApi(dataSourceId: number, limit: number = 100, offset: number = 0) {
  const { data } = await api.get(`/v1/data-sources/${dataSourceId}/tables`, {
    params: { limit, offset },
  })
  return data
}

export async function listColumnsByTableApi(tableId: number) {
  const { data } = await api.get(`/v1/data-sources/tables/${tableId}/columns`)
  return data
}

// ---- 查询模板管理 ----
export async function createTemplateApi(payload: {
  name: string; description?: string; category?: string;
  natural_language_template: string; sql_template: string; parameters?: any; is_public?: boolean
}) {
  const { data } = await api.post('/v1/queries/templates', payload)
  return data
}

export async function updateTemplateApi(id: number, payload: {
  name?: string; description?: string; category?: string;
  natural_language_template?: string; sql_template?: string; parameters?: any; is_public?: boolean
}) {
  const { data } = await api.patch(`/v1/queries/templates/${id}`, payload)
  return data
}

export async function deleteTemplateApi(id: number) {
  const { data } = await api.delete(`/v1/queries/templates/${id}`)
  return data
}

// ---- RAG 文档管理与查询 ----
export async function searchRagDocs(query: string, topK: number = 4) {
  const { data } = await api.get('/v1/rag/search', { params: { q: query, top_k: topK } })
  return data
}

export async function upsertRagDocs(documents: Array<{ id?: string; text: string; source?: string }>) {
  const { data } = await api.post('/v1/rag/documents', { documents })
  return data
}

// 简单的401拦截处理
api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    // 开发阶段：不对401进行任何提示或跳转，保持接口无登录直通
    return Promise.reject(err)
  }
)