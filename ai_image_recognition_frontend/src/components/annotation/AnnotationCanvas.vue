<template>
  <div class="annotation-canvas-container">
    <div class="image-wrapper" style="position: relative;">
      <img 
        :src="imageUrl" 
        :alt="imageName" 
        class="display-image"
        @load="onImageLoad"
        ref="displayImage"
        id="displayImage"
        style="display: block; max-width: 100%;"
      />
      <canvas 
        class="annotation-canvas"
        ref="annotationCanvas"
        id="annotationCanvas"
        @mousedown="handleCanvasMouseDown"
        @mousemove="handleCanvasMouseMove"
        @mouseup="handleCanvasMouseUp"
        @mouseleave="handleCanvasMouseLeave"
        @mouseenter="handleCanvasMouseEnter"
        @contextmenu.prevent
        @contextmenu="handleContextMenu"
      ></canvas>
      
      <!-- 标注提示信息 -->
      <div class="annotation-hint" v-if="imageLoaded">
        <template v-if="selectedTool === 'object_detection'">
          目标检测: 左键拖拽绘制边界框，点击边界框拖拽移动，拖动四角调整大小，右键删除标注
        </template>
        <template v-else-if="selectedTool === 'object_detection_obb'">
          旋转框(OBB): 左键拖拽绘制框，点击边界框拖拽移动，拖动四角调整大小，拖动顶部旋转控制点旋转，右键删除标注
        </template>
        <template v-else-if="selectedTool === 'image_segmentation'">
          图像分割: 左键点击添加多边形顶点，点击第一个顶点闭合，右键删除标注
        </template>
      </div>
      
      <!-- 标签编辑弹出框 -->
      <div 
        v-if="isEditingLabel"
        class="label-editor"
        :style="{ left: labelPosition.x + 'px', top: labelPosition.y + 'px' }"
      >
        <el-select 
          v-model="editingLabel"
          placeholder="选择类别"
          filterable
          allow-create
          default-first-option
          @change="() => {
            // 确定要更新的标注索引
            let indexToUpdate = -1;
            if (activeBoxIndex.value >= 0) {
              indexToUpdate = activeBoxIndex.value;
            } else if (activePolygonIndex.value >= 0) {
              indexToUpdate = activePolygonIndex.value;
            }
            
            // 只有当有有效索引且标签不为空时才更新
            if (indexToUpdate >= 0 && editingLabel.value && editingLabel.value.trim()) {
              updateAnnotationLabel(indexToUpdate, editingLabel.value.trim());
            }
          }"
          @blur="() => {
            // 如果用户点击了选择器外部，并且标签有值，先更新再关闭
            let indexToUpdate = -1;
            if (activeBoxIndex.value >= 0) {
              indexToUpdate = activeBoxIndex.value;
            } else if (activePolygonIndex.value >= 0) {
              indexToUpdate = activePolygonIndex.value;
            }
            
            if (indexToUpdate >= 0 && editingLabel.value && editingLabel.value.trim()) {
              updateAnnotationLabel(indexToUpdate, editingLabel.value.trim());
            }
            isEditingLabel.value = false;
          }"
        >
          <el-option 
            v-for="category in annotationCategories" 
            :key="category" 
            :label="category" 
            :value="category"
          ></el-option>
        </el-select>
      </div>
    </div>
    
    <!-- 标签输入弹窗 -->
    <el-dialog
      v-model="isLabelDialogVisible"
      title="输入标签"
      width="30%"
      :close-on-click-modal="false"
    >
      <el-form :model="labelForm" label-width="80px">
        <el-form-item label="标签名称">
          <el-input v-model="labelForm.label" placeholder="请输入标签名称" @keyup.enter="submitLabel"></el-input>
        </el-form-item>
        <el-form-item label="快速选择">
          <div class="quick-select-container">
            <el-tag
              v-for="category in annotationCategories"
              :key="category"
              :closable="false"
              @click="selectQuickLabel(category)"
              class="quick-select-tag"
            >
              {{ category }}
            </el-tag>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelLabel">取消</el-button>
        <el-button type="primary" @click="submitLabel">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 右键菜单 -->
    <div 
      v-if="isContextMenuVisible" 
      class="context-menu"
      :style="{ left: contextMenuPosition.x + 'px', top: contextMenuPosition.y + 'px' }"
    >
      <div class="context-menu-item" @click="editSelectedAnnotation">
        编辑标签
      </div>
      <div class="context-menu-item" @click="deleteSelectedAnnotation">
        删除标注
      </div>
    </div>
  </div>
</template>

<style scoped>
.context-menu {
  position: fixed;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 10000;
  min-width: 100px;
}

