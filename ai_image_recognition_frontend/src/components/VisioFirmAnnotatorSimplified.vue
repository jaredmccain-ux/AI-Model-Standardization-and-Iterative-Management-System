<template>
  <div class="visiofirm-annotator">
    <div v-if="!isLoaded" class="loading-state" v-loading="!isLoaded">
      <p>加载VisioFirm标注工具中...</p>
    </div>
    
    <div v-else class="annotator-container">
      <!-- 页面标题和介绍 -->
      <div class="page-header">
        <h2>AI图像标注平台</h2>
        <p>选择图片并使用先进的AI模型进行自动标注</p>
      </div>
      
      <!-- 工具栏 -->
      <div class="annotation-toolbar">
        <!-- 模块切换 -->
        <el-radio-group v-model="currentModule" size="large" class="module-switch">
          <el-radio-button label="classification" class="module-btn">图像分类</el-radio-button>
          <el-radio-button label="detection" class="module-btn">图像检测</el-radio-button>
          <el-radio-button label="segmentation" class="module-btn">图像分割</el-radio-button>
        </el-radio-group>
        
        <!-- 模型选择 -->
        <div class="model-selection" v-if="currentModule">
          <!-- 模型类型选择 -->
          <el-select 
            v-model="selectedModelType" 
            placeholder="选择模型类型" 
            :disabled="isAnnotating || isDownloading"
            style="width: 180px;"
            @change="handleModelTypeChange"
          >
            <el-option 
              v-for="type in modelTypes[currentModule]" 
              :key="type.id" 
              :label="type.name" 
              :value="type.id"
            >
              <div class="model-option">
                <span>{{ type.name }}</span>
              </div>
            </el-option>
          </el-select>
          
          <!-- 具体模型选择 -->
          <el-select 
            v-model="selectedModel" 
            placeholder="选择模型" 
            :loading="isDownloading"
            :disabled="isAnnotating || isDownloading || !selectedModelType"
            style="width: 220px;"
            @change="handleModelChange"
            filterable
          >
            <el-option-group label="推荐模型">
              <el-option 
                v-for="model in recommendedModels" 
                :key="model.id" 
                :label="model.name" 
                :value="model.id"
              >
                <div class="model-option">
                  <span>{{ model.name }}</span>
                  <el-tag size="small" type="success" v-if="model.isLocal">本地</el-tag>
                </div>
              </el-option>
            </el-option-group>
            <el-option-group label="所有模型">
              <el-option 
                v-for="model in filteredModels" 
                :key="model.id" 
                :label="model.name" 
                :value="model.id"
              >
                <div class="model-option">
                  <span>{{ model.name }}</span>
                  <el-tag size="small" type="success" v-if="model.isLocal">本地</el-tag>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
          
          <!-- 下载进度条 -->
          <el-progress 
            v-if="isDownloading && downloadProgress > 0" 
            :percentage="downloadProgress" 
            :status="downloadProgress < 100 ? 'normal' : 'success'"
            :stroke-width="6"
            style="width: 200px; margin-left: 20px;"
          />
        </div>
        
        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button 
            type="primary" 
            size="large"
            @click="startAutoAnnotation" 
            :disabled="!currentImage || isAnnotating || isDownloading || !selectedModel"
            :loading="isAnnotating"
          >
            <el-icon v-if="isAnnotating"><Loading /></el-icon>
            {{ isAnnotating ? 'AI标注中...' : 'AI自动标注' }}
          </el-button>
          
          <el-button 
            type="warning" 
            size="large"
            @click="clearCurrentAnnotations" 
            :disabled="!hasAnnotations || isAnnotating"
          >
            清除当前标注
          </el-button>
        </div>
      </div>
      
      <!-- 主要内容区域 -->
      <div class="main-content-area">
        <!-- 左侧控制面板 -->
        <div class="control-panel">
          <div class="model-info-card">
            <h3>当前模型信息</h3>
            <div v-if="currentModelInfo" class="model-details">
              <p><strong>名称:</strong> {{ currentModelInfo.name }}</p>
              <p><strong>类型:</strong> {{ getModuleDisplayName(currentModule) }}</p>
              <p><strong>描述:</strong> {{ currentModelInfo.description }}</p>
              <p><strong>状态:</strong> <span :class="'status-' + (currentModelInfo.isLocal ? 'local' : 'remote')">
                {{ currentModelInfo.isLocal ? '已下载' : '需要下载' }}
              </span></p>
              <p v-if="currentModelInfo.accuracy"><strong>准确率:</strong> {{ currentModelInfo.accuracy }}</p>
              <p v-if="currentModelInfo.speed"><strong>推理速度:</strong> {{ currentModelInfo.speed }}</p>
            </div>
            <div v-else class="no-model-selected">
              <p>请选择一个模型开始标注</p>
            </div>
          </div>

          <!-- 标注信息详细面板 -->
          <div v-if="hasAnnotations" class="annotation-info-panel">
            <h3>标注详情</h3>
            <div v-if="currentModule === 'classification' && classificationResult" class="classification-details">
              <div class="info-item">
                <span class="label">分类结果:</span>
                <span class="value">{{ classificationResult.label }}</span>
                <el-tag type="success" size="small">{{ (classificationResult.confidence * 100).toFixed(1) }}%</el-tag>
              </div>
            </div>
            <div v-else-if="annotations.length > 0" class="detection-details">
              <div class="info-item">
                <span class="label">总检测数:</span>
                <span class="value">{{ annotations.length }}</span>
              </div>
              <div class="object-list">
                <div v-for="(obj, index) in annotations" :key="index" class="object-item">
                  <div class="object-header">
                    <span class="object-label">{{ obj.label || '未命名' }}</span>
                    <el-tag type="primary" size="mini">{{ (obj.confidence || obj.score || 0.9) * 100 }}%</el-tag>
                  </div>
                  <div v-if="obj.type === 'bbox'" class="bbox-info">
                    <div>位置: ({{ Math.round(obj.x) }}, {{ Math.round(obj.y) }})</div>
                    <div>尺寸: {{ Math.round(obj.width) }}×{{ Math.round(obj.height) }}</div>
                  </div>
                  <div v-else-if="obj.points" class="polygon-info">
                    <div>多边形: {{ obj.points.length }}个点</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧图像显示区域 -->
        <div class="image-display-area">
          <div v-if="!currentImage" class="no-image-placeholder">
            <el-icon size="80"><PictureFilled /></el-icon>
            <h3>请选择一张图片开始标注</h3>
            <p>支持拖拽上传或点击选择文件</p>
          </div>
          <div v-else class="image-container">
            <!-- 图像标题 -->
            <div class="image-header">
              <h3>{{ currentImage.name }}</h3>
              <div class="image-dimensions" v-if="imageDimensions">
                {{ imageDimensions.width }} × {{ imageDimensions.height }}
              </div>
            </div>
            
            <!-- 主要图像显示区域 -->
            <div class="image-viewport">
              <img 
                :src="currentImage.url" 
                :alt="currentImage.name" 
                class="main-image"
                ref="annotationImage"
                @load="onImageLoad"
              />
              <!-- 标注覆盖层 -->
              <div class="annotation-overlay" ref="annotationOverlay"></div>
            </div>
            
            <!-- 图像操作工具栏 -->
            <div class="image-toolbar">
              <el-button-group>
                <el-button size="small" @click="zoomIn" :disabled="zoomLevel >= 3">
                  <el-icon><ZoomIn /></el-icon>
                </el-button>
                <el-button size="small" @click="resetZoom">
                  <span>{{ Math.round(zoomLevel * 100) }}%</span>
                </el-button>
                <el-button size="small" @click="zoomOut" :disabled="zoomLevel <= 0.5">
                  <el-icon><ZoomOut /></el-icon>
                </el-button>
              </el-button-group>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 底部说明 -->
      <div class="page-footer">
        <p>提示: 首次使用模型会自动下载到本地，以便离线使用</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { ElMessage, ElButton, ElRadioGroup, ElRadioButton, ElSelect, ElOption, ElProgress, ElBadge, ElLoading } from 'element-plus';
