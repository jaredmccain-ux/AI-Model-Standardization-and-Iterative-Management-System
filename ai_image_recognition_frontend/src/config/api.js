/**
 * API配置管理文件
 * 统一管理所有后端接口地址，方便在本地开发和生产环境之间切换
 */

// 环境配置
const ENV_CONFIG = {
  // 开发环境（本地）
  development: {
    API_BASE_URL: 'http://localhost:8000',
    // 修改为更可靠的备用地址（开发环境下不启用）
    FALLBACK_API_URL: 'http://114.55.52.100:8000',  // 使用更稳定的备用服务器
    TIMEOUT: 30000
  },
  // 生产环境（线上）
  production: {
    // 与前端同域部署，后端通过 Nginx 代理到 `/api`，
    // 因此这里仅使用 `origin`，各请求在代码中统一拼接 `/api/...`
    API_BASE_URL: window.location.origin,
    FALLBACK_API_URL: 'http://114.55.52.100:8000',  // 统一使用同一个备用服务器
    TIMEOUT: 30000
  }
}

// 当前环境检测
// 方法1: 基于hostname自动检测
const getCurrentEnv = () => {
  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.')) {
    return 'development'
  }
  return 'production'
}

// 方法2: 手动设置环境（优先级更高）
// 如果需要强制指定环境，可以修改下面这行
// 可选值: 'development' | 'production' | 'auto'
// 环境选择：'development' | 'production' | 'auto'
// 使用自动检测以在本地与云端间无缝切换
const FORCE_ENV = 'auto'

// 获取当前环境配置
const getEnvConfig = () => {
  const env = FORCE_ENV === 'auto' ? getCurrentEnv() : FORCE_ENV
  return ENV_CONFIG[env] || ENV_CONFIG.development
}

// 导出当前配置
const config = getEnvConfig()

// API请求智能路由
let currentApiUrl = config.API_BASE_URL
let usingFallback = false

// 智能API请求函数
export const getApiUrl = () => {
  return currentApiUrl
}

// 切换到后备API（当nginx代理失败时）
export const switchToFallback = () => {
  // 仅在生产环境启用备用服务器切换，开发环境一律不切换，避免误判导致本地联调命中外网备用地址
  const env = FORCE_ENV === 'auto' ? getCurrentEnv() : FORCE_ENV
  if (env !== 'production') {
    console.info('开发环境不启用备用服务器切换，保持使用本地后端:', currentApiUrl)
    return false
  }
  if (config.FALLBACK_API_URL && !usingFallback) {
    currentApiUrl = config.FALLBACK_API_URL
    usingFallback = true
    console.warn('🔄 API切换到后备地址:', currentApiUrl)
    return true
  }
  return false
}

// 重置到主API
export const resetToMainApi = () => {
  currentApiUrl = config.API_BASE_URL
  usingFallback = false
  console.log('✅ API重置到主地址:', currentApiUrl)
}

export const API_BASE_URL = config.API_BASE_URL
export const TIMEOUT = config.TIMEOUT

// 导出完整配置对象
export default {
  API_BASE_URL: config.API_BASE_URL,
  FALLBACK_API_URL: config.FALLBACK_API_URL,
  TIMEOUT: config.TIMEOUT,
  // 当前环境信息
  currentEnv: FORCE_ENV === 'auto' ? getCurrentEnv() : FORCE_ENV,
  // API管理方法
  getApiUrl,
  switchToFallback,
  resetToMainApi,
  // 切换环境的方法（用于调试）
  switchEnv: (env) => {
    console.warn('请修改 src/config/api.js 中的 FORCE_ENV 变量来切换环境')
    console.log('当前环境:', getCurrentEnv())
    console.log('可用环境:', Object.keys(ENV_CONFIG))
  }
}

// 开发时的调试信息
if (process.env.NODE_ENV === 'development') {
  console.log('🔧 API配置信息:')
  console.log('当前环境:', config)
  console.log('API地址:', config.API_BASE_URL)
}
