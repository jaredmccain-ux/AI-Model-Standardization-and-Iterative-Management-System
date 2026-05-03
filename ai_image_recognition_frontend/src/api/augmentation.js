/**
 * 智能体数据增广 API：指令 + 图片 → 增广后的图片
 */
import axios from 'axios';
import { getApiUrl, TIMEOUT } from '@/config/api.js';

/**
 * 请求对选中的图片执行数据增广
 * @param {Object} payload - 增广参数
 * @param {File[]} payload.imageFiles - 图片文件列表
 * @param {'ai'|'classic'} payload.mode - 增广模式
 * @param {string} [payload.instruction] - AI 增广指令
 * @param {string} [payload.apiKey] - 用户自填 API Key
 * @param {string} [payload.providerPreset] - 供应商预设
 * @param {string} [payload.apiStyle] - 图像接口风格
 * @param {string} [payload.baseUrl] - 文本模型 API Base URL
 * @param {string} [payload.imageUrl] - 图像接口 URL
 * @param {string} [payload.textModel] - 文本模型
 * @param {string} [payload.imageModel] - 图像增广模型
 * @param {string[]} [payload.classicOptions] - 常规增广选项
 */
export async function runAugmentation({
  imageFiles,
  mode = 'ai',
  instruction = '',
  apiKey = '',
  providerPreset = '',
  apiStyle = '',
  baseUrl = '',
  imageUrl = '',
  textModel = '',
  imageModel = '',
  classicOptions = [],
}) {
  const formData = new FormData();
  formData.append('mode', mode);
  formData.append('instruction', instruction || '');
  if (apiKey) {
    formData.append('api_key', apiKey);
  }
  if (providerPreset) {
    formData.append('provider_preset', providerPreset);
  }
  if (apiStyle) {
    formData.append('api_style', apiStyle);
  }
  if (baseUrl) {
    formData.append('base_url', baseUrl);
  }
  if (imageUrl) {
    formData.append('image_url', imageUrl);
  }
  if (textModel) {
    formData.append('text_model', textModel);
  }
  if (imageModel) {
    formData.append('image_model', imageModel);
  }
  if (Array.isArray(classicOptions) && classicOptions.length > 0) {
    formData.append('classic_options', JSON.stringify(classicOptions));
  }
  imageFiles.forEach(file => {
    formData.append('images', file);
  });
  const { data } = await axios.post(
    `${getApiUrl()}/api/augmentation/run`,
    formData,
    {
      timeout: Math.max(TIMEOUT, 60000),
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}