.context-menu-item {
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.context-menu-item:hover {
  background-color: #f5f7fa;
  color: #409eff;
}
</style>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { ElMessage, ElSelect, ElOption } from 'element-plus';
import { saveSingleAnnotation } from '@/api/annotation.js';

const props = defineProps({
  imageUrl: {
    type: String,
    required: true
  },
  imageName: {
    type: String,
    default: ''
  },
  annotations: {
    type: Array,
    default: () => []
  },
  selectedTool: {
    type: String,
    default: 'object_detection'
  }
});

const emit = defineEmits(['update:annotations', 'polygon-completed']);

// 引用和状态
const displayImage = ref(null);
const annotationCanvas = ref(null);
const imageLoaded = ref(false);
let retryCount = 0;

// 人工标注相关状态
const isDrawingPolygon = ref(false);
const currentPolygonPoints = ref([]);
const tempPoint = ref(null);
const activePolygonIndex = ref(-1);
const isDrawingBox = ref(false);
const currentBox = ref(null);
const activeBoxIndex = ref(-1);
const editingLabel = ref('');
const isEditingLabel = ref(false);
const labelPosition = ref({ x: 0, y: 0 });

// 标注框拖拽和调整大小相关状态
const isDraggingBox = ref(false);
const isResizingBox = ref(false);
const isRotatingBox = ref(false); // 新增：跟踪是否正在旋转
const resizeHandle = ref(''); // 记录当前调整的控制点位置: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
const dragStartPos = ref({ x: 0, y: 0 });
const boxStartPos = ref({ x: 0, y: 0, width: 0, height: 0, angle: 0 }); // 新增：记录起始角度

// 右键菜单相关状态
const isContextMenuVisible = ref(false);
const contextMenuPosition = ref({ x: 0, y: 0 });
const selectedAnnotationIndex = ref(-1);
const selectedAnnotationType = ref('');

// 标签弹窗相关状态
const isLabelDialogVisible = ref(false);
const labelForm = ref({ label: '' });
const pendingAnnotationIndex = ref(-1);
const pendingAnnotationType = ref('');

// 快速选择标签
const selectQuickLabel = (label) => {
  labelForm.value.label = label;
  submitLabel();
};

// 提交标签
const submitLabel = () => {
  if (!labelForm.value.label.trim()) {
    ElMessage.warning('请输入标签名称');
    return;
  }
  
  const label = labelForm.value.label.trim();
  
  // 判断是新增标注还是编辑已有标注
  if (pendingAnnotationIndex.value >= 0) {
    // 编辑已有标注
    updateAnnotationLabel(pendingAnnotationIndex.value, label);
    
    // 更新本地状态
    const updatedAnnotations = [...props.annotations];
    updatedAnnotations[pendingAnnotationIndex.value].label = label;
    emit('update:annotations', updatedAnnotations);
    
    // 重新绘制标注
    drawAnnotations();
    
    ElMessage.success('标签更新成功');
  }
    // 新增标注的逻辑已在completePolygon和completeBoundingBox中处理，此处不需要重复处理
  
  // 重置状态
  isLabelDialogVisible.value = false;
  labelForm.value.label = '';
  pendingAnnotationIndex.value = -1;
  pendingAnnotationType.value = '';
};

// 取消标签输入
const cancelLabel = () => {
  // 对于编辑模式，取消时不需要删除标注
  // 对于新建模式，创建标注的逻辑已在completePolygon和completeBoundingBox中处理
  // 编辑已有标注时，不需要删除，只关闭弹窗即可
  
  // 重置状态
  isLabelDialogVisible.value = false;
  labelForm.value.label = '';
  pendingAnnotationIndex.value = -1;
  pendingAnnotationType.value = '';
};

// 处理右键菜单
const handleContextMenu = (event) => {
  event.preventDefault();
  
  const canvas = annotationCanvas.value;
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / canvas.width) * 100;
  const y = ((event.clientY - rect.top) / canvas.height) * 100;
  
  // 检查是否点击了多边形
  const clickedPolygonIndex = checkPolygonVertexClick(x, y);
  if (clickedPolygonIndex >= 0) {
    // 显示右键菜单
    isContextMenuVisible.value = true;
    contextMenuPosition.value = { x: event.clientX, y: event.clientY };
    selectedAnnotationIndex.value = clickedPolygonIndex;
    selectedAnnotationType.value = 'polygon';
    return;
  }
  
  // 检查是否点击了边界框（包括OBB框）
  const boxClickResult = checkBoxClick(x, y);
  if (boxClickResult.index >= 0) {
    // 获取标注类型
    const annotation = props.annotations[boxClickResult.index];
    
    // 显示右键菜单
    isContextMenuVisible.value = true;
    contextMenuPosition.value = { x: event.clientX, y: event.clientY };
    selectedAnnotationIndex.value = boxClickResult.index;
    selectedAnnotationType.value = annotation.type;
    return;
  }
  
  // 如果没有点击到任何标注，不显示右键菜单
  isContextMenuVisible.value = false;
};

// 编辑选中的标注
const editSelectedAnnotation = () => {
  if (selectedAnnotationIndex.value >= 0) {
    // 复用标签输入弹窗，这样更简单可靠
    // 设置待编辑的标注索引和类型
    pendingAnnotationIndex.value = selectedAnnotationIndex.value;
    pendingAnnotationType.value = selectedAnnotationType.value;
    
    // 填充当前标签值到输入框
    labelForm.value.label = props.annotations[selectedAnnotationIndex.value].label || '';
    
    // 打开标签输入弹窗
    isLabelDialogVisible.value = true;
    
    // 关闭右键菜单
    isContextMenuVisible.value = false;
  }
};

// 删除选中的标注
const deleteSelectedAnnotation = () => {
  if (selectedAnnotationIndex.value >= 0) {
    // 删除标注
    const updatedAnnotations = [...props.annotations];
    updatedAnnotations.splice(selectedAnnotationIndex.value, 1);
    emit('update:annotations', updatedAnnotations);
    
    // 根据标注类型显示不同的成功消息
    let annotationTypeName;
    switch (selectedAnnotationType.value) {
      case 'polygon':
        annotationTypeName = '多边形';
        break;
      case 'obb':
        annotationTypeName = '旋转框';
        break;
      case 'bbox':
      case 'bounding_box':
        annotationTypeName = '边界框';
        break;
      default:
        annotationTypeName = '标注';
    }
    ElMessage.success(`已删除${annotationTypeName}标注`);
    
    // 重绘
    drawAnnotations();
    
    // 关闭右键菜单并重置状态
    isContextMenuVisible.value = false;
    selectedAnnotationIndex.value = -1;
    selectedAnnotationType.value = '';
  }
};

// 点击页面其他地方关闭右键菜单
const closeContextMenu = () => {
  isContextMenuVisible.value = false;
  selectedAnnotationIndex.value = -1;
  selectedAnnotationType.value = '';
};

// 组件挂载时添加全局点击事件
onMounted(() => {
  document.addEventListener('click', closeContextMenu);
});

// 组件卸载时移除全局点击事件
onUnmounted(() => {
  document.removeEventListener('click', closeContextMenu);
});

// 标注类别列表
const annotationCategories = ref(['person', 'car', 'dog', 'cat', 'bicycle', 'motorcycle', 'bus', 'truck', 'bird', 'other']);

// 图片加载完成事件
const onImageLoad = async () => {
  await nextTick();
  if (displayImage.value && annotationCanvas.value) {
    const img = displayImage.value;
    const canvas = annotationCanvas.value;
    
    // 设置canvas尺寸与图片显示尺寸一致
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    
    imageLoaded.value = true;
    console.log('图片加载完成，Canvas尺寸设置为:', canvas.width, 'x', canvas.height);
    
    // 重新绘制标注
    try {
      // 重置重试计数器
      retryCount = 0;
      // 延迟一点时间确保DOM完全更新
      setTimeout(() => {
        console.log('开始绘制标注...');
        drawAnnotations();
      }, 200);
    } catch (error) {
      console.error('图片加载后绘制标注出错:', error);
      ElMessage.error('绘制标注时出错: ' + error.message);
    }
  } else {
    console.log('图片或Canvas元素不存在，延迟重试');
    // 延迟重试，给元素一些时间加载
    setTimeout(() => onImageLoad(), 300);
  }
};

// 监听窗口大小变化，重新调整canvas尺寸
const resizeHandler = () => {
  if (displayImage.value && annotationCanvas.value && imageLoaded.value) {
    const img = displayImage.value;
    const canvas = annotationCanvas.value;
    
    // 重新设置canvas尺寸
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    
    // 重新绘制标注
    try {
      drawAnnotations();
    } catch (error) {
      console.error('窗口大小变化时绘制标注出错:', error);
    }
  }
};

