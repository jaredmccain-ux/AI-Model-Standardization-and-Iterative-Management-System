<template>
  <div class="annotations-section" :class="{ collapsed: !visible }">
    <div class="annotations-header">
      <h3>标注结果</h3>
      <el-button type="text" @click="toggleVisibility" class="toggle-btn">
        <el-icon>
          <arrow-up v-if="visible" />
          <arrow-down v-else />
        </el-icon>
      </el-button>
    </div>
    <div v-show="visible" class="annotations-list">
      <div class="annotation-items">
        <div 
          v-for="(annotation, index) in annotations"
          :key="index"
          class="annotation-item"
          :class="{ active: selectedIndex === index }"
          @click="onSelectItem(index)"
        >
          <div class="annotation-type">{{ getAnnotationTypeName(annotation.type) }}</div>
          <div class="annotation-details">
            <div v-if="annotation.type === 'rectanglelabels'">
              标签: {{ annotation.value.rectanglelabels.join(', ') }}<br>
              位置: x={{ annotation.value.x }}%, y={{ annotation.value.y }}%<br>
              尺寸: {{ annotation.value.width }}% × {{ annotation.value.height }}%
            </div>
            <div v-else-if="annotation.type === 'polygonlabels'">
              标签: {{ annotation.value.polygonlabels.join(', ') }}<br>
              顶点数: {{ annotation.value.points.length }}
            </div>
            <div v-else-if="annotation.type === 'keypointlabels'">
              标签: {{ annotation.value.keypointlabels.join(', ') }}<br>
              位置: x={{ annotation.value.x }}%, y={{ annotation.value.y }}%
            </div>
            <div v-else-if="annotation.type === 'bbox' || annotation.type === 'bounding_box' || annotation.type === 'obb'">
              类型: {{ getBoxTypeLabel(annotation) }}<br>
              标签: {{ annotation.label }}<br>
              <template v-if="annotation.confidence != null">置信度: {{ (annotation.confidence * 100).toFixed(2) }}%<br></template>
              位置: x={{ (annotation.bbox?.x ?? 0).toFixed(2) }}%, y={{ (annotation.bbox?.y ?? 0).toFixed(2) }}%<br>
              尺寸: {{ (annotation.bbox?.width ?? 0).toFixed(2) }}% × {{ (annotation.bbox?.height ?? 0).toFixed(2) }}%
              <template v-if="shouldShowAngle(annotation)"><br>旋转: {{ formatAngle(annotation.bbox?.angle) }}°</template>
            </div>
            <div v-else-if="annotation.type === 'polygon'">
              标签: {{ annotation.label }}<br>
              置信度: {{ (annotation.confidence * 100).toFixed(2) }}%<br>
              顶点数: {{ annotation.points.length }}
            </div>
            <div v-else-if="annotation.type === 'classification'">
              标签: {{ annotation.label }}<br>
              置信度: {{ (annotation.confidence * 100).toFixed(2) }}%
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue';

const props = defineProps({
  annotations: {
    type: Array,
    default: () => []
  },
  initialVisible: {
    type: Boolean,
    default: true
  },
  /** 当前选中的标注索引（与画布高亮联动） */
  selectedIndex: {
    type: Number,
    default: -1
  }
});

const emit = defineEmits(['toggle', 'select']);

const onSelectItem = (index) => {
  emit('select', index);
};

const visible = ref(props.initialVisible);

const toggleVisibility = () => {
  visible.value = !visible.value;
};

// 标注类型名称映射（列表标题用）
const getAnnotationTypeName = (type) => {
  const typeNames = {
    'rectanglelabels': '边界框',
    'polygonlabels': '多边形',
    'keypointlabels': '关键点',
    'bbox': '目标检测',
    'bounding_box': '矩形框',
    'obb': '旋转框(OBB)',
    'polygon': '图像分割',
    'classification': '图像分类'
  };
  return typeNames[type] || type;
};

// 详情中显示的框类型（矩形框 / 旋转框(OBB)）
const getBoxTypeLabel = (annotation) => {
  if (annotation.type === 'obb') return '旋转框(OBB)';
  if (annotation.type === 'bounding_box' || annotation.type === 'bbox') return '矩形框';
  return getAnnotationTypeName(annotation.type);
};

// OBB 或存在角度时显示旋转角；OBB 始终显示（含 0°）
const shouldShowAngle = (annotation) => {
  if (!annotation.bbox) return false;
  if (annotation.type === 'obb') return true;
  return annotation.bbox.angle != null && annotation.bbox.angle !== 0;
};

const formatAngle = (rad) => {
  if (rad == null) return '0';
  return ((rad * 180) / Math.PI).toFixed(1);
};
</script>

<style scoped>
.annotations-section {
  margin-top: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  transition: all 0.3s;
}

.annotations-section.collapsed {
  max-height: 40px;
}

.annotations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e0e0e0;
}

.annotations-header h3 {
  margin: 0;
  font-size: 16px;
}

.annotations-list {
  max-height: min(40vh, 300px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px;
  width: 100%;
  box-sizing: border-box;
}

.annotation-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15.625rem), 1fr));
  gap: 10px;
}

.annotation-item {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 10px;
  background-color: #fff;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}
.annotation-item:hover {
  border-color: #c0c4cc;
  background-color: #fafafa;
}
.annotation-item.active {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.annotation-type {
  font-weight: bold;
  margin-bottom: 5px;
  color: #409EFF;
}

.annotation-details {
  font-size: 13px;
  line-height: 1.5;
}

.toggle-btn {
  padding: 2px;
}
</style>