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
            <div v-else-if="annotation.type === 'bbox'">
              标签: {{ annotation.label }}<br>
              置信度: {{ (annotation.confidence * 100).toFixed(2) }}%<br>
              位置: x={{ annotation.bbox.x.toFixed(2) }}%, y={{ annotation.bbox.y.toFixed(2) }}%<br>
              尺寸: {{ annotation.bbox.width.toFixed(2) }}% × {{ annotation.bbox.height.toFixed(2) }}%
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
  }
});

const visible = ref(props.initialVisible);

const toggleVisibility = () => {
  visible.value = !visible.value;
};

// 标注类型名称映射
const getAnnotationTypeName = (type) => {
  const typeNames = {
    'rectanglelabels': '边界框',
    'polygonlabels': '多边形',
    'keypointlabels': '关键点',
    'bbox': '目标检测',
    'polygon': '图像分割',
    'classification': '图像分类'
  };
  return typeNames[type] || type;
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
  max-height: 300px;
  overflow-y: auto;
  padding: 10px;
}

.annotation-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 10px;
}

.annotation-item {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 10px;
  background-color: #fff;
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