// 绘制标注
const drawAnnotations = () => {
  if (!annotationCanvas.value || !displayImage.value) {
    if (retryCount < 5) {
      retryCount++;
      setTimeout(() => drawAnnotations(), 200);
    }
    return;
  }
  
  const canvas = annotationCanvas.value;
  const ctx = canvas.getContext('2d');
  
  // 清除画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 绘制已有的标注
  // 先绘制非分类标注
  props.annotations.forEach((annotation, index) => {
    const isActive = index === activePolygonIndex.value || index === activeBoxIndex.value;
    
    // 确保正确处理并绘制不同类型的标注
    if (annotation.type === 'bbox' || annotation.type === 'bounding_box' || annotation.type === 'obb') {
      // 所有边界框类型都使用OBB绘制函数，确保支持旋转
      drawOBB(ctx, annotation, isActive);
    } else if (annotation.type === 'polygon') {
      drawPolygon(ctx, annotation, isActive);
    }
  });
  
  // 单独处理分类标注，避免重叠
  const classificationAnnotations = props.annotations.filter(ann => ann.type === 'classification');
  classificationAnnotations.forEach((annotation, index) => {
    drawClassification(ctx, annotation, index);
  });
  
  // 绘制正在创建的多边形
  if (isDrawingPolygon.value && currentPolygonPoints.value.length > 0) {
    drawCurrentPolygon(ctx);
  }
  
  // 绘制正在创建的边界框
  if (isDrawingBox.value && currentBox.value) {
    drawCurrentBox(ctx);
  }
};

