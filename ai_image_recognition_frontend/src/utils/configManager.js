/**
 * 用户配置管理模块
 * 用于存储和管理用户的导入导出路径等设置
 */

// 配置存储键名
const STORAGE_KEY = 'user_config';

// 默认配置
const defaultConfig = {
  importPath: '',
  exportPath: ''
};

/**
 * 获取用户配置
 * @returns {Object} 用户配置对象
 */
export const getUserConfig = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...defaultConfig, ...JSON.parse(stored) };
    }
  } catch (error) {
    console.error('读取用户配置失败:', error);
  }
  return { ...defaultConfig };
};

/**
 * 保存用户配置
 * @param {Object} config 配置对象
 */
export const saveUserConfig = (config) => {
  try {
    const currentConfig = getUserConfig();
    const newConfig = { ...currentConfig, ...config };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newConfig));
    return true;
  } catch (error) {
    console.error('保存用户配置失败:', error);
    return false;
  }
};

/**
 * 获取导入路径
 * @returns {string} 导入路径
 */
export const getImportPath = () => {
  return getUserConfig().importPath;
};

/**
 * 设置导入路径
 * @param {string} path 导入路径
 */
export const setImportPath = (path) => {
  return saveUserConfig({ importPath: path });
};

/**
 * 获取导出路径
 * @returns {string} 导出路径
 */
export const getExportPath = () => {
  return getUserConfig().exportPath;
};

/**
 * 设置导出路径
 * @param {string} path 导出路径
 */
export const setExportPath = (path) => {
  return saveUserConfig({ exportPath: path });
};