import { Loading, PictureFilled, ZoomIn, ZoomOut } from '@element-plus/icons-vue';
import { visioFirmAPI } from '../api/visioFirm.js';

// 从父组件接收的props
const props = defineProps({
  currentImage: {
    type: Object,
    default: null
  }
});

// 响应式数据
const isLoaded = ref(true);
const isAnnotating = ref(false);
const isDownloading = ref(false);
const downloadProgress = ref(0);
const currentModule = ref('classification');
const selectedModelType = ref('');
const selectedModel = ref('');
const annotations = ref([]);
const classificationResult = ref(null);
const imageDimensions = ref(null);
const zoomLevel = ref(1);

// DOM引用
const annotationImage = ref(null);
const annotationOverlay = ref(null);

// 模型类型配置
const modelTypes = ref({
  classification: [
    { id: 'general', name: '通用分类' },
    { id: 'scene', name: '场景识别' },
    { id: 'product', name: '商品识别' },
    { id: 'medical', name: '医学影像' },
    { id: 'custom', name: '自定义分类' }
  ],
  detection: [
    { id: 'general', name: '通用检测' },
    { id: 'face', name: '人脸检测' },
    { id: 'person', name: '人体检测' },
    { id: 'vehicle', name: '车辆检测' },
    { id: 'custom', name: '自定义检测' }
  ],
  segmentation: [
    { id: 'general', name: '通用分割' },
    { id: 'medical', name: '医学分割' },
    { id: 'aerial', name: '航拍分割' },
    { id: 'custom', name: '自定义分割' }
  ]
});