// 绘制边界框
const drawBoundingBox = (ctx, annotation, isActive) => {
  const { bbox, label, confidence } = annotation;
  
  // 计算实际像素坐标
  const x = (bbox.x / 100) * ctx.canvas.width;
  const y = (bbox.y / 100) * ctx.canvas.height;
  const width = (bbox.width / 100) * ctx.canvas.width;
  const height = (bbox.height / 100) * ctx.canvas.height;
  
  // 设置样式
  ctx.lineWidth = isActive ? 3 : 2;
  ctx.strokeStyle = isActive ? '#ff0000' : '#00ff00';
  
  // 绘制矩形
  ctx.beginPath();
  ctx.rect(x, y, width, height);
  ctx.stroke();
  
  // 如果是人工标注，添加半透明填充
  if (!confidence || confidence === 1.0) {
    ctx.fillStyle = isActive ? 'rgba(255, 0, 0, 0.2)' : 'rgba(0, 255, 0, 0.2)';
    ctx.fillRect(x, y, width, height);
  }
  
  // 如果是活动状态，绘制调整大小的控制点
  if (isActive) {
    const handleSize = 6;
    
    // 绘制四个角的控制点
    const handles = [
      { x: x, y: y, type: 'top-left' },
      { x: x + width, y: y, type: 'top-right' },
      { x: x, y: y + height, type: 'bottom-left' },
      { x: x + width, y: y + height, type: 'bottom-right' }
    ];
    
    handles.forEach(handle => {
      ctx.beginPath();
      ctx.arc(handle.x, handle.y, handleSize, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }
  
  // 绘制标签
  const confidenceText = confidence && confidence < 1.0 ? ` (${(confidence * 100).toFixed(0)}%)` : '';
  const text = `${label || '未分类'}${confidenceText}`;
  
  ctx.font = '14px Arial';
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.fillRect(x, y - 20, ctx.measureText(text).width + 10, 20);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(text, x + 5, y - 5);
};

// 绘制正在创建的边界框或旋转框预览
const drawCurrentBox = (ctx) => {
  if (!currentBox.value) return;
  
  // 计算边界框参数
  const startX = Math.min(currentBox.value.startX, currentBox.value.endX);
  const startY = Math.min(currentBox.value.startY, currentBox.value.endY);
  const width = Math.abs(currentBox.value.endX - currentBox.value.startX);
  const height = Math.abs(currentBox.value.endY - currentBox.value.startY);
  
  // 转换为像素坐标
  const x = (startX / 100) * ctx.canvas.width;
  const y = (startY / 100) * ctx.canvas.height;
  const pixelWidth = (width / 100) * ctx.canvas.width;
  const pixelHeight = (height / 100) * ctx.canvas.height;
  
  // 设置样式
  ctx.lineWidth = 2;
  
  // 根据工具类型设置不同的样式
  if (props.selectedTool === 'object_detection_obb') {
    // OBB框使用橙色
    ctx.strokeStyle = '#ff6600';
    ctx.fillStyle = 'rgba(255, 102, 0, 0.2)';
    
    // 保存当前状态
    ctx.save();
    
    // 移动到矩形中心
    ctx.translate(x + pixelWidth / 2, y + pixelHeight / 2);
    
    // 绘制矩形
    ctx.beginPath();
    ctx.rect(-pixelWidth / 2, -pixelHeight / 2, pixelWidth, pixelHeight);
    ctx.fill();
    ctx.stroke();
    
    // 绘制四个角的控制点
    const handleSize = 6;
    const handles = [
      { x: -pixelWidth / 2, y: -pixelHeight / 2 },
      { x: pixelWidth / 2, y: -pixelHeight / 2 },
      { x: -pixelWidth / 2, y: pixelHeight / 2 },
      { x: pixelWidth / 2, y: pixelHeight / 2 }
    ];
    
    handles.forEach(handle => {
      ctx.beginPath();
      ctx.arc(handle.x, handle.y, handleSize, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
    
    // 添加旋转提示
    const rotationIndicatorRadius = 8;
    const rotationIndicatorDistance = Math.max(pixelWidth, pixelHeight) / 2 + 20;
    
    // 绘制连接线
    ctx.beginPath();
    ctx.moveTo(0, -pixelHeight / 2);
    ctx.lineTo(0, -rotationIndicatorDistance + rotationIndicatorRadius);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.stroke();
    
    // 绘制旋转控制点
    ctx.beginPath();
    ctx.arc(0, -rotationIndicatorDistance, rotationIndicatorRadius, 0, Math.PI * 2);
    ctx.fillStyle = '#ff0000';
    ctx.fill();
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.stroke();
    
    // 添加旋转标记
    ctx.beginPath();
    ctx.moveTo(-rotationIndicatorRadius / 2, -rotationIndicatorDistance);
    ctx.lineTo(rotationIndicatorRadius / 2, -rotationIndicatorDistance);
    ctx.moveTo(0, -rotationIndicatorDistance - rotationIndicatorRadius / 2);
    ctx.lineTo(0, -rotationIndicatorDistance + rotationIndicatorRadius / 2);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // 恢复状态
    ctx.restore();
  } else {
    // 普通矩形框
    ctx.strokeStyle = '#00ff00';
    ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
    
    // 绘制矩形
    ctx.beginPath();
    ctx.rect(x, y, pixelWidth, pixelHeight);
    ctx.fill();
    ctx.stroke();
  }
};

// 绘制多边形
const drawPolygon = (ctx, annotation, isActive) => {
  const { points, label, confidence } = annotation;
  
  if (!points || points.length < 3) return;
  
  // 设置样式
  ctx.lineWidth = isActive ? 3 : 2;
  ctx.strokeStyle = isActive ? '#ff0000' : '#0000ff';
  ctx.fillStyle = isActive ? 'rgba(255, 0, 0, 0.2)' : 'rgba(0, 0, 255, 0.2)';
  
  // 绘制多边形
  ctx.beginPath();
  
  // 转换为像素坐标
  const pixelPoints = points.map(point => [
    (point[0] / 100) * ctx.canvas.width,
    (point[1] / 100) * ctx.canvas.height
  ]);
  
  ctx.moveTo(pixelPoints[0][0], pixelPoints[0][1]);
  
  for (let i = 1; i < pixelPoints.length; i++) {
    ctx.lineTo(pixelPoints[i][0], pixelPoints[i][1]);
  }
  
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  
  // 绘制顶点
  pixelPoints.forEach(point => {
    ctx.beginPath();
    ctx.arc(point[0], point[1], 4, 0, Math.PI * 2);
    ctx.fillStyle = isActive ? '#ff0000' : '#0000ff';
    ctx.fill();
  });
  
  // 绘制标签
  if (label) {
    const confidenceText = confidence ? ` (${(confidence * 100).toFixed(0)}%)` : '';
    const text = `${label}${confidenceText}`;
    const firstPoint = pixelPoints[0];
    
    ctx.font = '14px Arial';
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(firstPoint[0], firstPoint[1] - 20, ctx.measureText(text).width + 10, 20);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(text, firstPoint[0] + 5, firstPoint[1] - 5);
  }
};

// 绘制旋转边界框(OBB)
const drawOBB = (ctx, annotation, isActive) => {
  const { bbox, label, confidence } = annotation;
  
  // 计算实际像素坐标
  const x = (bbox.x / 100) * ctx.canvas.width;
  const y = (bbox.y / 100) * ctx.canvas.height;
  const width = (bbox.width / 100) * ctx.canvas.width;
  const height = (bbox.height / 100) * ctx.canvas.height;
  const angle = bbox.angle || 0;
  
  // 保存当前状态
  ctx.save();
  
  // 移动到矩形中心并旋转
  ctx.translate(x + width / 2, y + height / 2);
  ctx.rotate(angle);
  
  // 设置样式
  ctx.lineWidth = isActive ? 3 : 2;
  ctx.strokeStyle = isActive ? '#ff0000' : '#ff6600'; // OBB使用橙色以示区分
  
  // 绘制矩形
  ctx.beginPath();
  ctx.rect(-width / 2, -height / 2, width, height);
  ctx.stroke();
  
  // 如果是人工标注，添加半透明填充
  if (!confidence || confidence === 1.0) {
    ctx.fillStyle = isActive ? 'rgba(255, 0, 0, 0.2)' : 'rgba(255, 102, 0, 0.2)';
    ctx.fill();
  }
  
  // 如果是活动状态，绘制调整大小的控制点
  if (isActive) {
    const handleSize = 6;
    
    // 绘制四个角的控制点
    const handles = [
      { x: -width / 2, y: -height / 2, type: 'top-left' },
      { x: width / 2, y: -height / 2, type: 'top-right' },
      { x: -width / 2, y: height / 2, type: 'bottom-left' },
      { x: width / 2, y: height / 2, type: 'bottom-right' }
    ];
    
    handles.forEach(handle => {
      ctx.beginPath();
      ctx.arc(handle.x, handle.y, handleSize, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
    
    // 绘制旋转控制点（类似于Word的图片旋转控制点）
    const rotationHandleRadius = 15;
    const rotationHandleDistance = Math.max(width, height) / 2 + 20;
    
    // 绘制连接线段
    ctx.beginPath();
    ctx.moveTo(0, -height / 2);
    ctx.lineTo(0, -rotationHandleDistance + rotationHandleRadius);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.stroke();
    
    // 绘制旋转控制点
    ctx.beginPath();
    ctx.arc(0, -rotationHandleDistance, rotationHandleRadius, 0, Math.PI * 2);
    ctx.fillStyle = '#ff0000'; // 使用红色，更醒目
    ctx.fill();
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.stroke();
    
    // 添加旋转标记（类似于Word中的旋转箭头）
    ctx.beginPath();
    ctx.moveTo(-rotationHandleRadius / 2, -rotationHandleDistance);
    ctx.lineTo(rotationHandleRadius / 2, -rotationHandleDistance);
    ctx.moveTo(0, -rotationHandleDistance - rotationHandleRadius / 2);
    ctx.lineTo(0, -rotationHandleDistance + rotationHandleRadius / 2);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  
  // 绘制标签（在旋转后的坐标系内，确保与框同步旋转）
  const confidenceText = confidence && confidence < 1.0 ? ` (${(confidence * 100).toFixed(0)}%)` : '';
  const text = `${label || '未分类'}${confidenceText}`;
  
  ctx.font = '14px Arial';
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  
  // 计算标签尺寸
  const textWidth = ctx.measureText(text).width + 10;
  const textHeight = 20;
  
  // 在旋转后的坐标系中绘制标签，位置在框的上方
  ctx.fillRect(-textWidth / 2, -height / 2 - textHeight, textWidth, textHeight);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(text, -textWidth / 2 + 5, -height / 2 - 5);
  
  // 恢复状态
  ctx.restore();
};

// 绘制分类标注
const drawClassification = (ctx, annotation, index = 0) => {
  const { label, confidence } = annotation;
  
  // 绘制标签
  const confidenceText = confidence ? ` (${(confidence * 100).toFixed(0)}%)` : '';
  const text = `分类: ${label}${confidenceText}`;
  
  // 计算垂直位置，避免重叠
  const yPosition = 10 + (index * 30); // 每个标签占30px高度
  
  ctx.font = 'bold 16px Arial';
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.fillRect(10, yPosition, ctx.measureText(text).width + 10, 25);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(text, 15, yPosition + 18);
};

// 绘制当前正在创建的多边形
const drawCurrentPolygon = (ctx) => {
  if (currentPolygonPoints.value.length === 0) return;
  
  // 设置样式
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#ff6600';
  ctx.fillStyle = 'rgba(255, 102, 0, 0.2)';
  
  // 转换为像素坐标
  const pixelPoints = currentPolygonPoints.value.map(point => [
    (point[0] / 100) * ctx.canvas.width,
    (point[1] / 100) * ctx.canvas.height
  ]);
  
  // 绘制已有的线段
  ctx.beginPath();
  ctx.moveTo(pixelPoints[0][0], pixelPoints[0][1]);
  
  for (let i = 1; i < pixelPoints.length; i++) {
    ctx.lineTo(pixelPoints[i][0], pixelPoints[i][1]);
  }
  
  // 如果有临时点，连接到临时点
  if (tempPoint.value) {
    const tempPixel = [
      (tempPoint.value[0] / 100) * ctx.canvas.width,
      (tempPoint.value[1] / 100) * ctx.canvas.height
    ];
    ctx.lineTo(tempPixel[0], tempPixel[1]);
  }
  
  // 如果有3个以上的点，闭合多边形
  if (pixelPoints.length > 2) {
    ctx.closePath();
    ctx.fill();
  }
  
  ctx.stroke();
  
  // 绘制顶点
  pixelPoints.forEach(point => {
    ctx.beginPath();
    ctx.arc(point[0], point[1], 4, 0, Math.PI * 2);
    ctx.fillStyle = '#ff6600';
    ctx.fill();
  });
  
  // 绘制第一个点特殊标记（用于闭合多边形）
  if (pixelPoints.length > 2) {
    ctx.beginPath();
    ctx.arc(pixelPoints[0][0], pixelPoints[0][1], 6, 0, Math.PI * 2);
    ctx.strokeStyle = '#ff0000';
    ctx.stroke();
  }
};

// 检查是否点击了多边形顶点
const checkPolygonVertexClick = (x, y) => {
  for (let i = 0; i < props.annotations.length; i++) {
    const annotation = props.annotations[i];
    
    if (annotation.type === 'polygon' && annotation.points) {
      for (const point of annotation.points) {
        const distance = Math.sqrt(Math.pow(x - point[0], 2) + Math.pow(y - point[1], 2));
        if (distance < 3) {
          return i;
        }
      }
    }
  }
  
  return -1;
};

// 检查是否点击了边界框、OBB框或旋转控制点
const checkBoxClick = (x, y) => {
  for (let i = 0; i < props.annotations.length; i++) {
    const annotation = props.annotations[i];
    if ((annotation.type === 'bbox' || annotation.type === 'bounding_box' || annotation.type === 'obb') && annotation.bbox) {
      const { x: boxX, y: boxY, width, height, angle = 0 } = annotation.bbox;
      const canvas = annotationCanvas.value;
      
      // 转换为像素坐标
      const pixelBoxX = (boxX / 100) * canvas.width;
      const pixelBoxY = (boxY / 100) * canvas.height;
      const pixelWidth = (width / 100) * canvas.width;
      const pixelHeight = (height / 100) * canvas.height;
      const pixelX = (x / 100) * canvas.width;
      const pixelY = (y / 100) * canvas.height;
      
      // 计算边界框中心
      const centerX = pixelBoxX + pixelWidth / 2;
      const centerY = pixelBoxY + pixelHeight / 2;
      
      // 检查是否点击了旋转控制点（对所有类型的边界框都支持）
      // 计算旋转控制点的位置（与drawOBB函数的绘制位置完全一致）
      const rotationHandleDistance = Math.max(pixelWidth, pixelHeight) / 2 + 20;
      const rotationHandleRadius = 15; // 统一检测半径为15px，与drawOBB函数保持一致
      
      // 计算旋转后控制点的实际位置
      // 注意：在drawOBB中，控制点是先旋转坐标系再绘制的，所以实际坐标需要进行反向转换
      // 控制点在旋转后的坐标系中位于(0, -rotationHandleDistance)
      // 转换到原始坐标系的公式为：
      // x = centerX + Math.sin(angle) * rotationHandleDistance;
      // y = centerY - Math.cos(angle) * rotationHandleDistance;
      const handleX = centerX - Math.sin(angle) * rotationHandleDistance;
      const handleY = centerY - Math.cos(angle) * rotationHandleDistance;
      
      // 检查是否点击了旋转控制点
      const distance = Math.sqrt((pixelX - handleX) ** 2 + (pixelY - handleY) ** 2);
      if (distance <= rotationHandleRadius) {
        return { index: i, isRotationHandle: true };
      }
      
      // 检查是否点击了边界框（考虑旋转，对所有类型的边界框都支持）
      // 将点击点转换到边界框的局部坐标系
      const dx = pixelX - centerX;
      const dy = pixelY - centerY;
      
      // 反向旋转点击点
      const rotatedX = dx * Math.cos(-angle) - dy * Math.sin(-angle);
      const rotatedY = dx * Math.sin(-angle) + dy * Math.cos(-angle);
      
      // 检查是否在边界框内
      if (rotatedX >= -pixelWidth / 2 && rotatedX <= pixelWidth / 2 &&
          rotatedY >= -pixelHeight / 2 && rotatedY <= pixelHeight / 2) {
        return { index: i, isRotationHandle: false };
      }
    }
  }
  return { index: -1, isRotationHandle: false };
};

// 检查是否点击了边界框的调整大小控制点
const checkBoxResizeHandle = (event) => {
  const canvas = annotationCanvas.value;
  const rect = canvas.getBoundingClientRect();
  const pixelX = event.clientX - rect.left;
  const pixelY = event.clientY - rect.top;
  const handleSize = 8; // 控制点检测区域大小
  
  for (let i = 0; i < props.annotations.length; i++) {
    const annotation = props.annotations[i];
    
    if ((annotation.type === 'bbox' || annotation.type === 'bounding_box' || annotation.type === 'obb') && annotation.bbox) {
      const { x, y, width, height, angle = 0 } = annotation.bbox;
      
      // 转换为像素坐标
      const pixelBoxX = (x / 100) * canvas.width;
      const pixelBoxY = (y / 100) * canvas.height;
      const pixelBoxWidth = (width / 100) * canvas.width;
      const pixelBoxHeight = (height / 100) * canvas.height;
      
      // 计算边界框中心
      const centerX = pixelBoxX + pixelBoxWidth / 2;
      const centerY = pixelBoxY + pixelBoxHeight / 2;
      
      // 将点击点转换到边界框的局部坐标系
      const dx = pixelX - centerX;
      const dy = pixelY - centerY;
      
      // 反向旋转点击点
      const rotatedX = dx * Math.cos(-angle) - dy * Math.sin(-angle);
      const rotatedY = dx * Math.sin(-angle) + dy * Math.cos(-angle);
      
      // 检查四个角的控制点（在局部坐标系中）
      const halfWidth = pixelBoxWidth / 2;
      const halfHeight = pixelBoxHeight / 2;
      
      if (Math.abs(rotatedX + halfWidth) <= handleSize && Math.abs(rotatedY + halfHeight) <= handleSize) {
        return { index: i, handle: 'top-left' };
      }
      if (Math.abs(rotatedX - halfWidth) <= handleSize && Math.abs(rotatedY + halfHeight) <= handleSize) {
        return { index: i, handle: 'top-right' };
      }
      if (Math.abs(rotatedX + halfWidth) <= handleSize && Math.abs(rotatedY - halfHeight) <= handleSize) {
        return { index: i, handle: 'bottom-left' };
      }
      if (Math.abs(rotatedX - halfWidth) <= handleSize && Math.abs(rotatedY - halfHeight) <= handleSize) {
        return { index: i, handle: 'bottom-right' };
      }
    }
  }
  
  return null;
};

// 更新鼠标指针样式
const updateCursorStyle = (event) => {
  const canvas = annotationCanvas.value;
  if (!canvas) return;
  
  // 检查是否悬停在调整大小控制点上
  const resizeInfo = checkBoxResizeHandle(event);
  if (resizeInfo) {
    switch (resizeInfo.handle) {
      case 'top-left':
      case 'bottom-right':
        canvas.style.cursor = 'nwse-resize';
        break;
      case 'top-right':
      case 'bottom-left':
        canvas.style.cursor = 'nesw-resize';
        break;
    }
    return;
  }
  
  // 检查是否悬停在旋转控制点上
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / canvas.width) * 100;
  const y = ((event.clientY - rect.top) / canvas.height) * 100;
  const boxClickResult = checkBoxClick(x, y);
  
  if (boxClickResult.index >= 0) {
    if (boxClickResult.isRotationHandle) {
      // 对于旋转控制点，使用旋转光标样式
      canvas.style.cursor = 'grab';
    } else {
      // 对于边界框本体，使用移动光标样式
      canvas.style.cursor = 'move';
    }
    return;
  }
  
  // 恢复默认指针样式
  canvas.style.cursor = 'crosshair';
};

// 保存标注到后端
const saveAnnotationToServer = async (annotation) => {
  try {
    // 确保有标签再保存
    if (!annotation.label || !annotation.label.trim()) {
      console.warn('未设置标签，不保存到服务器');
      ElMessage.warning('请先设置标注标签再保存');
      return;
    }
    
    // 标准化参数格式（避免422错误）
    const annotationData = {
      id: annotation.id || Date.now().toString(), // 确保有ID
      image_name: props.imageName, // 图片名称（必填）
      label: annotation.label || 'unknown', // 标签（必填）
      type: annotation.type || 'obb', // 明确标注类型为obb
      bbox: {
        x: parseFloat(annotation.bbox.x),
        y: parseFloat(annotation.bbox.y),
        width: parseFloat(annotation.bbox.width),
        height: parseFloat(annotation.bbox.height),
        angle: parseFloat(annotation.bbox.angle || 0) // 必传angle，避免422
      },
      confidence: parseFloat(annotation.confidence || 1.0),
      created_at: new Date().toISOString()
    };
    
    // 调用API
    console.log('准备保存标注:', annotationData);
    await saveSingleAnnotation(annotationData);
    ElMessage.success('标注保存成功');
  } catch (error) {
    console.error('保存标注到服务器失败:', error);
    // 仅提示错误，不阻断前端功能（避免因API问题导致标注无法使用）
    ElMessage.warning(`标注本地保存成功，服务器同步失败：${error.message}`);
  }
};

// 完成多边形绘制
const completePolygon = () => {
  if (currentPolygonPoints.value.length < 3) {
    isDrawingPolygon.value = false;
    currentPolygonPoints.value = [];
    return;
  }
  
  // 创建新的多边形标注
  const newPolygon = {
    type: 'polygon',
    label: '', // 初始为空，等待用户输入
    confidence: 1.0,
    points: [...currentPolygonPoints.value]
  };
  
  // 更新标注列表
  const updatedAnnotations = [...props.annotations, newPolygon];
  emit('update:annotations', updatedAnnotations);
  emit('polygon-completed', newPolygon);
  
  // 保存待处理的标注索引和类型
  pendingAnnotationIndex.value = updatedAnnotations.length - 1;
  pendingAnnotationType.value = 'polygon';
  
  // 打开标签输入弹窗
  isLabelDialogVisible.value = true;
  labelForm.value.label = '';
  
  // 重置状态
  isDrawingPolygon.value = false;
  currentPolygonPoints.value = [];
  tempPoint.value = null;
  
  // 重绘
  drawAnnotations();
};

// 完成边界框绘制
const completeBoundingBox = () => {
  if (!currentBox.value) return;
  
  // 计算边界框参数
  const x = Math.min(currentBox.value.startX, currentBox.value.endX);
  const y = Math.min(currentBox.value.startY, currentBox.value.endY);
  const width = Math.abs(currentBox.value.endX - currentBox.value.startX);
  const height = Math.abs(currentBox.value.endY - currentBox.value.startY);
  
  // 确保边界框有一定大小
  if (width < 2 || height < 2) {
    isDrawingBox.value = false;
    currentBox.value = null;
    return;
  }
  
  // 根据当前工具类型创建标注
  let newAnnotation;
  if (props.selectedTool === 'object_detection_obb') {
    // 创建OBB标注，确保正确保存旋转信息
    newAnnotation = {
      type: 'obb',
      label: '', // 初始为空，等待用户输入
      confidence: 1.0,
      bbox: {
        x,
        y,
        width,
        height,
        angle: 0, // 初始角度为0
        center: {
          x: x + width / 2,
          y: y + height / 2
        }
      }
    };
    pendingAnnotationType.value = 'obb';
  } else {
    // 创建普通边界框标注
    // 使用'bounding_box'类型以兼容后端数据格式
    newAnnotation = {
      type: 'bounding_box',
      label: '', // 初始为空，等待用户输入
      confidence: 1.0,
      bbox: {
        x,
        y,
        width,
        height,
        angle: 0 // 初始角度为0，以支持旋转功能
      }
    };
    pendingAnnotationType.value = 'bounding_box';
  }
  
  // 更新标注列表
  const updatedAnnotations = [...props.annotations, newAnnotation];
  emit('update:annotations', updatedAnnotations);
  
  // 保存待处理的标注索引和类型
  pendingAnnotationIndex.value = updatedAnnotations.length - 1;
  
  // 打开标签输入弹窗
  isLabelDialogVisible.value = true;
  labelForm.value.label = '';
  
  // 重置状态
  isDrawingBox.value = false;
  currentBox.value = null;
  
  // 重绘
  drawAnnotations();
};

// 更新标注标签
const updateAnnotationLabel = (annotationIndex, newLabel) => {
  if (annotationIndex >= 0 && annotationIndex < props.annotations.length) {
    const updatedAnnotations = [...props.annotations];
    updatedAnnotations[annotationIndex] = {
      ...updatedAnnotations[annotationIndex],
      label: newLabel
    };
    emit('update:annotations', updatedAnnotations);
    
    // 关闭标签编辑模式
    isEditingLabel.value = false;
    activeBoxIndex.value = -1;
    activePolygonIndex.value = -1;
    editingLabel.value = '';
    
    // 重绘
    drawAnnotations();
    
    // 只有当通过弹窗设置标签时才保存到后端并显示成功消息
    if (pendingAnnotationIndex.value >= 0) {
      // 保存到后端
      saveAnnotationToServer(updatedAnnotations[annotationIndex]);
      ElMessage.success('标注成功添加！');
    } else {
      ElMessage.success('标注标签已更新');
    }
  }
};

// 鼠标事件处理
const handleCanvasMouseDown = (event) => {
  // 重置活动状态
  activePolygonIndex.value = -1;
  activeBoxIndex.value = -1;
  
  const canvas = annotationCanvas.value;
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / canvas.width) * 100;
  const y = ((event.clientY - rect.top) / canvas.height) * 100;
  
  // 右键点击已经在@contextmenu事件中处理，这里不再处理
  if (event.button === 2) { // 右键
    return;
  }
  
  // 处理目标检测工具 - 绘制边界框或旋转框
  if (props.selectedTool === 'object_detection' || props.selectedTool === 'object_detection_obb') {
    // 检查是否点击了调整大小控制点
    const resizeInfo = checkBoxResizeHandle(event);
    if (resizeInfo) {
      // 进入调整大小模式
      isResizingBox.value = true;
      activeBoxIndex.value = resizeInfo.index;
      resizeHandle.value = resizeInfo.handle;
      
      // 记录起始位置
      const annotation = props.annotations[resizeInfo.index];
      dragStartPos.value = { x: event.clientX, y: event.clientY };
      boxStartPos.value = {
        x: annotation.bbox.x,
        y: annotation.bbox.y,
        width: annotation.bbox.width,
        height: annotation.bbox.height
      };
      
      // 阻止默认行为
      event.preventDefault();
      return;
    }
    
    // 检查是否点击了已有边界框
    const boxClickResult = checkBoxClick(x, y);
    
    if (boxClickResult.index >= 0) {
      activeBoxIndex.value = boxClickResult.index;
      const annotation = props.annotations[boxClickResult.index];
      
      if (boxClickResult.isRotationHandle) {
        // 点击了旋转控制点，进入旋转模式
        isRotatingBox.value = true;
        dragStartPos.value = { x: event.clientX, y: event.clientY };
        
        // 【新增】定义angle变量（关键修复）
        const angle = annotation.bbox.angle || 0; // 从标注数据中获取角度，无则默认为0
        
        // 获取图片真实尺寸和canvas尺寸（处理图片缩放）
        const canvas = annotationCanvas.value;
        const img = displayImage.value;
        const imgRealWidth = img ? img.naturalWidth : canvas.width;
        const imgRealHeight = img ? img.naturalHeight : canvas.height;
        const scaleX = canvas.width / imgRealWidth;
        const scaleY = canvas.height / imgRealHeight;
        
        // 计算边界框中心（基于真实尺寸的像素坐标）
        const centerX = (annotation.bbox.x / 100) * imgRealWidth * scaleX;
        const centerY = (annotation.bbox.y / 100) * imgRealHeight * scaleY;
        
        // 计算旋转控制点的位置（与drawOBB函数的绘制位置完全一致）
        const pixelWidth = (annotation.bbox.width / 100) * canvas.width;
        const pixelHeight = (annotation.bbox.height / 100) * canvas.height;
        const rotationHandleDistance = Math.max(pixelWidth, pixelHeight) / 2 + 20;
        
        // 计算旋转后控制点的实际位置
        const handleX = centerX - Math.sin(angle) * rotationHandleDistance;
        const handleY = centerY - Math.cos(angle) * rotationHandleDistance;
        
        // 计算起始鼠标位置相对于旋转控制点的角度
        const startAngle = Math.atan2(
          event.clientY - rect.top - handleY,
          event.clientX - rect.left - handleX
        );
        
        boxStartPos.value = {
          x: annotation.bbox.x,
          y: annotation.bbox.y,
          width: annotation.bbox.width,
          height: annotation.bbox.height,
          angle: annotation.bbox.angle || 0,
          startAngle: startAngle, // 记录起始角度
          handleX: handleX, // 记录旋转控制点的位置
          handleY: handleY
        };
        
        // 添加调试信息
        console.log('旋转模式参数：', {
          centerX,
          centerY,
          startAngle,
          boxStartPos: boxStartPos.value
        });
      } else {
        // 点击了边界框，进入拖拽模式
        isDraggingBox.value = true;
        dragStartPos.value = { x: event.clientX, y: event.clientY };
        boxStartPos.value = {
          x: annotation.bbox.x,
          y: annotation.bbox.y,
          width: annotation.bbox.width,
          height: annotation.bbox.height,
          angle: annotation.bbox.angle || 0
        };
      }
      
      // 阻止默认行为
      event.preventDefault();
    } else {
      // 开始绘制新边界框
      isDrawingBox.value = true;
      currentBox.value = {
        startX: x,
        startY: y,
        endX: x,
        endY: y
      };
    }
    return;
  }
  
  // 处理图像分割工具 - 绘制多边形
  if (props.selectedTool === 'image_segmentation') {
    // 检查是否点击了已有多边形的顶点
    const clickedPolygonIndex = checkPolygonVertexClick(x, y);
    
    if (clickedPolygonIndex >= 0) {
      // 选中已有多边形并进入编辑模式
      activePolygonIndex.value = clickedPolygonIndex;
      isEditingLabel.value = true;
      editingLabel.value = props.annotations[clickedPolygonIndex].label || 'polygon';
      labelPosition.value = {
        x: event.clientX,
        y: event.clientY
      };
      drawAnnotations();
      return;
    }
    
    if (!isDrawingPolygon.value) {
      // 开始新的多边形
      isDrawingPolygon.value = true;
      currentPolygonPoints.value = [[x, y]];
    } else {
      // 检查是否点击了第一个点以闭合多边形
      const firstPoint = currentPolygonPoints.value[0];
      const distance = Math.sqrt(Math.pow(x - firstPoint[0], 2) + Math.pow(y - firstPoint[1], 2));
      
      if (currentPolygonPoints.value.length > 2 && distance < 3) {
        // 闭合多边形并添加标注
        completePolygon();
      } else {
        // 添加新点
        currentPolygonPoints.value.push([x, y]);
      }
    }
  }
  
  drawAnnotations();
};

const handleCanvasMouseMove = (event) => {
  // 更新鼠标指针样式
  updateCursorStyle(event);
  
  // 处理拖拽边界框
  if (isDraggingBox.value && activeBoxIndex.value >= 0) {
    const canvas = annotationCanvas.value;
    const rect = canvas.getBoundingClientRect();
    
    // 计算移动距离
    const deltaX = (event.clientX - dragStartPos.value.x) / canvas.width * 100;
    const deltaY = (event.clientY - dragStartPos.value.y) / canvas.height * 100;
    
    // 更新标注
    const updatedAnnotations = [...props.annotations];
    const annotation = updatedAnnotations[activeBoxIndex.value];
    
    // 确保不超出画布边界
    const newX = Math.max(0, Math.min(100 - boxStartPos.value.width, boxStartPos.value.x + deltaX));
    const newY = Math.max(0, Math.min(100 - boxStartPos.value.height, boxStartPos.value.y + deltaY));
    
    annotation.bbox.x = newX;
    annotation.bbox.y = newY;
    
    // 发送更新
    emit('update:annotations', updatedAnnotations);
    
    // 重绘
    drawAnnotations();
    return;
  }
  
  // 处理旋转边界框
  if (isRotatingBox.value && activeBoxIndex.value >= 0) {
    const canvas = annotationCanvas.value;
    const rect = canvas.getBoundingClientRect();
    
    // 获取当前鼠标位置（相对于画布像素坐标）
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    
    // 获取标注信息
    const updatedAnnotations = [...props.annotations];
    const annotation = updatedAnnotations[activeBoxIndex.value];
    
    // 获取旋转控制点的位置
    const { handleX, handleY } = boxStartPos.value;
    
    // 计算当前鼠标位置相对于旋转控制点的角度
    const currentAngle = Math.atan2(mouseY - handleY, mouseX - handleX);
    
    // 计算角度差（当前角度 - 起始角度）
    const angleDiff = currentAngle - boxStartPos.value.startAngle;
    
    // 计算新角度（起始边界框角度 + 角度差）
    let newAngle = boxStartPos.value.angle + angleDiff;
    
    // 确保角度在0-2π范围内
    while (newAngle < 0) newAngle += 2 * Math.PI;
    while (newAngle >= 2 * Math.PI) newAngle -= 2 * Math.PI;
    
    annotation.bbox.angle = newAngle;
    
    // 发送更新
    emit('update:annotations', updatedAnnotations);
    
    // 重绘
    drawAnnotations();
    return;
  }
  
  // 处理调整边界框大小
  if (isResizingBox.value && activeBoxIndex.value >= 0) {
    const canvas = annotationCanvas.value;
    const rect = canvas.getBoundingClientRect();
    
    // 计算相对起始位置的偏移
    const deltaX = (event.clientX - dragStartPos.value.x) / canvas.width * 100;
    const deltaY = (event.clientY - dragStartPos.value.y) / canvas.height * 100;
    
    // 更新标注
    const updatedAnnotations = [...props.annotations];
    const annotation = updatedAnnotations[activeBoxIndex.value];
    
    // 保存原始角度
    const originalAngle = annotation.bbox.angle || 0;
    
    switch (resizeHandle.value) {
      case 'top-left':
        annotation.bbox.width = Math.max(2, boxStartPos.value.width - deltaX);
        annotation.bbox.height = Math.max(2, boxStartPos.value.height - deltaY);
        annotation.bbox.x = boxStartPos.value.x + deltaX;
        annotation.bbox.y = boxStartPos.value.y + deltaY;
        break;
      case 'top-right':
        annotation.bbox.width = Math.max(2, boxStartPos.value.width + deltaX);
        annotation.bbox.height = Math.max(2, boxStartPos.value.height - deltaY);
        annotation.bbox.y = boxStartPos.value.y + deltaY;
        break;
      case 'bottom-left':
        annotation.bbox.width = Math.max(2, boxStartPos.value.width - deltaX);
        annotation.bbox.height = Math.max(2, boxStartPos.value.height + deltaY);
        annotation.bbox.x = boxStartPos.value.x + deltaX;
        break;
      case 'bottom-right':
        annotation.bbox.width = Math.max(2, boxStartPos.value.width + deltaX);
        annotation.bbox.height = Math.max(2, boxStartPos.value.height + deltaY);
        break;
    }
    
    // 确保调整大小后角度信息不丢失
    annotation.bbox.angle = originalAngle;
    
    // 确保不超出画布边界
    annotation.bbox.x = Math.max(0, annotation.bbox.x);
    annotation.bbox.y = Math.max(0, annotation.bbox.y);
    annotation.bbox.width = Math.min(100 - annotation.bbox.x, annotation.bbox.width);
    annotation.bbox.height = Math.min(100 - annotation.bbox.y, annotation.bbox.height);
    
    // 发送更新
    emit('update:annotations', updatedAnnotations);
    
    // 重绘
    drawAnnotations();
    return;
  }
  
  // 处理正在绘制的边界框
  if (isDrawingBox.value && currentBox.value) {
    const canvas = annotationCanvas.value;
    const rect = canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / canvas.width) * 100;
    const y = ((event.clientY - rect.top) / canvas.height) * 100;
    
    currentBox.value.endX = x;
    currentBox.value.endY = y;
    drawAnnotations();
    return;
  }
  
  // 处理正在绘制的多边形
  if (isDrawingPolygon.value) {
    const canvas = annotationCanvas.value;
    const rect = canvas.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / canvas.width) * 100;
    const y = ((event.clientY - rect.top) / canvas.height) * 100;
    
    tempPoint.value = [x, y];
    drawAnnotations();
  }
};

const handleCanvasMouseUp = () => {
  // 重置拖拽、调整大小和旋转状态
  isDraggingBox.value = false;
  isResizingBox.value = false;
  isRotatingBox.value = false; // 重置旋转状态
  resizeHandle.value = '';
  
  // 完成边界框绘制
  if (isDrawingBox.value) {
    completeBoundingBox();
  }
};

const handleCanvasMouseLeave = () => {
  tempPoint.value = null;
  isDraggingBox.value = false;
  isResizingBox.value = false;
  isRotatingBox.value = false; // 重置旋转状态
  resizeHandle.value = '';
  
  // 恢复默认指针样式
  if (annotationCanvas.value) {
    annotationCanvas.value.style.cursor = 'crosshair';
  }
  
  drawAnnotations();
};

// 处理键盘事件，支持删除选中的标注
const handleKeyDown = (event) => {
  // 删除选中的边界框（包括OBB框）
  if ((event.key === 'Delete' || event.key === 'Backspace') && activeBoxIndex.value >= 0) {
    const updatedAnnotations = [...props.annotations];
    updatedAnnotations.splice(activeBoxIndex.value, 1);
    emit('update:annotations', updatedAnnotations);
    
    // 重置选中状态
    activeBoxIndex.value = -1;
    
    // 显示删除成功消息
    ElMessage.success('标注已删除');
  }
  
  // 删除选中的多边形
  if ((event.key === 'Delete' || event.key === 'Backspace') && activePolygonIndex.value >= 0) {
    const updatedAnnotations = [...props.annotations];
    updatedAnnotations.splice(activePolygonIndex.value, 1);
    emit('update:annotations', updatedAnnotations);
    
    // 重置选中状态
    activePolygonIndex.value = -1;
    
    // 显示删除成功消息
    ElMessage.success('标注已删除');
  }
};

// 监听标注变化
watch(() => props.annotations, () => {
  drawAnnotations();
}, { deep: true });

// 监听图片URL变化
watch(() => props.imageUrl, () => {
  imageLoaded.value = false;
}, { immediate: true });

// 监听工具选择变化，延迟重绘避免切换下拉时卡顿（不阻塞主线程）
watch(() => props.selectedTool, () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      drawAnnotations();
    });
  });
});

// 组件挂载和卸载
const handleCanvasMouseEnter = (event) => {
  // 更新光标样式
  if (annotationCanvas.value) {
    updateCursorStyle(event);
  }
};

onMounted(() => {
  window.addEventListener('resize', resizeHandler);
  // 添加键盘事件监听
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler);
  // 移除键盘事件监听
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<style scoped>
.annotation-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.image-wrapper {
  position: relative;
  width: 100%;
}

.display-image {
  display: block;
  max-width: 100%;
  height: auto;
}

.annotation-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

/* 标签编辑弹出框样式 */
.label-editor {
  position: absolute;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 10px;
  z-index: 1000;
}

.label-editor .el-select {
  width: 150px;
}

/* 提示信息样式 */
.annotation-hint {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  z-index: 100;
}
</style>