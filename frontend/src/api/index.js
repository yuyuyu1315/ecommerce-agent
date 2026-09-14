import axios from 'axios'

// 后端 API 客户端（开发环境经 Vite 代理到 8001）
const api = axios.create({
  baseURL: '/api',
  timeout: 180000
})

export default api