// 模型配置
const availableModels = ref({
  classification: {
    general: [
      { id: 'resnet50', name: 'ResNet50', description: '通用图像分类模型', isLocal: true, accuracy: '76.2%', speed: '快速' },
      { id: 'efficientnet', name: 'EfficientNet', description: '高效图像分类模型', isLocal: false, accuracy: '84.5%', speed: '中等' },
      { id: 'vit', name: 'Vision Transformer', description: '基于Transformer的图像分类', isLocal: false, accuracy: '88.6%', speed: '慢速' },
      { id: 'mobilenet', name: 'MobileNet', description: '轻量级移动设备分类模型', isLocal: false, accuracy: '71.3%', speed: '极快' }
    ],
    scene: [
      { id: 'places365', name: 'Places365', description: '场景识别专用模型', isLocal: false, accuracy: '82.1%', speed: '中等' },
      { id: 'scene_resnet', name: 'Scene-ResNet', description: '场景识别优化ResNet', isLocal: false, accuracy: '79.5%', speed: '快速' }
    ],
    product: [
      { id: 'product_classifier', name: '商品分类器', description: '电商商品分类模型', isLocal: false, accuracy: '85.7%', speed: '快速' },
      { id: 'retail_classifier', name: '零售分类器', description: '零售商品分类模型', isLocal: false, accuracy: '83.2%', speed: '中等' }
    ],
    medical: [
      { id: 'medical_classifier', name: '医学分类器', description: '医学影像分类模型', isLocal: false, accuracy: '91.3%', speed: '慢速' },
      { id: 'xray_classifier', name: 'X光片分类器', description: 'X光片专用分类模型', isLocal: false, accuracy: '89.8%', speed: '中等' }
    ],
    custom: [
      { id: 'custom_classifier', name: '自定义分类器', description: '可定制的分类模型', isLocal: false, accuracy: '因训练而异', speed: '中等' }
    ]
  },
  detection: {
    general: [
      { id: 'yolov8n', name: 'YOLOv8-nano', description: '轻量级目标检测模型', isLocal: true, accuracy: '37.3% mAP', speed: '极快' },
      { id: 'yolov8s', name: 'YOLOv8-small', description: '小型目标检测模型', isLocal: false, accuracy: '44.9% mAP', speed: '快速' },
      { id: 'faster-rcnn', name: 'Faster R-CNN', description: '高精度目标检测模型', isLocal: false, accuracy: '42.1% mAP', speed: '慢速' },
      { id: 'yolov8m', name: 'YOLOv8-medium', description: '中型目标检测模型', isLocal: false, accuracy: '50.2% mAP', speed: '中等' },
      { id: 'yolov8l', name: 'YOLOv8-large', description: '大型目标检测模型', isLocal: false, accuracy: '52.9% mAP', speed: '慢速' }
    ],
    face: [
      { id: 'retinaface', name: 'RetinaFace', description: '人脸检测模型', isLocal: false, accuracy: '95.6%', speed: '快速' },
      { id: 'mtcnn', name: 'MTCNN', description: '多任务级联人脸检测', isLocal: false, accuracy: '94.4%', speed: '中等' }
    ],
    person: [
      { id: 'person_detector', name: '人体检测器', description: '专用人体检测模型', isLocal: false, accuracy: '89.7%', speed: '快速' },
      { id: 'pose_detector', name: '姿态检测器', description: '人体姿态检测模型', isLocal: false, accuracy: '87.3%', speed: '中等' }
    ],
    vehicle: [
      { id: 'vehicle_detector', name: '车辆检测器', description: '专用车辆检测模型', isLocal: false, accuracy: '88.5%', speed: '快速' },
      { id: 'license_plate', name: '车牌检测器', description: '车牌检测模型', isLocal: false, accuracy: '92.1%', speed: '中等' }
    ],
    custom: [
      { id: 'custom_detector', name: '自定义检测器', description: '可定制的检测模型', isLocal: false, accuracy: '因训练而异', speed: '中等' }
    ]
  },
  segmentation: {
    general: [
      { id: 'sam', name: 'SAM', description: '分割一切模型', isLocal: true, accuracy: '高', speed: '中等' },
      { id: 'mask-rcnn', name: 'Mask R-CNN', description: '实例分割模型', isLocal: false, accuracy: '中高', speed: '慢速' },
      { id: 'yolov8-seg', name: 'YOLOv8-Seg', description: 'YOLO分割模型', isLocal: false, accuracy: '中高', speed: '快速' },
      { id: 'sam-hq', name: 'SAM-HQ', description: '高质量分割一切模型', isLocal: false, accuracy: '极高', speed: '慢速' }
    ],
    medical: [
      { id: 'medical_segmenter', name: '医学分割器', description: '医学影像分割模型', isLocal: false, accuracy: '91.7%', speed: '慢速' },
      { id: 'unet', name: 'U-Net', description: '医学图像分割模型', isLocal: false, accuracy: '89.5%', speed: '中等' }
    ],
    aerial: [
      { id: 'aerial_segmenter', name: '航拍分割器', description: '航拍图像分割模型', isLocal: false, accuracy: '87.3%', speed: '慢速' },
      { id: 'satellite_segmenter', name: '卫星图像分割器', description: '卫星图像分割模型', isLocal: false, accuracy: '85.9%', speed: '慢速' }
    ],
    custom: [
      { id: 'custom_segmenter', name: '自定义分割器', description: '可定制的分割模型', isLocal: false, accuracy: '因训练而异', speed: '中等' }
    ]
  }
});

