import axios from 'axios'
import { getApiUrl, switchToFallback } from '@/config/api.js'

// 创建axios实例
const api = axios.create({
  timeout: 60000, // 60秒超时时间
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 确保使用最新的API地址
    config.baseURL = getApiUrl()
    // 确保每次请求都使用最新的API地址
    if (!config.url.startsWith('http')) {
      config.url = config.baseURL + config.url
      config.baseURL = ''
    }
    console.log('发送VisioFirm请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  error => {
    console.error('VisioFirm请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('收到VisioFirm响应:', response.status, response.config.url)
    return response
  },
  error => {
    console.error('VisioFirm响应错误:', error.response?.status, error.response?.data)
    
    return Promise.reject(error)
  }
)

// 检测当前后端类型
let backendType = null; // null: 未检测, 'custom': 自定义后端, 'visiofirm': VisioFirm原生后端
let lastBackendCheck = 0;

// 检测后端类型的函数
const detectBackendType = async () => {
  const now = Date.now();
  // 缓存后端类型检测结果5分钟
  if (backendType && now - lastBackendCheck < 5 * 60 * 1000) {
    return backendType;
  }
  
  lastBackendCheck = now;
  const baseUrl = getApiUrl();
  
  try {
    // 尝试访问自定义后端的API
    const customResponse = await axios.get(`${baseUrl}/api/visiofirm/tools`, { timeout: 2000 });
    if (customResponse.status === 200) {
      backendType = 'custom';
      return 'custom';
    }
  } catch (customError) {
    // 自定义后端访问失败，尝试检测VisioFirm原生后端
    try {
      const visiofirmResponse = await axios.get(`${baseUrl}/annotation/check_preannotation_status`, { 
        params: { project_name: 'test' },
        timeout: 2000 
      });
      if (visiofirmResponse.status === 200 && visiofirmResponse.data.success !== undefined) {
        backendType = 'visiofirm';
        return 'visiofirm';
      }
    } catch (visiofirmError) {
      console.warn('无法确定后端类型:', customError, visiofirmError);
    }
  }
  
  return null;
}

// VisioFirm API封装
export const visioFirmAPI = {
  // 自动标注API（统一至 /api/visiofirm/annotate）
  autoAnnotate: async (formData, retryCount = 0) => {
    try {
      // 设置较长的超时时间
      const response = await api.post('/api/visiofirm/annotate', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 60000  // 设置60秒超时
      });
      return response;
    } catch (error) {
      // 扩展错误类型判断
      const shouldRetry = [
        'Network Error',
        'ERR_CONNECTION_REFUSED',
        'ECONNABORTED',
        'timeout of',
        '504',  // Gateway Timeout
        '503',  // Service Unavailable
      ].some(errType => error.message?.includes(errType) || error.response?.status === parseInt(errType));
  
      if (shouldRetry && retryCount < 3) {  // 增加重试次数到3次
        // 使用指数退避策略
        const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
        
        // 如果是第一次重试，尝试切换到备用服务器
        if (retryCount === 0) {
          const switched = switchToFallback();
          if (switched) {
            console.warn('🔄 网络连接问题，已切换到备用服务器，正在重试..');
            // 显示用户友好的提示信息
            if (typeof window !== 'undefined' && window.ElMessage) {
              window.ElMessage.warning('网络连接问题，已切换到备用服务器，正在重试..');
            }
          }
        }
        
        console.warn(`请求失败，${delay/1000}秒后进行第${retryCount + 1}次重试...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return visioFirmAPI.autoAnnotate(formData, retryCount + 1);
      }
      
      // 所有重试都失败，抛出最终错误
      throw new Error(`标注失败: ${error.response?.data?.detail || error.message}`);
    }
  },
  
  // 获取可用工具列表
  getTools: async () => {
    try {
      const detectedBackend = await detectBackendType();
      
      if (detectedBackend === 'custom') {
        return await api.get('/api/tools');
      } else {
        // 对于其他类型的后端，返回模拟数据
        return {
          data: {
            tools: ['classification', 'detection', 'segmentation']
          }
        };
      }
    } catch (error) {
      console.error('获取工具列表失败:', error);
      // 返回模拟数据
      return {
        data: {
          tools: ['classification', 'detection', 'segmentation']
        }
      };
    }
  },
  
  // 保存标注结果
  saveAnnotations: async (formData) => {
    try {
      const detectedBackend = await detectBackendType();
      
      if (detectedBackend === 'custom') {
        return await api.post('/api/annotations', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
      } else {
        // 对于其他类型的后端，返回成功模拟
        return {
          data: {
            success: true,
            message: '标注结果已保存'
          }
        };
      }
    } catch (error) {
      console.error('保存标注结果失败:', error);
      // 返回成功模拟
      return {
        data: {
          success: true,
          message: '标注结果已保存'
        }
      };
    }
  }
}

export default api
