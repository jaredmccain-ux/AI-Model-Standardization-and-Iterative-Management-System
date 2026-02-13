/**
 * 图像标注相关API
 */
import axios from 'axios';
import { getApiUrl, TIMEOUT } from '@/config/api.js';

// 创建带有拦截器的axios实例
const api = axios.create({
  baseURL: getApiUrl(),
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 调试axios实例配置
console.log('axios实例初始配置:', {
  baseURL: api.defaults.baseURL,
  timeout: api.defaults.timeout,
  headers: api.defaults.headers
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 确保使用最新的API地址
    config.baseURL = getApiUrl()
    
    // 详细记录请求配置
    console.log('=== 请求拦截器调试信息 ===')
    console.log('请求方法:', config.method)
    console.log('请求URL:', config.url)
    console.log('请求baseURL:', config.baseURL)
    console.log('完整请求URL:', config.baseURL + config.url)
    console.log('请求headers:', config.headers)
    console.log('请求数据:', config.data)
    console.log('========================')
    
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  error => {
    console.error('响应错误:', error.response?.status, error.response?.data)
    return Promise.reject(error)
  }
);

/**
 * 自动标注图像
 * @param {File} image - 图像文件
 * @param {String} tool - 标注工具类型 (object_detection, image_classification, image_segmentation)
 * @param {String} model - 选择的模型名称
 * @param {Array} categories - 类别列表
 * @returns {Promise} - 返回标注结果
 */
export const annotateImage = async (image, tool, model, categories) => {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('tool', tool);
  formData.append('model', model);
  
  // 添加类别信息
  formData.append('categories', JSON.stringify(categories));
  
  return api.post('/api/auto_annotate', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

/**
 * 导出标注结果
 * @param {Object} data - 标注数据
 * @param {String} format - 导出格式 (json, coco, voc, yolo, csv, yaml)
 * @returns {Object} - 包含下载链接和MIME类型的对象
 */
export const exportAnnotationData = (data, format = 'json') => {
  let content, mimeType, extension;
  
  switch (format) {
    case 'json':
      content = JSON.stringify(data, null, 2);
      mimeType = 'application/json';
      extension = 'json';
      break;
      
    case 'coco':
      content = convertToCOCO(data);
      mimeType = 'application/json';
      extension = 'json';
      break;
      
    case 'voc':
      content = convertToPascalVOC(data);
      mimeType = 'application/xml';
      extension = 'xml';
      break;
      
    case 'yolo':
      content = convertToYOLO(data);
      mimeType = 'text/plain';
      extension = 'txt';
      break;
      
    case 'csv':
      content = convertToCSV(data);
      mimeType = 'text/csv';
      extension = 'csv';
      break;
      
    case 'yaml':
    case 'yml':
      content = convertToYAML(data);
      mimeType = 'application/x-yaml';
      extension = 'yaml';
      break;
      
    default:
      content = JSON.stringify(data, null, 2);
      mimeType = 'application/json';
      extension = 'json';
  }
  
  return {
    content,
    url: `data:${mimeType};charset=utf-8,${encodeURIComponent(content)}`,
    mimeType,
    extension
  };
};

/**
 * 将标注数据转换为COCO格式
 * @param {Object} data - 原始标注数据
 * @returns {String} - COCO格式的JSON字符串
 */
function convertToCOCO(data) {
  const cocoFormat = {
    info: {
      description: 'AI Image Recognition Annotation Dataset',
      version: '1.0',
      year: new Date().getFullYear(),
      date_created: new Date().toISOString()
    },
    images: [
      {
        id: 1,
        file_name: data.image,
        width: 0, // 需要从图片实际获取
        height: 0 // 需要从图片实际获取
      }
    ],
    annotations: [],
    categories: []
  };
  
  // 提取所有唯一类别
  const categories = [...new Set(data.annotations.map(ann => ann.label || 'unknown'))];
  categories.forEach((category, index) => {
    cocoFormat.categories.push({
      id: index + 1,
      name: category,
      supercategory: 'object'
    });
  });
  
  // 转换标注
  data.annotations.forEach((annotation, index) => {
    if (annotation.type === 'bbox' && annotation.bbox) {
      const categoryId = categories.indexOf(annotation.label || 'unknown') + 1;
      cocoFormat.annotations.push({
        id: index + 1,
        image_id: 1,
        category_id: categoryId,
        bbox: [
          annotation.bbox.x,
          annotation.bbox.y,
          annotation.bbox.width,
          annotation.bbox.height
        ],
        area: annotation.bbox.width * annotation.bbox.height,
        segmentation: [],
        iscrowd: 0
      });
    }
  });
  
  return JSON.stringify(cocoFormat, null, 2);
}

/**
 * 将标注数据转换为Pascal VOC XML格式
 * @param {Object} data - 原始标注数据
 * @returns {String} - XML字符串
 */
function convertToPascalVOC(data) {
  let xml = `<?xml version="1.0" encoding="UTF-8"?>
`;
  xml += `<annotation>
`;
  xml += `  <folder>Annotations</folder>
`;
  xml += `  <filename>${data.image}</filename>
`;
  xml += `  <source>
`;
  xml += `    <database>AI Image Recognition</database>
`;
  xml += `  </source>
`;
  xml += `  <size>
`;
  xml += `    <width>0</width>
`; // 需要从图片实际获取
  xml += `    <height>0</height>
`; // 需要从图片实际获取
  xml += `    <depth>3</depth>
`;
  xml += `  </size>
`;
  xml += `  <segmented>0</segmented>
`;
  
  // 添加对象
  data.annotations.forEach(annotation => {
    if (annotation.type === 'bbox' && annotation.bbox) {
      xml += `  <object>
`;
      xml += `    <name>${annotation.label || 'unknown'}</name>
`;
      xml += `    <pose>Unspecified</pose>
`;
      xml += `    <truncated>0</truncated>
`;
      xml += `    <difficult>0</difficult>
`;
      xml += `    <bndbox>
`;
      xml += `      <xmin>${Math.round(annotation.bbox.x)}</xmin>
`;
      xml += `      <ymin>${Math.round(annotation.bbox.y)}</ymin>
`;
      xml += `      <xmax>${Math.round(annotation.bbox.x + annotation.bbox.width)}</xmax>
`;
      xml += `      <ymax>${Math.round(annotation.bbox.y + annotation.bbox.height)}</ymax>
`;
      xml += `    </bndbox>
`;
      xml += `  </object>
`;
    }
  });
  
  xml += `</annotation>`;
  return xml;
}

/**
 * 将标注数据转换为YOLO格式
 * @param {Object} data - 原始标注数据
 * @returns {String} - YOLO格式的文本字符串
 */
function convertToYOLO(data) {
  // 提取所有唯一类别
  const categories = [...new Set(data.annotations.map(ann => ann.label || 'unknown'))];
  let yoloContent = '';
  
  data.annotations.forEach(annotation => {
    if (annotation.type === 'bbox' && annotation.bbox) {
      const categoryId = categories.indexOf(annotation.label || 'unknown');
      // YOLO格式要求中心点坐标和宽高是相对于图片尺寸的归一化值
      // 这里假设图片尺寸为1000x1000进行归一化，实际使用时应该从图片获取
      const imgWidth = 1000; // 需要从图片实际获取
      const imgHeight = 1000; // 需要从图片实际获取
      
      const x = (annotation.bbox.x + annotation.bbox.width / 2) / imgWidth;
      const y = (annotation.bbox.y + annotation.bbox.height / 2) / imgHeight;
      const width = annotation.bbox.width / imgWidth;
      const height = annotation.bbox.height / imgHeight;
      
      yoloContent += `${categoryId} ${x.toFixed(6)} ${y.toFixed(6)} ${width.toFixed(6)} ${height.toFixed(6)}\n`;
    }
  });
  
  return yoloContent;
}

/**
 * 将标注数据转换为CSV格式
 * @param {Object} data - 原始标注数据
 * @returns {String} - CSV字符串
 */
function convertToCSV(data) {
  let csvContent = 'image,label,type,x,y,width,height\n';
  
  data.annotations.forEach(annotation => {
    if (annotation.type === 'bbox' && annotation.bbox) {
      csvContent += `${data.image},`;
      csvContent += `${annotation.label || 'unknown'},`;
      csvContent += `${annotation.type},`;
      csvContent += `${annotation.bbox.x},`;
      csvContent += `${annotation.bbox.y},`;
      csvContent += `${annotation.bbox.width},`;
      csvContent += `${annotation.bbox.height}\n`;
    }
  });
  
  return csvContent;
}

/**
 * 将标注数据转换为YAML格式
 * @param {Object} data - 原始标注数据
 * @returns {String} - YAML字符串
 */
function convertToYAML(data) {
  // 手动构建YAML格式，避免引入额外依赖
  let yamlContent = '';
  
  // 添加图片信息
  yamlContent += `image: ${data.image}\n`;
  yamlContent += `tool: ${data.tool || 'unknown'}\n`;
  yamlContent += `annotations:\n`;
  
  // 添加标注信息
  data.annotations.forEach((annotation, index) => {
    yamlContent += `  - id: ${index + 1}\n`;
    yamlContent += `    type: ${annotation.type || 'unknown'}\n`;
    yamlContent += `    label: ${annotation.label || 'unknown'}\n`;
    yamlContent += `    confidence: ${annotation.confidence || 1.0}\n`;
    
    // 添加边界框信息
    if (annotation.bbox) {
      yamlContent += `    bbox:\n`;
      yamlContent += `      x: ${annotation.bbox.x}\n`;
      yamlContent += `      y: ${annotation.bbox.y}\n`;
      yamlContent += `      width: ${annotation.bbox.width}\n`;
      yamlContent += `      height: ${annotation.bbox.height}\n`;
    }
    
    // 添加多边形点信息
    if (annotation.points && Array.isArray(annotation.points)) {
      yamlContent += `    points: [\n`;
      annotation.points.forEach(point => {
        yamlContent += `      [${point[0]}, ${point[1]}],\n`;
      });
      yamlContent += `    ]\n`;
    }
  });
  
  return yamlContent;
}

/**
 * 保存单个标注数据到后端
 * @param {Object} annotationData - 标准化的标注数据
 * @returns {Promise} - 返回保存结果
 */
export const saveSingleAnnotation = async (annotationData) => {
  try {
    // 根据后端API要求，调整参数格式
    const requestData = {
      imageName: annotationData.image_name, // 后端期望驼峰命名
      tool: annotationData.type || 'obb',    // 后端需要tool字段
      annotation: annotationData             // 整个标注数据包装在annotation字段中
    };
    
    console.log('发送到后端的数据:', requestData);
    console.log('API基础URL:', getApiUrl());
    console.log('完整请求URL:', `${getApiUrl()}/api/annotations/single`);
    
    const response = await api.post('/api/annotations/single', requestData);
    return response;
  } catch (error) {
    console.error('保存单个标注失败:', error);
    // 更详细地记录错误信息
    console.error('错误响应:', error.response);
    console.error('错误数据:', error.response?.data);
    
    // 处理不同类型的错误信息
    let errorMessage;
    if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === 'string') {
        errorMessage = error.response.data.detail;
      } else if (Array.isArray(error.response.data.detail)) {
        // 处理数组形式的错误详情
        errorMessage = error.response.data.detail.map(detail => 
          typeof detail === 'string' ? detail : JSON.stringify(detail)
        ).join(', ');
      } else {
        // 处理对象形式的错误详情
        errorMessage = JSON.stringify(error.response.data.detail);
      }
    } else if (error.response?.data?.message) {
      errorMessage = error.response.data.message;
    } else {
      errorMessage = error.message;
    }
    
    throw new Error(`保存失败：${errorMessage}`);
  }
};

/**
 * 批量保存人工标注
 * @param {Object} data - 包含imageName、tool和annotations的数据对象
 * @returns {Promise} - 返回保存结果
 */
export const saveBatchAnnotations = async (data) => {
  return api.post('/api/annotations/batch', data);
};

/**
 * 删除标注
 * @param {Number} annotationId - 标注ID
 * @returns {Promise} - 返回删除结果
 */
export const deleteAnnotation = async (annotationId) => {
  return api.delete(`/api/annotations/${annotationId}`);
};

/**
 * 获取图像的标注数据
 * @param {String} imageName - 图像文件名
 * @returns {Promise} - 返回图像的标注数据
 */
export const getImageAnnotations = async (imageName) => {
  try {
    // 先获取图片列表，找到对应的image_id
    const imagesResponse = await api.get('/api/images/list');
    const images = imagesResponse.data.images;
    const image = images.find(img => img.filename === imageName);
    
    if (image) {
      // 根据image_id获取标注数据
      const annotationsResponse = await api.get(`/api/images/${image.id}/annotations`);
      
      // 合并自动标注和手动标注为前端期望的格式
      const allAnnotations = [];
      
      // 添加自动标注
      annotationsResponse.data.auto_annotations.forEach(ann => {
        allAnnotations.push(ann.annotation_data);
      });
      
      // 添加手动标注
      annotationsResponse.data.manual_annotations.forEach(ann => {
        allAnnotations.push(ann.annotation_data);
      });
      
      // 转换为前端期望的格式
      return { 
        data: { 
          annotations: allAnnotations 
        } 
      };
    } else {
      // 如果找不到对应的图片，返回空的标注列表
      console.log(`未找到图片 ${imageName} 的记录，返回空列表`);
      return { data: { annotations: [] } };
    }
  } catch (error) {
    // 如果服务器返回404或其他错误，返回一个空的标注列表，而不是抛出错误
    console.error(`获取图片 ${imageName} 标注失败:`, error);
    return { data: { annotations: [] } };
  }
};