// 计算属性
const filteredModels = computed(() => {
  if (!currentModule.value || !selectedModelType.value) return [];
  return availableModels.value[currentModule.value][selectedModelType.value] || [];
});

const currentModelInfo = computed(() => {
  if (!selectedModel.value || !currentModule.value || !selectedModelType.value) return null;
  return filteredModels.value.find(m => m.id === selectedModel.value);
});

// 推荐模型 - 根据当前模块类型和模型类型显示推荐模型
const recommendedModels = computed(() => {
  if (!currentModule.value || !selectedModelType.value) return [];
  
  // 每个模块和类型的推荐模型ID
  const recommendations = {
    classification: {
      general: ['resnet50', 'efficientnet'],
      scene: ['places365'],
      product: ['product_classifier'],
      medical: ['medical_classifier'],
      custom: ['custom_classifier']
    },
    detection: {
      general: ['yolov8n', 'yolov8s'],
      face: ['retinaface'],
      person: ['person_detector'],
      vehicle: ['vehicle_detector'],
      custom: ['custom_detector']
    },
    segmentation: {
      general: ['sam', 'yolov8-seg'],
      medical: ['unet'],
      aerial: ['aerial_segmenter'],
      custom: ['custom_segmenter']
    }
  };
  
  // 根据推荐ID过滤模型列表
  const recommendIds = recommendations[currentModule.value][selectedModelType.value] || [];
  return filteredModels.value.filter(model => recommendIds.includes(model.id));
});

const hasAnnotations = computed(() => {
  return annotations.value.length > 0 || classificationResult.value !== null;
});

// 方法
const getModuleDisplayName = (module) => {
  const names = {
    classification: '图像分类',
    detection: '目标检测',
    segmentation: '图像分割'
  };
  return names[module] || module;
};

const handleModelTypeChange = (type) => {
  selectedModelType.value = type;
  selectedModel.value = '';
  clearCurrentAnnotations();
  
  // 如果有推荐模型，自动选择第一个
  if (recommendedModels.value.length > 0) {
    selectedModel.value = recommendedModels.value[0].id;
  }
};

