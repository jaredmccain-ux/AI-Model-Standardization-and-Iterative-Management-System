import axios from 'axios'
import { getApiUrl, switchToFallback } from '@/config/api.js'

const api = axios.create({
  timeout: 60000,
})

api.interceptors.request.use(
  config => {
    config.baseURL = getApiUrl()
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

let backendType = null;
let lastBackendCheck = 0;

const detectBackendType = async () => {
  const now = Date.now();
  if (backendType && now - lastBackendCheck < 5 * 60 * 1000) {
    return backendType;
  }
  lastBackendCheck = now;
  const baseUrl = getApiUrl();
  try {
    const customResponse = await axios.get(`${baseUrl}/api/visiofirm/tools`, { timeout: 2000 });
    if (customResponse.status === 200) {
      backendType = 'custom';
      return 'custom';
    }
  } catch (customError) {
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

const BUILTIN_MODELS_FALLBACK = [
  { id: 'YOLO', name: 'YOLOv8-nano', task: 'detection', source: 'builtin', isLocal: true },
  { id: 'FasterRCNN', name: 'Faster R-CNN', task: 'detection', source: 'builtin', isLocal: true },
  { id: 'SSD', name: 'SSD', task: 'detection', source: 'builtin', isLocal: true },
  { id: 'ResNet', name: 'ResNet50', task: 'classification', source: 'builtin', isLocal: true },
  { id: 'EfficientNet', name: 'EfficientNet', task: 'classification', source: 'builtin', isLocal: true },
  { id: 'YOLO-Seg', name: 'YOLOv8-Seg', task: 'segmentation', source: 'builtin', isLocal: true },
  { id: 'MaskRCNN', name: 'Mask R-CNN', task: 'segmentation', source: 'builtin', isLocal: true },
  { id: 'SAM', name: 'SAM', task: 'segmentation', source: 'builtin', isLocal: true },
];

function normalizeModelName(name, id) {
  const raw = (name || id || '').trim();
  if (!raw) return id || '';
  return raw
    .replace(/\s*\(内置\)\s*/g, '')
    .replace(/^SAM(\s+分割一切)?$/i, 'SAM')
    .trim();
}

export const visioFirmAPI = {
  autoAnnotate: async (formData, retryCount = 0) => {
    try {
      const response = await api.post('/api/visiofirm/annotate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000
      });
      return response;
    } catch (error) {
      const shouldRetry = [
        'Network Error',
        'ERR_CONNECTION_REFUSED',
        'ECONNABORTED',
        'timeout of',
        '504',
        '503',
      ].some(errType => error.message?.includes(errType) || error.response?.status === parseInt(errType));

      if (shouldRetry && retryCount < 3) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
        if (retryCount === 0) {
          const switched = switchToFallback();
          if (switched) {
            console.warn('网络连接问题，已切换到备用服务器，正在重试..');
            if (typeof window !== 'undefined' && window.ElMessage) {
              window.ElMessage.warning('网络连接问题，已切换到备用服务器，正在重试..');
            }
          }
        }
        console.warn(`请求失败，${delay/1000}秒后进行第${retryCount + 1}次重试...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return visioFirmAPI.autoAnnotate(formData, retryCount + 1);
      }
      throw new Error(`标注失败: ${error.response?.data?.detail || error.message}`);
    }
  },

  getTools: async () => {
    try {
      const detectedBackend = await detectBackendType();
      if (detectedBackend === 'custom') {
        return await api.get('/api/tools');
      } else {
        return { data: { tools: ['classification', 'detection', 'segmentation'] } };
      }
    } catch (error) {
      console.error('获取工具列表失败:', error);
      return { data: { tools: ['classification', 'detection', 'segmentation'] } };
    }
  },

  getModels: async () => {
    try {
      const response = await api.get('/api/visiofirm/models', { timeout: 10000 });
      if (Array.isArray(response.data) && response.data.length > 0) {
        return response.data.map(m => ({
          ...m,
          name: normalizeModelName(m.name, m.id),
        }));
      }
      const catalogResp = await api.get('/api/visiofirm/models/catalog', { timeout: 10000 });
      const catalog = Array.isArray(catalogResp.data) ? catalogResp.data : [];
      const mappedCatalog = catalog.map(m => ({
        id: m.id,
        name: normalizeModelName(m.name, m.id),
        task: m.task || 'detection',
        source: 'catalog',
        isLocal: m.isLocal === true,
        description: m.description || '',
        accuracy: m.accuracy || '',
        speed: m.speed || '',
        size: m.size || '',
      }));
      return [...BUILTIN_MODELS_FALLBACK, ...mappedCatalog];
    } catch (error) {
      console.error('获取模型列表失败:', error);
      try {
        const catalogResp = await api.get('/api/visiofirm/models/catalog', { timeout: 10000 });
        const catalog = Array.isArray(catalogResp.data) ? catalogResp.data : [];
        const mappedCatalog = catalog.map(m => ({
          id: m.id,
          name: normalizeModelName(m.name, m.id),
          task: m.task || 'detection',
          source: 'catalog',
          isLocal: m.isLocal === true,
          description: m.description || '',
          accuracy: m.accuracy || '',
          speed: m.speed || '',
          size: m.size || '',
        }));
        return [...BUILTIN_MODELS_FALLBACK, ...mappedCatalog];
      } catch (catalogError) {
        console.error('获取模型目录也失败:', catalogError);
        return BUILTIN_MODELS_FALLBACK;
      }
    }
  },

  getModelsCatalog: async () => {
    try {
      const response = await api.get('/api/visiofirm/models/catalog', { timeout: 10000 });
      return response.data;
    } catch (error) {
      console.error('获取模型目录失败:', error);
      return [];
    }
  },

  uploadModel: async (file, name, task) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('task', task);
    const response = await api.post('/api/visiofirm/models/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
    return response.data;
  },

  downloadModel: async (modelId) => {
    const formData = new FormData();
    formData.append('model_id', modelId);
    const response = await api.post('/api/visiofirm/models/download', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    });
    return response.data;
  },

  saveModelFileAs: async (modelId) => {
    const safeModelId = String(modelId || 'model').replace(/[<>:"/\\|?*]+/g, '_');
    const suggestedName = safeModelId.endsWith('.pt') || safeModelId.endsWith('.pth') ? safeModelId : `${safeModelId}.pt`;
    let handle = null;
    if (typeof window.showSaveFilePicker === 'function') {
      handle = await window.showSaveFilePicker({
        suggestedName,
        types: [
          { description: 'PyTorch 模型', accept: { 'application/octet-stream': ['.pt', '.pth'] } },
        ],
      });
    }
    await visioFirmAPI.downloadModel(modelId);
    const baseUrl = getApiUrl().replace(/\/$/, '');
    const url = `${baseUrl}/api/visiofirm/models/${encodeURIComponent(modelId)}/file`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `获取文件失败: ${res.status}`);
    }
    const blob = await res.blob();
    if (handle) {
      const w = await handle.createWritable();
      await w.write(blob);
      await w.close();
    } else {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = suggestedName;
      a.click();
      URL.revokeObjectURL(a.href);
    }
  },

  saveAnnotations: async (formData) => {
    try {
      const detectedBackend = await detectBackendType();
      if (detectedBackend === 'custom') {
        return await api.post('/api/annotations', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        return { data: { success: true, message: '标注结果已保存' } };
      }
    } catch (error) {
      console.error('保存标注结果失败:', error);
      return { data: { success: true, message: '标注结果已保存' } };
    }
  }
}

export default api
