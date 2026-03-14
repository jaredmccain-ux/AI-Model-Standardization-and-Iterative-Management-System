import axios from 'axios';
import { API_BASE_URL, TIMEOUT } from '@/config/api.js';

const API_BASE = API_BASE_URL;

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  config => {
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
};

export default api;