const handleModelChange = (modelId) => {
  selectedModel.value = modelId;
  clearCurrentAnnotations();
};

const startAutoAnnotation = async () => {
  if (!props.currentImage || !selectedModel.value) return;
  
  isAnnotating.value = true;
  clearCurrentAnnotations();
  
  try {
    // 创建表单数据
    const formData = new FormData();
    // 检查currentImage的结构，如果有file属性则使用file，否则直接使用currentImage
    const imageFile = props.currentImage?.file || props.currentImage;
    if (!imageFile) {
      ElMessage.error('请先选择图片');
      return;
    }
    formData.append('image', imageFile);
    formData.append('module_type', currentModule.value);
    formData.append('model', selectedModel.value);
    formData.append('model_type', selectedModelType.value);
    
    console.log('📤 发送标注请求:', {
      imageFile: imageFile.name || 'unknown',
      module_type: currentModule.value,
      model: selectedModel.value,
      model_type: selectedModelType.value
    });
    
    // 显示正在处理的模型信息
    ElMessage.info(`正在使用 ${currentModelInfo.value?.name || selectedModel.value} 进行标注，请稍候...`);
    
    const response = await visioFirmAPI.autoAnnotate(formData);
    
    if (response.data) {
      if (currentModule.value === 'classification') {
        classificationResult.value = {
          label: response.data.label,
          confidence: response.data.confidence
        };
      } else {
        annotations.value = response.data.annotations || [];
      }
      drawAnnotations();
      ElMessage.success(`使用 ${currentModelInfo.value?.name || selectedModel.value} 标注完成`);
    }
  } catch (error) {
    console.error('标注失败:', error);
    ElMessage.error(`标注失败: ${error.response?.data?.detail || error.message}`);
  } finally {
    isAnnotating.value = false;
  }
};

const onImageLoad = () => {
  if (annotationImage.value) {
    const img = annotationImage.value;
    imageDimensions.value = {
      width: img.naturalWidth,
      height: img.naturalHeight
    };
    updateZoom();
  }
};

const zoomIn = () => {
  if (zoomLevel.value < 3) {
    zoomLevel.value = Math.min(zoomLevel.value + 0.25, 3);
    updateZoom();
  }
};

const zoomOut = () => {
  if (zoomLevel.value > 0.5) {
    zoomLevel.value = Math.max(zoomLevel.value - 0.25, 0.5);
    updateZoom();
  }
};

const resetZoom = () => {
  zoomLevel.value = 1;
  updateZoom();
};

const updateZoom = () => {
  if (annotationImage.value) {
    annotationImage.value.style.transformOrigin = 'top left';
    annotationImage.value.style.transform = `scale(${zoomLevel.value})`;
  }
  drawAnnotations();
};

const clearCurrentAnnotations = () => {
  annotations.value = [];
  classificationResult.value = null;
  
  if (annotationOverlay.value) {
    annotationOverlay.value.innerHTML = '';
  }
};

