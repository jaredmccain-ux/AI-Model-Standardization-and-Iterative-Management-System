import axios from 'axios';
import { TIMEOUT, getApiUrl, switchToFallback } from '@/config/api.js';

// 创建axios实例
const api = axios.create({
  baseURL: getApiUrl(),
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    config.baseURL = getApiUrl();
    console.log('发送请求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  error => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('收到响应:', response.status, response.config.url);
    return response;
  },
  error => {
    console.error('响应错误:', error.response?.status, error.response?.data);

    if (
      error.message?.includes('Network Error') ||
      error.message?.includes('ERR_CONNECTION_REFUSED')
    ) {
      const switched = switchToFallback?.();
      if (switched) {
        console.warn('网络连接问题，已切换到备用服务器');
      }
    }
    return Promise.reject(error);
  }
);

// 评估API
export const evaluationAPI = {
  // 启动评估
  startEvaluation: (modelId, data) => {
    return api.post(`/api/models/${modelId}/evaluate`, data);
  },

  // 获取评估结果
  getEvaluationResult: (evaluationId, modelId = 'yolov8n') => {
    return api.get(`/api/models/${modelId}/evaluation/${evaluationId}`);
  },

  // 获取模型的所有评估
  getModelEvaluations: (modelId) => {
    return api.get(`/api/models/${modelId}/evaluations`);
  },

  // 获取项目最新训练产物中的 evaluation_data.json
  getLatestEvaluationData: (projectId) => {
    return api.get(`/api/projects/${projectId}/artifacts/evaluation-data`);
  },

  // 获取项目下的评估记录列表（扫描 projects/<id>/evaluation）
  listProjectEvaluations: (projectId, limit = 50) => {
    return api.get(`/api/projects/${projectId}/evaluations`, { params: { limit } });
  },

  // 获取某次评估详情（metrics.json + analysis_report.md）
  getProjectEvaluation: (projectId, evaluationId) => {
    return api.get(`/api/projects/${projectId}/evaluations/${evaluationId}`);
  },

  // 重新生成项目最新训练产物的 evaluation_data.json
  regenerateLatestEvaluationData: (projectId) => {
    return api.post(`/api/projects/${projectId}/artifacts/evaluation-data/regenerate`);
  },
};

export default api;
