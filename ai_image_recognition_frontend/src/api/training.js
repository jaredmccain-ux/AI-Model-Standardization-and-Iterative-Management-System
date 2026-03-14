import axios from 'axios'
import { API_BASE_URL, TIMEOUT, switchToFallback, getApiUrl } from '@/config/api.js'

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 确保使用最新的API地址
    config.baseURL = getApiUrl()
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  error => {
    console.error('响应错误:', error.response?.status, error.response?.data)
    
    // 处理网络错误和连接拒绝错误
    if (error.message.includes('Network Error') || 
        error.message.includes('ERR_CONNECTION_REFUSED')) {
      // 尝试切换到备用API
      const switched = switchToFallback();
      if (switched) {
        console.warn('网络连接问题，已切换到备用服务器');
      }
    }
    
    return Promise.reject(error)
  }
)

// 训练API
export const trainingAPI = {
  // 启动常规训练
  startRegularTraining: (config) => {
    return api.post('/api/training/regular', config)
  },

  // 启动增量训练
  startIncrementalTraining: (config) => {
    return api.post('/api/training/incremental', config)
  },

  // 启动冻结策略训练
  startFreezeStrategyTraining: (config) => {
    return api.post('/api/training/freeze-strategy', config)
  },

  // 启动蒸馏训练
  startDistillationTraining: (config) => {
    return api.post('/api/training/distillation', config)
  },

  // 获取所有训练任务
  getAllTasks: () => {
    return api.get('/api/training/tasks')
  },

  // 获取特定训练任务
  getTask: (taskId) => {
    return api.get(`/api/training/tasks/${taskId}`)
  },

  // 获取训练任务日志
  getTaskLogs: (taskId) => {
    return api.get(`/api/training/tasks/${taskId}/logs`)
  },

  // 取消训练任务
  cancelTask: (taskId) => {
    return api.post(`/api/training/tasks/${taskId}/cancel`)
  },

  // 获取训练服务状态
  getTrainingStatus: () => {
    return api.get('/api/training/status')
  }
}

export default api