const drawAnnotations = () => {
  if (!annotationOverlay.value || !props.currentImage) return;
  
  // 清除现有标注
  annotationOverlay.value.innerHTML = '';
  
  if (!hasAnnotations.value) return;
  
  const img = annotationImage.value;
  const overlay = annotationOverlay.value;
  
  if (!img || !overlay) return;
  
  const imgRect = img.getBoundingClientRect();
  const overlayRect = overlay.getBoundingClientRect();
  
  // 设置覆盖层样式
  overlay.style.position = 'absolute';
  overlay.style.top = '0';
  overlay.style.left = '0';
  overlay.style.width = imgRect.width + 'px';
  overlay.style.height = imgRect.height + 'px';
  overlay.style.pointerEvents = 'none';
  
  // 计算缩放比例（已包含zoom）
  const scaleX = imgRect.width / (imageDimensions.value?.width || img.naturalWidth);
  const scaleY = imgRect.height / (imageDimensions.value?.height || img.naturalHeight);
  
  // 绘制分类结果
  if (currentModule.value === 'classification' && classificationResult.value) {
    const labelDiv = document.createElement('div');
    labelDiv.className = 'classification-label';
    labelDiv.textContent = `${classificationResult.value.label} (${(classificationResult.value.confidence * 100).toFixed(1)}%)`;
    labelDiv.style.position = 'absolute';
    labelDiv.style.top = '20px';
    labelDiv.style.left = '20px';
    labelDiv.style.background = 'rgba(0, 0, 0, 0.7)';
    labelDiv.style.color = 'white';
    labelDiv.style.padding = '10px 15px';
    labelDiv.style.borderRadius = '5px';
    labelDiv.style.fontSize = '16px';
    labelDiv.style.fontWeight = 'bold';
    overlay.appendChild(labelDiv);
  }
  
  // 绘制检测和分割结果
  annotations.value.forEach((annotation, index) => {
    if (annotation.type === 'bbox') {
      // 边界框
      const bbox = document.createElement('div');
      bbox.className = 'annotation-bbox';
      
      // 兼容多种坐标输入：{x,y,width,height} 或 bbox: [x,y,w,h]
      // 同时兼容0~1归一化与像素坐标
      const imgW = imageDimensions.value?.width || img.naturalWidth;
      const imgH = imageDimensions.value?.height || img.naturalHeight;
      const arr = Array.isArray(annotation.bbox) && annotation.bbox.length === 4 ? annotation.bbox : null;
      const xRaw = annotation.x ?? (arr ? arr[0] : 0);
      const yRaw = annotation.y ?? (arr ? arr[1] : 0);
      const wRaw = annotation.width ?? (arr ? arr[2] : 0);
      const hRaw = annotation.height ?? (arr ? arr[3] : 0);
      const toPixels = (v, dim) => (v <= 1 ? v * dim : v);
      
      // 注意：scaleX/scaleY已经包含zoom，不再重复乘以zoomLevel
      const x = toPixels(xRaw, imgW) * scaleX;
      const y = toPixels(yRaw, imgH) * scaleY;
      const width = toPixels(wRaw, imgW) * scaleX;
      const height = toPixels(hRaw, imgH) * scaleY;
      
      bbox.style.position = 'absolute';
      bbox.style.left = x + 'px';
      bbox.style.top = y + 'px';
      bbox.style.width = width + 'px';
      bbox.style.height = height + 'px';
      // 青色描边、透明填充
      bbox.style.border = '2px solid #00E5FF';
      bbox.style.backgroundColor = 'transparent';
      
      // 添加标签（左上角）
      const label = document.createElement('div');
      label.className = 'annotation-label';
      const conf = (annotation.confidence ?? annotation.score ?? 0.9);
      label.textContent = `${annotation.label || 'Object'} (${(conf * 100).toFixed(1)}%)`;
      label.style.position = 'absolute';
      label.style.top = '-18px';
      label.style.left = '0';
      label.style.background = 'rgba(0, 229, 255, 0.85)';
      label.style.color = '#00333d';
      label.style.padding = '1px 6px';
      label.style.fontSize = '12px';
      label.style.borderRadius = '2px';
      label.style.whiteSpace = 'nowrap';
      
      bbox.appendChild(label);
      overlay.appendChild(bbox);
      
    } else if (annotation.points && annotation.points.length > 0) {
      // 多边形
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.style.position = 'absolute';
      svg.style.top = '0';
      svg.style.left = '0';
      svg.style.width = '100%';
      svg.style.height = '100%';
      svg.style.pointerEvents = 'none';
      
      const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      const points = annotation.points.map(point => {
        const px = point[0] * scaleX; // 已包含zoom
        const py = point[1] * scaleY;
        return `${px},${py}`;
      }).join(' ');
      
      polygon.setAttribute('points', points);
      polygon.setAttribute('fill', 'rgba(52, 152, 219, 0.3)');
      polygon.setAttribute('stroke', '#3498db');
      polygon.setAttribute('stroke-width', '2');
      
      svg.appendChild(polygon);
      overlay.appendChild(svg);
      
      // 添加标签
      if (annotation.points.length > 0) {
        const firstPoint = annotation.points[0];
        const label = document.createElement('div');
        label.className = 'annotation-label';
        label.textContent = `${annotation.label || 'Object'} ${Math.round((annotation.confidence || 0.9) * 100)}%`;
        label.style.position = 'absolute';
        label.style.left = (firstPoint[0] * scaleX) + 'px';
        label.style.top = (firstPoint[1] * scaleY - 25) + 'px';
        label.style.background = '#3498db';
        label.style.color = 'white';
        label.style.padding = '2px 6px';
        label.style.fontSize = '12px';
        label.style.borderRadius = '3px';
        label.style.whiteSpace = 'nowrap';
        
        overlay.appendChild(label);
      }
    }
  });
};

