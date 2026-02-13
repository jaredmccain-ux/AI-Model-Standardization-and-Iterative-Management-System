/**
 * 智能体数据增广 API：指令 + 图片 → 增广后的图片
 */
import axios from 'axios';
import { getApiUrl, TIMEOUT } from '@/config/api.js';

/**
 * 请求对选中的图片执行智能增广
 * @param {File[]} imageFiles - 图片文件列表
 * @param {string} instruction - 增广指令（如：增加光照变化、添加轻微噪声）
 * @returns {Promise<{ augmented: { filename, image_base64, error? }[], params_used, api_configured }>}
 */
export async function runAugmentation(imageFiles, instruction) {
  const formData = new FormData();
  formData.append('instruction', instruction || '不做任何增广');
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
