<template>
  <div class="visiofirm-annotator">
    <div v-if="!isLoaded" class="loading-state" v-loading="!isLoaded">
      <p>加载VisioFirm标注工具中...</p>
    </div>
    
    <div v-else class="annotator-container">
      <!-- 工具栏 -->
      <div class="annotation-toolbar">
        <el-button 
          type="primary" 
          @click="startAutoAnnotation" 
          :disabled="!currentImage || isAnnotating"
        >
          {{ isAnnotating ? 'AI标注中...' : 'AI自动标注' }}
        </el-button>
        
        <!-- 人工标注相关按钮 -->
        <el-button 
          type="success" 
          @click="startManualAnnotation" 
          :disabled="!currentImage || isManualAnnotating || !classes.length"
        >
          开始人工标注
        </el-button>
        <el-button 
          type="danger" 
          @click="endManualAnnotation" 
          :disabled="!isManualAnnotating"
        >
          结束人工标注
        </el-button>
        
        <!-- 人工标注绘制类型选择 -->
        <el-radio-group v-model="currentDrawingType" style="margin-left: 10px;" :disabled="!isManualAnnotating">
          <el-radio-button label="bbox">边界框</el-radio-button>
          <el-radio-button label="polygon">多边形</el-radio-button>
        </el-radio-group>
        
        <el-button 
          type="warning" 
          @click="clearCurrentAnnotations" 
          :disabled="!hasAnnotations"
        >
          清除当前标注
        </el-button>
        <el-button 
          type="primary" 
          @click="saveAnnotations" 
          :disabled="!hasAnnotations"
        >
          保存标注
        </el-button>
        <el-button 
          type="info" 
          @click="exportAnnotations" 
          :disabled="!hasAnnotations"
        >
          导出标注结果
        </el-button>
        
        <!-- 模块切换 -->
        <el-radio-group v-model="currentModule" style="margin-left: 20px;">
          <el-radio-button label="classification">图像分类</el-radio-button>
          <el-radio-button label="detection">图像检测</el-radio-button>
          <el-radio-button label="segmentation">图像分割</el-radio-button>
        </el-radio-group>
      </div>
      
      <!-- 标注画布区域 -->
      <div class="annotation-canvas-container">
        <div v-if="!currentImage" class="no-image-placeholder">
          <p>请选择一张图片开始标注</p>
        </div>
        <div v-else class="image-annotation-area">
          <!-- VisioFirm标注画布 -->
          <div class="visiofirm-canvas-wrapper">
            <img 
              :src="currentImage.url" 
              :alt="currentImage.name" 
              class="annotation-image"
              ref="annotationImage"
            />
            <!-- 标注覆盖层 -->
            <div class="annotation-overlay" ref="annotationOverlay"></div>
            
            <!-- 分类结果显示 -->
            <div v-if="currentModule === 'classification' && classificationResult" class="classification-result">
              <div class="classification-box">
                <div class="class-name">{{ classificationResult.label }}</div>
                <div class="confidence">置信度: {{ (classificationResult.confidence * 100).toFixed(1) }}%</div>
              </div>
            </div>
          </div>
          
          <!-- 标注控制面板 -->
          <div class="annotation-controls">
            <h4>标注控制</h4>
            <div class="class-list">
              <h5>类别列表</h5>
              <el-input 
                v-model="newClassName" 
                placeholder="输入新类别名" 
                style="margin-bottom: 10px;"
              />
              <el-button 
                type="primary" 
                size="small" 
                @click="addClass" 
                :disabled="!newClassName.trim()"
              >
                添加类别
              </el-button>
              <el-divider />
              <div class="class-items">
                <div 
                  v-for="(className, index) in classes" 
                  :key="index"
                  class="class-item"
                >
                  <span>{{ className }}</span>
                  <el-button 
                    type="danger" 
                    size="small" 
                    circle 
                    @click="removeClass(index)"
                    class="remove-class-btn"
                  >
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 标注结果预览 -->
      <div class="annotations-preview">
        <h4>标注结果</h4>
        <div class="annotations-list">
          <!-- 分类结果预览 -->
          <div v-if="classificationResult && currentModule === 'classification'" class="annotation-item">
            <div class="annotation-info">
              <span class="annotation-type">分类</span>
              <span class="annotation-label">{{ classificationResult.label }}</span>
            </div>
            <div class="annotation-meta">
              置信度: {{ (classificationResult.confidence * 100).toFixed(1) }}%
            </div>
          </div>
          
          <!-- 检测结果预览 -->
          <div v-if="currentModule === 'detection'">
            <h5>检测对象列表</h5>
            <div v-for="(annotation, index) in annotations" :key="index" class="annotation-item">
              <div class="annotation-info">
                <span class="annotation-type">边界框 #{{ index + 1 }}</span>
                <span class="annotation-label">{{ annotation.label }}</span>
              </div>
              <div class="annotation-meta">
                位置: x={{ annotation.x.toFixed(1) }}%, y={{ annotation.y.toFixed(1) }}%, 宽={{ annotation.width.toFixed(1) }}%, 高={{ annotation.height.toFixed(1) }}%
                <span v-if="annotation.confidence"> | 置信度: {{ (annotation.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          
          <!-- 分割结果预览 -->
          <div v-if="currentModule === 'segmentation'">
            <h5>分割区域列表</h5>
            <div v-for="(annotation, index) in annotations" :key="index" class="annotation-item">
              <div class="annotation-info">
                <span class="annotation-type">多边形 #{{ index + 1 }}</span>
                <span class="annotation-label">{{ annotation.label }}</span>
              </div>
              <div class="annotation-meta">
                顶点数量: {{ annotation.points.length }}个
                <span v-if="annotation.confidence"> | 置信度: {{ (annotation.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { ElMessage, ElMessageBox, ElButton, ElRadioGroup, ElRadioButton, ElInput, ElDivider } from 'element-plus';
import 'element-plus/dist/index.css';
import { Close } from '@element-plus/icons-vue';
import axios from 'axios';
import { getApiUrl, switchToFallback } from '@/config/api.js';

// 从父组件接收的props
const props = defineProps({
  currentImage: {
    type: Object,
    default: null
  }
});

// 状态管理
const isLoaded = ref(false);
const isAnnotating = ref(false);
const annotations = ref([]);
const classificationResult = ref(null);
const classes = ref([]); // 移除默认类别
const newClassName = ref('');
const currentModule = ref('detection'); // 默认图像检测模块
const annotationImage = ref(null);
const annotationOverlay = ref(null);

// 人工标注相关变量
const isManualAnnotating = ref(false);
const currentManualAnnotation = ref(null);
const currentDrawingType = ref('bbox'); // 默认边界框

// 计算属性
const hasAnnotations = computed(() => annotations.value.length > 0);

// 组件挂载时初始化VisioFirm
onMounted(async () => {
  try {
    // 初始化时获取可用的标注工具列表
    await fetchAnnotationTools();
    isLoaded.value = true;
    ElMessage.success('VisioFirm标注工具加载成功');
  } catch (error) {
    console.error('VisioFirm初始化失败:', error);
    ElMessage.error('VisioFirm标注工具加载失败');
  }
});

// 获取可用的标注工具列表
const fetchAnnotationTools = async () => {
  try {
    const response = await axios.get(`${getApiUrl()}/api/visiofirm/tools`);
    if (response.data && Array.isArray(response.data)) {
      // 保存标注工具列表
      annotationTools.value = response.data;
    }
  } catch (error) {
    console.error('获取标注工具列表失败:', error);
    // 备用工具列表
    annotationTools.value = [
      {value: 'bbox', label: '边界框'},
      {value: 'polygon', label: '多边形'},
      {value: 'keypoint', label: '关键点'},
      {value: 'obb', label: '方向框'}
    ];
  }
};

// 添加标注工具列表状态
const annotationTools = ref([]);

// 监听当前图片变化
watch(() => props.currentImage, async (newImage) => {
  if (newImage && isLoaded.value) {
    await nextTick();
    // 清除之前的标注
    annotations.value = [];
    // 重置画布
    resetCanvas();
  }
});

// 重置画布
const resetCanvas = () => {
  if (annotationImage.value && annotationOverlay.value) {
    // 同步覆盖层尺寸与图片尺寸
    const img = annotationImage.value;
    const overlay = annotationOverlay.value;
    overlay.style.width = `${img.width}px`;
    overlay.style.height = `${img.height}px`;
    // 清除覆盖层内容
    overlay.innerHTML = '';
  }
};

// 开始AI自动标注
const startAutoAnnotation = async () => {
  if (!props.currentImage) {
    ElMessage.warning('请先选择一张图片');
    return;
  }

  // 根据模块类型确定标注工具
  let toolType = 'bbox'; // 默认边界框
  if (currentModule.value === 'segmentation') {
    toolType = 'polygon';
  }

  isAnnotating.value = true;
  
  // 获取当前选择的模型
// 定义获取默认模型的方法
const getDefaultModelForModule = (moduleType) => {
  const defaults = {
    classification: 'resnet50',
    detection: 'yolov8n',
    segmentation: 'yolov8-seg'
  };
  return defaults[moduleType] || null;
};

const selectedModelId = selectedModel.value || getDefaultModelForModule(currentModule.value);
const modelInfo = currentModelInfo.value;
const modelName = modelInfo ? modelInfo.name : selectedModelId;
  
  ElMessage.info(`AI正在使用${modelName}模型分析图片，请稍候...`);

  try {
    // 调用VisioFirm后端API进行AI标注
    const formData = new FormData();
    formData.append('image', props.currentImage.file);
    formData.append('module_type', currentModule.value); // 使用module_type参数
    formData.append('model', selectedModelId); // 添加模型选择参数
    formData.append('classes', JSON.stringify(classes.value));

    // 使用getApiUrl配置调用后端VisioFirm统一接口
    const response = await axios.post(`${getApiUrl()}/api/visiofirm/annotate`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      // 在请求失败时尝试切换到备用API
      validateStatus: (status) => {
        if (status >= 500) {
          switchToFallback();
        }
        return status < 500;
      }
    });
    
    // 如果响应中包含使用的模型信息，显示给用户
    if (response.data && response.data.model_used) {
      console.log(`使用模型: ${response.data.model_used}`);
    }

    // 根据VisioFirm API规范处理响应
    if (response.data && response.data.success) {
      // 检测或分割模块 - 显示标注结果
      if (response.data.annotations && Array.isArray(response.data.annotations) && response.data.annotations.length > 0) {
        // 预处理和验证标注数据
        annotations.value = [];
        for (let i = 0; i < response.data.annotations.length; i++) {
          const annotation = response.data.annotations[i];
          // 确保返回的是对象格式
          if (typeof annotation !== 'object' || annotation === null) {
            console.warn('无效的标注对象在索引 ' + i + '，跳过', annotation);
            continue;
          }
          
          // 验证多边形点格式
          if (annotation.points) {
            if (!Array.isArray(annotation.points)) {
              console.warn('多边形点不是数组在索引 ' + i + '，重置为空数组');
              annotation.points = [];
            } else {
              // 清理无效的点
              const validPoints = [];
              for (let j = 0; j < annotation.points.length; j++) {
                const point = annotation.points[j];
                const isValid = Array.isArray(point) && point.length >= 2 && 
                               typeof point[0] === 'number' && typeof point[1] === 'number';
                if (!isValid) {
                  console.warn('无效的多边形点在索引 ' + i + ', 点 ' + j, point);
                } else {
                  validPoints.push(point);
                }
              }
              annotation.points = validPoints;
            }
          }
          
          // 确保字段名称一致
          if (annotation.score !== undefined && annotation.confidence === undefined) {
            annotation.confidence = annotation.score;
          }
          if (annotation.type === undefined) {
            annotation.type = currentModule.value === 'segmentation' ? 'polygon' : 'bbox';
          }
          
          annotations.value.push(annotation);
        }
        
        classificationResult.value = null; // 清空分类结果
        // 绘制标注结果
        drawAnnotations();
        ElMessage.success(`AI标注完成，共检测到${annotations.value.length}个对象`);
      } else {
        ElMessage.warning('未检测到任何对象');
        annotations.value = [];
        classificationResult.value = null;
      }
    } else {
      // 处理失败情况
      const errorMessage = response.data?.detail || '标注处理失败';
      ElMessage.error(errorMessage);
      annotations.value = [];
      classificationResult.value = null;
    }
  } catch (error) {
    console.error('AI标注失败 - 详细信息:', error);
    console.log('错误类型:', typeof error);
    console.log('错误响应:', error.response);
    console.log('错误请求配置:', error.config);
    if (error.config) {
      console.log('请求URL:', error.config.url);
      console.log('请求方法:', error.config.method);
      console.log('请求头:', error.config.headers);
    }
    
    // 尝试直接连接后端API进行测试
    try {
      console.log('尝试直接连接后端测试...');
      const testResponse = await fetch(`${getApiUrl()}/api/visiofirm/tools`);
      console.log('直接连接测试结果:', testResponse.status, testResponse.statusText);
    } catch (testError) {
      console.log('直接连接测试失败:', testError.message);
    }
    
    ElMessage.error('AI标注失败: ' + (error.response?.data?.detail || error.message));
  } finally {
    isAnnotating.value = false;
  }
};

// 绘制标注结果
const drawAnnotations = () => {
  if (!annotationOverlay.value) return;
  
  // 清空现有标注
  const overlay = annotationOverlay.value;
  overlay.innerHTML = '';
  
  // 绘制分类结果文本
  if (classificationResult.value) {
    const resultElement = document.createElement('div');
    resultElement.className = 'classification-result';
    resultElement.style.position = 'absolute';
    resultElement.style.top = '10px';
    resultElement.style.right = '10px';
    resultElement.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
    resultElement.style.padding = '10px 15px';
    resultElement.style.borderRadius = '4px';
    resultElement.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.2)';
    resultElement.textContent = `分类结果: ${classificationResult.value.label || classificationResult.value}`;
    overlay.appendChild(resultElement);
  }
  
  // 绘制检测或分割结果
  annotations.value.forEach((annotation, index) => {
    const annotationElement = document.createElement('div');
    annotationElement.className = `annotation-element ${annotation.type || 'bbox'}`;
    annotationElement.setAttribute('data-index', index);

    // 根据标注类型设置样式和内容
    if (annotation.type === 'bbox' || (!annotation.type && annotation.x !== undefined)) {
      // 边界框样式
      annotationElement.style.position = 'absolute';
      annotationElement.style.border = '2px solid #409EFF';
      annotationElement.style.backgroundColor = 'rgba(64, 158, 255, 0.2)';
      annotationElement.style.pointerEvents = 'auto';
      annotationElement.style.cursor = 'move';
      
      // 处理不同的数据格式
      let x, y, width, height;
      
      // 格式1: x, y, width, height (百分比)
      if (annotation.x !== undefined && annotation.width !== undefined) {
        x = annotation.x;
        y = annotation.y;
        width = annotation.width;
        height = annotation.height;
      }
      // 格式2: bbox数组 [x, y, width, height] (百分比)
      else if (annotation.bbox && Array.isArray(annotation.bbox) && annotation.bbox.length === 4) {
        x = annotation.bbox[0];
        y = annotation.bbox[1];
        width = annotation.bbox[2];
        height = annotation.bbox[3];
      }
      // 格式3: xywh (像素坐标，需要转换为百分比)
      else if (annotation.xywh && Array.isArray(annotation.xywh) && annotation.xywh.length === 4 && props.currentImage) {
        const imgWidth = props.currentImage.width || 1;
        const imgHeight = props.currentImage.height || 1;
        x = (annotation.xywh[0] / imgWidth) * 100;
        y = (annotation.xywh[1] / imgHeight) * 100;
        width = (annotation.xywh[2] / imgWidth) * 100;
        height = (annotation.xywh[3] / imgHeight) * 100;
      }
      // 默认值
      else {
        x = 10;
        y = 10;
        width = 30;
        height = 30;
      }
      
      // 限制边界框在画布内
      const limitedX = Math.min(Math.max(x, 0), 100);
      const limitedY = Math.min(Math.max(y, 0), 100);
      const limitedWidth = Math.min(Math.max(width, 1), 100 - limitedX);
      const limitedHeight = Math.min(Math.max(height, 1), 100 - limitedY);
      
      annotationElement.style.left = `${limitedX}%`;
      annotationElement.style.top = `${limitedY}%`;
      annotationElement.style.width = `${limitedWidth}%`;
      annotationElement.style.height = `${limitedHeight}%`;
      annotationElement.style.transform = 'translate(-50%, -50%)';
      
      // 添加标签和置信度
      const labelElement = document.createElement('div');
      labelElement.className = 'annotation-label';
      labelElement.style.position = 'absolute';
      labelElement.style.top = '-20px';
      labelElement.style.left = '50%';
      labelElement.style.transform = 'translateX(-50%)';
      labelElement.style.backgroundColor = '#409EFF';
      labelElement.style.color = '#FFF';
      labelElement.style.padding = '2px 8px';
      labelElement.style.fontSize = '12px';
      labelElement.style.whiteSpace = 'nowrap';
      const confidence = annotation.confidence ? ` (${(annotation.confidence * 100).toFixed(1)}%)` : '';
      labelElement.textContent = (annotation.label || '未命名') + confidence;
      annotationElement.appendChild(labelElement);
    } else if (annotation.type === 'polygon' || annotation.points) {
      // 多边形样式
      annotationElement.style.position = 'absolute';
      annotationElement.style.width = '100%';
      annotationElement.style.height = '100%';
      annotationElement.style.top = '0';
      annotationElement.style.left = '0';
      
      // 获取多边形点
      const points = annotation.points || [];
      
      // 创建多边形路径
      if (points.length >= 3) {
        let path = 'M';
        points.forEach((point, i) => {
          // 确保点是数组格式
          const pointArray = Array.isArray(point) ? point : [0, 0];
          // 限制点在画布范围内
          const limitedX = Math.min(Math.max(pointArray[0], 0), 100);
          const limitedY = Math.min(Math.max(pointArray[1], 0), 100);
          // SVG的points属性不应该包含百分号
          path += `${limitedX} ${limitedY}${i < points.length - 1 ? ' L' : ''}`;
        });
        path += ' Z';
        
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.style.position = 'absolute';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.pointerEvents = 'none';
        
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        
        // 验证和清理path格式 - 确保它是一个有效的字符串
        let safePath = path;
        if (typeof safePath !== 'string') {
          safePath = '';
          console.error('无效的path值类型:', typeof path, '值:', path);
        }
        
        // 检查多边形点格式
        if (safePath && points.length >= 3) {
          // 安全地设置多边形属性
          polygon.setAttribute('points', safePath);
          polygon.setAttribute('fill', 'rgba(103, 194, 58, 0.2)');
          polygon.setAttribute('stroke', '#67C23A');
          polygon.setAttribute('stroke-width', '2');
        } else {
          console.warn('跳过无效的多边形标注，点数量不足或path无效');
        }
        
        svg.appendChild(polygon);
        annotationElement.appendChild(svg);
        
        // 添加标签和置信度
        const labelElement = document.createElement('div');
        labelElement.className = 'annotation-label';
        labelElement.style.position = 'absolute';
        labelElement.style.top = '-20px';
        labelElement.style.left = '50%';
        labelElement.style.transform = 'translateX(-50%)';
        labelElement.style.backgroundColor = '#67C23A';
        labelElement.style.color = '#FFF';
        labelElement.style.padding = '2px 8px';
        labelElement.style.fontSize = '12px';
        labelElement.style.whiteSpace = 'nowrap';
        const confidence = annotation.confidence ? ` (${(annotation.confidence * 100).toFixed(1)}%)` : '';
        labelElement.textContent = (annotation.label || '未命名') + confidence;
        annotationElement.appendChild(labelElement);
      }
    }

    overlay.appendChild(annotationElement);
  });
};

// 清除当前标注
const clearCurrentAnnotations = () => {
  annotations.value = [];
  classificationResult.value = null;
  if (annotationOverlay.value) {
    annotationOverlay.value.innerHTML = '';
  }
  ElMessage.success('已清除当前图片的所有标注');
};

// 保存标注结果到服务器
const saveAnnotations = async () => {
  if (!props.currentImage || !hasAnnotations.value) {
    ElMessage.warning('没有可保存的标注');
    return;
  }

  try {
    // 构建保存标注的请求数据
    const formData = new FormData();
    formData.append('image_id', props.currentImage.id || '0'); // 使用图片ID或默认值
    formData.append('annotations', JSON.stringify(annotations.value));
    formData.append('format', 'json');

    // 调用VisioFirm保存标注API
    const response = await axios.post(`${getApiUrl()}/api/visiofirm/save_annotations`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    if (response.data && response.data.success) {
      ElMessage.success('标注结果保存成功');
    } else {
      const errorMessage = response.data?.detail || '保存标注失败';
      ElMessage.error(errorMessage);
    }
  } catch (error) {
    console.error('保存标注失败:', error);
    ElMessage.error('保存标注失败');
  }
};

// 导出标注结果
const exportAnnotations = () => {
  if ((currentModule.value === 'detection' || currentModule.value === 'segmentation') && !hasAnnotations.value) {
    ElMessage.warning('没有可导出的标注');
    return;
  }

  try {
    // 构建导出数据
    const exportData = {
      image: props.currentImage.name,
      module_type: currentModule.value,
      export_time: new Date().toISOString()
    };

    // 根据模块类型添加不同的标注数据
    if (currentModule.value === 'classification' && classificationResult.value) {
      exportData.classification_result = classificationResult.value;
    } else {
      exportData.annotations = annotations.value;
    }

    // 创建下载链接
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileName = `${props.currentImage.name.replace(/\.[^/.]+$/, '')}_${currentModule.value}_annotations.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileName);
    linkElement.click();

    ElMessage.success('标注结果导出成功');
  } catch (error) {
    console.error('导出标注失败:', error);
    ElMessage.error('导出标注失败');
  }
};

// 添加新类别
const addClass = () => {
  const className = newClassName.value.trim();
  if (!className) return;
  
  if (classes.value.includes(className)) {
    ElMessage.warning('该类别已存在');
    return;
  }

  classes.value.push(className);
  newClassName.value = '';
  ElMessage.success('类别添加成功');
};

// 移除类别
const removeClass = (index) => {
  ElMessageBox.confirm(
    `确定要删除类别 "${classes.value[index]}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    classes.value.splice(index, 1);
    ElMessage.success('类别删除成功');
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
};

// 开始人工标注
const startManualAnnotation = () => {
  if (!props.currentImage || !classes.value.length) {
    ElMessage.warning('请先选择图片并添加类别');
    return;
  }
  isManualAnnotating.value = true;
  ElMessage.info('进入人工标注模式，点击画布开始绘制');
};

// 结束人工标注
const endManualAnnotation = () => {
  isManualAnnotating.value = false;
  currentManualAnnotation.value = null;
  ElMessage.info('已退出人工标注模式');
};

// 初始化人工标注事件监听
onMounted(() => {
  const initCanvasEvents = () => {
    const canvasWrapper = document.querySelector('.visiofirm-canvas-wrapper');
    if (!canvasWrapper) return;
    
    let startX, startY, endX, endY;
    let tempElement = null;
    let points = [];
    let isDrawing = false;
    
    // 鼠标按下事件 - 开始绘制
    canvasWrapper.addEventListener('mousedown', (e) => {
      if (!isManualAnnotating.value || !annotationImage.value) return;
      
      const rect = canvasWrapper.getBoundingClientRect();
      startX = ((e.clientX - rect.left) / rect.width) * 100;
      startY = ((e.clientY - rect.top) / rect.height) * 100;
      
      if (currentDrawingType.value === 'bbox') {
        // 创建临时边界框
        tempElement = document.createElement('div');
        tempElement.style.position = 'absolute';
        tempElement.style.border = '2px dashed #FF6B6B';
        tempElement.style.backgroundColor = 'rgba(255, 107, 107, 0.2)';
        tempElement.style.left = `${startX}%`;
        tempElement.style.top = `${startY}%`;
        tempElement.style.width = '0';
        tempElement.style.height = '0';
        tempElement.style.transform = 'translate(-50%, -50%)';
        tempElement.style.pointerEvents = 'none';
        
        const overlay = annotationOverlay.value;
        if (overlay) {
          overlay.appendChild(tempElement);
        }
      } else if (currentDrawingType.value === 'polygon') {
        if (!isDrawing) {
          isDrawing = true;
          points = [[startX, startY]];
          // 创建多边形预览
          updatePolygonPreview();
          ElMessage.info('开始绘制多边形，点击添加点，双击结束');
        } else {
          points.push([startX, startY]);
          updatePolygonPreview();
        }
      }
      
      isDrawing = true;
    });
    
    // 鼠标移动事件 - 更新绘制
    canvasWrapper.addEventListener('mousemove', (e) => {
      if (!isManualAnnotating.value || !isDrawing || !tempElement) return;
      
      const rect = canvasWrapper.getBoundingClientRect();
      endX = ((e.clientX - rect.left) / rect.width) * 100;
      endY = ((e.clientY - rect.top) / rect.height) * 100;
      
      if (currentDrawingType.value === 'bbox') {
        // 计算边界框的位置和大小
        const width = Math.abs(endX - startX);
        const height = Math.abs(endY - startY);
        const left = Math.min(startX, endX);
        const top = Math.min(startY, endY);
        
        // 限制在画布范围内
        const limitedLeft = Math.min(Math.max(left, 10), 90);
        const limitedTop = Math.min(Math.max(top, 10), 90);
        const limitedWidth = Math.min(width, 100 - limitedLeft * 2);
        const limitedHeight = Math.min(height, 100 - limitedTop * 2);
        
        tempElement.style.left = `${limitedLeft + limitedWidth / 2}%`;
        tempElement.style.top = `${limitedTop + limitedHeight / 2}%`;
        tempElement.style.width = `${limitedWidth}%`;
        tempElement.style.height = `${limitedHeight}%`;
      }
    });
    
    // 鼠标抬起事件 - 结束绘制
    canvasWrapper.addEventListener('mouseup', () => {
      if (!isManualAnnotating.value || !isDrawing || !annotationImage.value) return;
      
      if (currentDrawingType.value === 'bbox' && tempElement) {
        // 计算最终边界框
        const width = Math.abs(endX - startX);
        const height = Math.abs(endY - startY);
        
        // 忽略太小的标注
        if (width < 2 || height < 2) {
          if (tempElement.parentNode) tempElement.parentNode.removeChild(tempElement);
          isDrawing = false;
          tempElement = null;
          return;
        }
        
        const left = Math.min(startX, endX);
        const top = Math.min(startY, endY);
        
        // 限制在画布范围内
        const limitedLeft = Math.min(Math.max(left, 10), 90);
        const limitedTop = Math.min(Math.max(top, 10), 90);
        const limitedWidth = Math.min(width, 100 - limitedLeft * 2);
        const limitedHeight = Math.min(height, 100 - limitedTop * 2);
        
        // 添加到标注列表
        ElMessageBox.prompt(
          '请选择类别',
          '人工标注',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            inputPlaceholder: '选择标注类别',
            inputType: 'select',
            inputOptions: classes.value.map(cls => ({ label: cls, value: cls }))
          }
        ).then(({ value }) => {
          const newAnnotation = {
            id: Date.now().toString(),
            type: 'bbox',
            label: value,
            confidence: 1.0, // 人工标注默认为100%置信度
            x: limitedLeft + limitedWidth / 2,
            y: limitedTop + limitedHeight / 2,
            width: limitedWidth,
            height: limitedHeight
          };
          
          annotations.value.push(newAnnotation);
          drawAnnotations();
          ElMessage.success('人工标注添加成功');
        }).catch(() => {
          ElMessage.info('已取消标注');
        }).finally(() => {
          if (tempElement.parentNode) tempElement.parentNode.removeChild(tempElement);
          isDrawing = false;
          tempElement = null;
        });
      }
    });
    
    // 双击事件 - 结束多边形绘制
    canvasWrapper.addEventListener('dblclick', () => {
      if (!isManualAnnotating.value || !isDrawing || currentDrawingType.value !== 'polygon' || points.length < 3) return;
      
      // 确保多边形闭合
      if (points.length > 0 && points[0][0] !== points[points.length - 1][0] && points[0][1] !== points[points.length - 1][1]) {
        points.push([points[0][0], points[0][1]]);
      }
      
      // 添加到标注列表
      ElMessageBox.prompt(
        '请选择类别',
        '人工标注',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          inputPlaceholder: '选择标注类别',
          inputType: 'select',
          inputOptions: classes.value.map(cls => ({ label: cls, value: cls }))
        }
      ).then(({ value }) => {
        const newAnnotation = {
          id: Date.now().toString(),
          type: 'polygon',
          label: value,
          confidence: 1.0, // 人工标注默认为100%置信度
          points: points
        };
        
        annotations.value.push(newAnnotation);
        drawAnnotations();
        ElMessage.success('人工标注添加成功');
      }).catch(() => {
        ElMessage.info('已取消标注');
      }).finally(() => {
        // 清理预览
        const overlay = annotationOverlay.value;
        if (overlay) {
          const previews = overlay.querySelectorAll('.polygon-preview');
          previews.forEach(preview => preview.parentNode.removeChild(preview));
        }
        isDrawing = false;
        points = [];
      });
    });
    
    // 更新多边形预览
    const updatePolygonPreview = () => {
      const overlay = annotationOverlay.value;
      if (!overlay || points.length < 2) return;
      
      // 移除旧的预览
      const previews = overlay.querySelectorAll('.polygon-preview');
      previews.forEach(preview => preview.parentNode.removeChild(preview));
      
      // 创建新的预览
      const previewElement = document.createElement('div');
      previewElement.className = 'polygon-preview';
      previewElement.style.position = 'absolute';
      previewElement.style.width = '100%';
      previewElement.style.height = '100%';
      previewElement.style.top = '0';
      previewElement.style.left = '0';
      
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.style.position = 'absolute';
      svg.style.width = '100%';
      svg.style.height = '100%';
      svg.style.top = '0';
      svg.style.left = '0';
      svg.style.pointerEvents = 'none';
      
      // 创建多边形路径
      let path = 'M';
      points.forEach((point, i) => {
        // SVG的points属性不应该包含百分号
        path += `${point[0]} ${point[1]}${i < points.length - 1 ? ' L' : ''}`;
      });
      path += ' Z';
      
      const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      polygon.setAttribute('points', path);
      polygon.setAttribute('fill', 'rgba(255, 107, 107, 0.2)');
      polygon.setAttribute('stroke', '#FF6B6B');
      polygon.setAttribute('stroke-width', '2');
      polygon.setAttribute('stroke-dasharray', '5,5');
      
      svg.appendChild(polygon);
      previewElement.appendChild(svg);
      overlay.appendChild(previewElement);
    };
  };
  
  // 等待组件渲染完成后初始化事件
  setTimeout(initCanvasEvents, 1000);
});
</script>

<style scoped>
.visiofirm-annotator {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
  overflow-y: auto;
  box-sizing: border-box;
  min-height: 0;

  /* 全局滚动条样式 */
  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.3);
  }
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 16px;
  color: #666;
}

.annotator-container {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding: 20px;
  box-sizing: border-box;
  min-height: 0;
}

.annotation-toolbar {
  display: flex;
  align-items: center;
  background-color: #fff;
  padding: 15px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.annotation-canvas-container {
  flex: 1;
  display: flex;
  gap: 20px;
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 600px;
  min-height: 0;
}

.no-image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background-color: #f8f8f8;
  border-radius: 4px;
  color: #999;
  font-size: 14px;
}

.image-annotation-area {
  flex: 1;
  display: flex;
  gap: 20px;
  min-height: 500px;
  min-height: 0;
}

.visiofirm-canvas-wrapper {
  flex: 1;
  position: relative;
  background-color: #f8f8f8;
  border-radius: 4px;
  overflow: hidden;
  background-image: 
    linear-gradient(45deg, #f0f0f0 25%, transparent 25%),
    linear-gradient(-45deg, #f0f0f0 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #f0f0f0 75%),
    linear-gradient(-45deg, transparent 75%, #f0f0f0 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}

.annotation-image {
  max-width: 100%;
  max-height: 100%;
  display: block;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.annotation-overlay {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  pointer-events: none;
}

.annotation-element {
  pointer-events: auto;
  cursor: pointer;
}

.annotation-label {
  z-index: 3;
  pointer-events: auto;
  user-select: none;
  white-space: nowrap;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.classification-result {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 10;
}

.classification-box {
  background-color: rgba(255, 255, 255, 0.9);
  padding: 15px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 4px solid #409EFF;
}

.class-name {
  font-size: 18px;
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.confidence {
  font-size: 14px;
  color: #666;
}

.annotation-controls {
  width: 280px;
  background-color: #f8f8f8;
  padding: 20px;
  border-radius: 8px;
  overflow-y: auto;
  max-height: 100%;
}

.annotation-controls h4 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
  font-size: 16px;
  font-weight: 500;
}

.class-list h5 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #666;
  font-size: 14px;
  font-weight: 500;
}

.class-items {
  margin-top: 15px;
}

.class-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  margin-bottom: 8px;
}

.remove-class-btn {
  margin-left: 8px;
}

.annotations-preview {
  margin-top: 20px;
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-height: 300px;
  overflow-y: auto;
}

.annotations-preview h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
  font-size: 16px;
  font-weight: 500;
}

.annotations-preview h5 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #666;
  font-size: 14px;
  font-weight: 500;
}

.annotations-list {
  margin-top: 10px;
}

.annotation-item {
  padding: 10px 15px;
  background-color: #f8f8f8;
  border-radius: 4px;
  margin-bottom: 8px;
}

.annotation-info {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.annotation-type {
  font-size: 12px;
  color: #666;
  margin-right: 10px;
}

.annotation-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  padding: 2px 8px;
  background-color: #e6f7ff;
  border-radius: 4px;
}

.annotation-meta {
  font-size: 12px;
  color: #999;
}

.polygon-preview {
  pointer-events: none;
  z-index: 5;
}
</style>
