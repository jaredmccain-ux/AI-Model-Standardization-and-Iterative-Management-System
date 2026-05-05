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

export const uploadProjectStagingImages = async (projectId, images, { overwrite = false } = {}) => {
  const formData = new FormData();
  (images || []).forEach((file) => {
    formData.append('images', file);
  });
  formData.append('overwrite', overwrite ? '1' : '0');
  return api.post(`/api/projects/${projectId}/staging/images`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

export const annotateProjectFile = async (projectId, payload) => {
  return api.post(`/api/projects/${projectId}/auto_annotate/file`, payload);
};

export const importStagingToProjectDataset = async (projectId, payload) => {
  return api.post(`/api/projects/${projectId}/dataset/from-staging`, payload);
};

/**
 * 将“标注页面当前会话”的图片与标注结果导入到某个项目的数据集目录中（生成 images/train|val 与 labels/train|val + dataset.yaml）
 * 后端接口：POST /api/projects/{projectId}/dataset/from-annotations
 */
export const importAnnotationsToProjectDataset = async ({
  projectId,
  images,
  annotationsByFilename,
  categories,
  valRatio = 0.2,
  splitsByFilename,
}) => {
  const formData = new FormData();
  images.forEach((file) => {
    formData.append('images', file);
  });
  formData.append('annotations', JSON.stringify(annotationsByFilename || {}));
  if (Array.isArray(categories)) {
    formData.append('categories', JSON.stringify(categories));
  }
  formData.append('val_ratio', String(valRatio));
  if (splitsByFilename && typeof splitsByFilename === 'object') {
    formData.append('splits', JSON.stringify(splitsByFilename));
  }

  return api.post(`/api/projects/${projectId}/dataset/from-annotations`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

export const getProjectDatasetState = async (projectId, options = {}) => {
  return api.get(`/api/projects/${projectId}/dataset/state`, { params: options });
};

/**
 * 导出标注结果
 * @param {Object} data - 标注数据，需含 image、annotations、tool；可选 width/height（像素）用于 COCO/VOC/DOTA 正确换算 bbox
 * @param {String} format - 导出格式 (json, coco, voc, yolo, dota, csv, yaml)
 * @returns {Object} - 包含 content, url, mimeType, extension
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
      
    case 'dota':
      content = convertToDOTA(data);
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

// 内部 bbox 为百分比 (0-100)。data 可含 width/height 像素尺寸用于正确导出。
function isBoxAnnotation(ann) {
  return (ann.type === 'bbox' || ann.type === 'bounding_box' || ann.type === 'obb') && ann.bbox;
}
function isOBB(ann) {
  return ann.type === 'obb' && ann.bbox && (ann.bbox.angle != null && ann.bbox.angle !== 0);
}
// 百分比 bbox → 像素 bbox
function percentBboxToPixel(bbox, imgWidth, imgHeight) {
  if (!imgWidth || !imgHeight) return null;
  return {
    x: (bbox.x / 100) * imgWidth,
    y: (bbox.y / 100) * imgHeight,
    width: (bbox.width / 100) * imgWidth,
    height: (bbox.height / 100) * imgHeight
  };
}
// OBB：由中心、半宽高、角度计算四个顶点（像素）
function obbToFourCorners(bbox, imgWidth, imgHeight) {
  if (!imgWidth || !imgHeight || bbox.width <= 0 || bbox.height <= 0) return null;
  const cx = (bbox.x + bbox.width / 2) / 100 * imgWidth;
  const cy = (bbox.y + bbox.height / 2) / 100 * imgHeight;
  const hw = (bbox.width / 100) * imgWidth / 2;
  const hh = (bbox.height / 100) * imgHeight / 2;
  const a = bbox.angle != null ? bbox.angle : 0;
  const cos = Math.cos(a);
  const sin = Math.sin(a);
  const corners = [
    [-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]
  ].map(([dx, dy]) => ({
    x: cx + dx * cos - dy * sin,
    y: cy + dx * sin + dy * cos
  }));
  return corners;
}

/**
 * 将标注数据转换为COCO格式
 * @param {Object} data - 原始标注数据，可含 width/height（像素）以正确转换 bbox
 * @returns {String} - COCO格式的JSON字符串
 */
function convertToCOCO(data) {
  const imgW = data.width || 0;
  const imgH = data.height || 0;
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
        width: imgW,
        height: imgH
      }
    ],
    annotations: [],
    categories: []
  };
  
  const categories = [...new Set(data.annotations.map(ann => ann.label || 'unknown'))];
  categories.forEach((category, index) => {
    cocoFormat.categories.push({
      id: index + 1,
      name: category,
      supercategory: 'object'
    });
  });
  
  data.annotations.forEach((annotation, index) => {
    if (!isBoxAnnotation(annotation)) return;
    const categoryId = categories.indexOf(annotation.label || 'unknown') + 1;
    const bbox = annotation.bbox;
    const pixel = percentBboxToPixel(bbox, imgW, imgH);
    const isRotated = isOBB(annotation);
    let cocoBbox;
    let segmentation = [];
    let area;
    if (pixel) {
      cocoBbox = [pixel.x, pixel.y, pixel.width, pixel.height];
      area = pixel.width * pixel.height;
      if (isRotated) {
        const corners = obbToFourCorners(bbox, imgW, imgH);
        if (corners) segmentation = [corners.flatMap(c => [c.x, c.y])];
      }
    } else {
      cocoBbox = [bbox.x, bbox.y, bbox.width, bbox.height];
      area = bbox.width * bbox.height;
    }
    cocoFormat.annotations.push({
      id: index + 1,
      image_id: 1,
      category_id: categoryId,
      bbox: cocoBbox,
      area,
      segmentation: segmentation.length ? segmentation : [],
      iscrowd: 0
    });
  });
  
  return JSON.stringify(cocoFormat, null, 2);
}

/**
 * 将标注数据转换为Pascal VOC XML格式
 * @param {Object} data - 原始标注数据，可含 width/height（像素）
 * @returns {String} - XML字符串
 */
function convertToPascalVOC(data) {
  const imgW = data.width || 0;
  const imgH = data.height || 0;
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
  xml += `    <width>${imgW}</width>
`;
  xml += `    <height>${imgH}</height>
`;
  xml += `    <depth>3</depth>
`;
  xml += `  </size>
`;
  xml += `  <segmented>0</segmented>
`;
  
  data.annotations.forEach(annotation => {
    if (!isBoxAnnotation(annotation)) return;
    const bbox = annotation.bbox;
    let xmin, ymin, xmax, ymax;
    if (imgW && imgH) {
      const pixel = percentBboxToPixel(bbox, imgW, imgH);
      xmin = pixel.x;
      ymin = pixel.y;
      xmax = pixel.x + pixel.width;
      ymax = pixel.y + pixel.height;
      if (isOBB(annotation)) {
        const corners = obbToFourCorners(bbox, imgW, imgH);
        if (corners) {
          const xs = corners.map(c => c.x);
          const ys = corners.map(c => c.y);
          xmin = Math.min(...xs);
          ymin = Math.min(...ys);
          xmax = Math.max(...xs);
          ymax = Math.max(...ys);
        }
      }
    } else {
      xmin = bbox.x;
      ymin = bbox.y;
      xmax = bbox.x + bbox.width;
      ymax = bbox.y + bbox.height;
    }
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
    xml += `      <xmin>${Math.round(xmin)}</xmin>
`;
    xml += `      <ymin>${Math.round(ymin)}</ymin>
`;
    xml += `      <xmax>${Math.round(xmax)}</xmax>
`;
    xml += `      <ymax>${Math.round(ymax)}</ymax>
`;
    xml += `    </bndbox>
`;
    xml += `  </object>
`;
  });
  
  xml += `</annotation>`;
  return xml;
}

/**
 * 将标注数据转换为YOLO格式（0-1 归一化，内部 bbox 为百分比 0-100）
 * @param {Object} data - 原始标注数据
 * @returns {String} - YOLO格式的文本字符串
 */
function convertToYOLO(data) {
  const categories = [...new Set(data.annotations.map(ann => ann.label || 'unknown'))];
  let yoloContent = '';
  
  data.annotations.forEach(annotation => {
    if (!isBoxAnnotation(annotation)) return;
    const bbox = annotation.bbox;
    const categoryId = categories.indexOf(annotation.label || 'unknown');
    // 内部为 0-100 百分比，YOLO 要求 0-1：直接除以 100
    const x = (bbox.x + bbox.width / 2) / 100;
    const y = (bbox.y + bbox.height / 2) / 100;
    const width = bbox.width / 100;
    const height = bbox.height / 100;
    yoloContent += `${categoryId} ${x.toFixed(6)} ${y.toFixed(6)} ${width.toFixed(6)} ${height.toFixed(6)}\n`;
  });
  
  return yoloContent;
}

/**
 * 将标注数据转换为 DOTA/Fair1m 风格 OBB 文本格式（每行：x1 y1 x2 y2 x3 y3 x4 y4 类别 difficulty）
 * 需 data.width / data.height 以输出像素坐标
 * @param {Object} data - 原始标注数据
 * @returns {String} - DOTA 格式文本
 */
function convertToDOTA(data) {
  const imgW = data.width || 0;
  const imgH = data.height || 0;
  let lines = [];
  data.annotations.forEach(annotation => {
    if (!isBoxAnnotation(annotation)) return;
    const bbox = annotation.bbox;
    const category = (annotation.label || 'unknown').replace(/\s+/g, '_');
    const difficulty = 0;
    let coords;
    if (imgW && imgH) {
      if (isOBB(annotation)) {
        const corners = obbToFourCorners(bbox, imgW, imgH);
        if (corners) coords = corners.flatMap(c => [c.x.toFixed(2), c.y.toFixed(2)]).join(' ');
      }
      if (!coords) {
        const pixel = percentBboxToPixel(bbox, imgW, imgH);
        const xmin = pixel.x; const ymin = pixel.y;
        const xmax = pixel.x + pixel.width; const ymax = pixel.y + pixel.height;
        coords = [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax].map(n => n.toFixed(2)).join(' ');
      }
    } else {
      const xmin = bbox.x; const ymin = bbox.y;
      const xmax = bbox.x + bbox.width; const ymax = bbox.y + bbox.height;
      coords = [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax].map(n => Number(n).toFixed(2)).join(' ');
    }
    lines.push(`${coords} ${category} ${difficulty}`);
  });
  return lines.join('\n');
}

/**
 * 将标注数据转换为CSV格式
 * @param {Object} data - 原始标注数据
 * @returns {String} - CSV字符串
 */
function convertToCSV(data) {
  let csvContent = 'image,label,type,x,y,width,height\n';
  
  data.annotations.forEach(annotation => {
    if (isBoxAnnotation(annotation)) {
      const b = annotation.bbox;
      csvContent += `${data.image},`;
      csvContent += `${annotation.label || 'unknown'},`;
      csvContent += `${annotation.type},`;
      csvContent += `${b.x},`;
      csvContent += `${b.y},`;
      csvContent += `${b.width},`;
      csvContent += `${b.height}\n`;
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