// 监听props变化
watch(() => props.currentImage, () => {
  clearCurrentAnnotations();
});

// 监听模块变化
watch(() => currentModule.value, () => {
  selectedModelType.value = '';
  selectedModel.value = '';
  clearCurrentAnnotations();
  
  // 设置默认模型类型
  if (modelTypes.value[currentModule.value]?.length > 0) {
    selectedModelType.value = modelTypes.value[currentModule.value][0].id;
  }
});

// 生命周期
onMounted(() => {
  // 设置默认模块和模型类型
  if (modelTypes.value.classification.length > 0) {
    selectedModelType.value = modelTypes.value.classification[0].id;
  }
});
</script>

<style scoped>
.model-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.visiofirm-annotator {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  box-sizing: border-box;
}

.annotator-container {
  max-width: 1400px;
  margin: 0 auto;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.page-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  text-align: center;
}

.page-header h2 {
  margin: 0 0 10px 0;
  font-size: 28px;
  font-weight: 600;
}

.page-header p {
  margin: 0;
  font-size: 16px;
  opacity: 0.9;
}

.annotation-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 30px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  flex-wrap: wrap;
  gap: 15px;
}

.module-switch {
  display: flex;
  gap: 10px;
}

.module-btn {
  font-size: 14px;
  font-weight: 500;
}

.model-selection {
  display: flex;
  align-items: center;
  gap: 15px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.main-content-area {
  display: flex;
  min-height: 600px;
  gap: 0;
}

.control-panel {
  width: 320px;
  background: #f8f9fa;
  border-right: 1px solid #e9ecef;
  padding: 20px;
  overflow-y: auto;
}

.model-info-card,
.annotation-info-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.model-info-card h3,
.annotation-info-panel h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.model-details p {
  margin: 8px 0;
  font-size: 14px;
}

.status-local {
  color: #27ae60;
  font-weight: 600;
}

.status-remote {
  color: #e74c3c;
  font-weight: 600;
}

.object-list {
  max-height: 400px;
  overflow-y: auto;
}

.object-item {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}

.object-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.object-label {
  font-weight: 600;
  color: #2c3e50;
}

.bbox-info,
.polygon-info {
  font-size: 13px;
  color: #7f8c8d;
  line-height: 1.4;
}

.image-display-area {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.no-image-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #95a5a6;
}

.no-image-placeholder h3 {
  margin: 20px 0 10px 0;
  font-size: 20px;
  color: #7f8c8d;
}

.image-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.image-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e9ecef;
}

.image-header h3 {
  margin: 0;
  font-size: 18px;
  color: #2c3e50;
}

.image-dimensions {
  font-size: 14px;
  color: #7f8c8d;
}

.image-viewport {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
  min-height: 400px;
}

.main-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 4px;
  transition: transform 0.3s ease;
}

.annotation-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.image-toolbar {
  display: flex;
  justify-content: center;
  margin-top: 15px;
}

.page-footer {
  background: #f8f9fa;
  padding: 15px 30px;
  text-align: center;
  color: #7f8c8d;
  font-size: 14px;
  border-top: 1px solid #e9ecef;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .main-content-area {
    flex-direction: column;
  }
  
  .control-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e9ecef;
  }
  
  .image-display-area {
    padding: 20px;
  }
  
  .main-image {
    max-height: 50vh;
  }
}

@media (max-width: 768px) {
  .annotation-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .model-selection {
    flex-direction: column;
    align-items: stretch;
  }
  
  .action-buttons {
    justify-content: center;
  }
  
  .control-panel {
    padding: 15px;
  }
  
  .image-display-area {
    padding: 15px;
  }
  
  .page-header {
    padding: 20px;
  }
  
  .page-header h2 {
    font-size: 24px;
  }
}

@media (max-width: 480px) {
  .visiofirm-annotator {
    padding: 10px;
  }
  
  .annotator-container {
    border-radius: 8px;
  }
  
  .main-image {
    max-height: 40vh;
  }
}

/* 加载状态 */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-size: 18px;
  color: white;
}

/* 动画效果 */
.classification-label,
.annotation-bbox,
.annotation-label {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>