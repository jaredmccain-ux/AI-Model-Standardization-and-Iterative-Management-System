<template>
  <div class="image-gallery">
    <div class="gallery-header">
      <h3>已上传的图片 ({{ images.length }}张)</h3>
      <div class="selection-controls" v-if="images.length > 0">
        <el-checkbox v-model="selectAll" @change="handleSelectAll">全选</el-checkbox>
        <el-button 
          type="primary" 
          size="small" 
          :disabled="selectedImages.length === 0"
          @click="batchAnnotate"
        >
          批量标注
        </el-button>
        <el-button 
          type="success" 
          size="small" 
          :disabled="selectedImages.length === 0"
          @click="batchExport"
        >
          批量导出
        </el-button>
        <el-button 
          type="warning" 
          size="small" 
          :disabled="selectedImages.length === 0"
          @click="batchClearAnnotations"
        >
          批量清除标注
        </el-button>
        <el-button 
          type="danger" 
          size="small" 
          :disabled="selectedImages.length === 0"
          @click="batchDelete"
        >
          批量删除
        </el-button>
      </div>
    </div>
    <div class="images-grid">
      <div 
        v-for="(image, index) in images" 
        :key="index"
        class="image-item"
        :class="{ active: currentIndex === index, selected: selectedImages.includes(index) }"
        @click="selectImage(index, $event)"
      >
        <div class="checkbox-wrapper" @click.stop>
          <el-checkbox v-model="image.selected" @change="updateSelection(index)"></el-checkbox>
        </div>
        <img :src="image.url" :alt="image.name" />
        <div class="image-overlay">
          <span class="image-name">{{ image.name }}</span>
          <el-button 
            type="danger" 
            size="small" 
            circle 
            @click.stop="removeImage(index)"
            class="remove-btn"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Close } from '@element-plus/icons-vue';

const props = defineProps({
  images: {
    type: Array,
    default: () => []
  },
  currentIndex: {
    type: Number,
    default: -1
  }
});

const emit = defineEmits(['select', 'remove', 'batchAnnotate', 'batchExport', 'batchClearAnnotations', 'batchDelete']);

// 多选相关状态
const selectedImages = ref([]);
const selectAll = ref(false);

// 监听images变化，初始化selected属性
watch(() => props.images, (newImages) => {
  newImages.forEach(image => {
    if (image.selected === undefined) {
      image.selected = false;
    }
  });
}, { immediate: true, deep: true });

// 全选/取消全选
const handleSelectAll = (val) => {
  props.images.forEach((image, index) => {
    image.selected = val;
  });
  updateSelectedImages();
};

// 更新选中状态
const updateSelection = (index) => {
  updateSelectedImages();
  // 检查是否所有图片都被选中
  selectAll.value = props.images.length > 0 && props.images.every(img => img.selected);
};

// 更新选中的图片索引数组
const updateSelectedImages = () => {
  selectedImages.value = props.images
    .map((image, index) => image.selected ? index : -1)
    .filter(index => index !== -1);
};

// 选择图片
const selectImage = (index, event) => {
  // 如果按住Ctrl键，则切换选中状态
  if (event && event.ctrlKey) {
    props.images[index].selected = !props.images[index].selected;
    updateSelection(index);
  } else {
    // 否则正常选择图片
    emit('select', index);
  }
};

// 移除图片
const removeImage = (index) => {
  emit('remove', index);
  // 更新选中状态
  updateSelectedImages();
};

// 批量标注
const batchAnnotate = () => {
  emit('batchAnnotate', selectedImages.value);
};

// 批量导出
const batchExport = () => {
  emit('batchExport', selectedImages.value);
};

// 批量清除标注
const batchClearAnnotations = () => {
  emit('batchClearAnnotations', selectedImages.value);
};

// 批量删除
const batchDelete = () => {
  emit('batchDelete', selectedImages.value);
};

// 供父组件（如智能体增广）获取当前选中的图片索引
defineExpose({
  getSelectedIndices() {
    return selectedImages.value;
  }
});
</script>

<style scoped>
.image-gallery {
  padding: 10px;
  height: auto;
  max-height: 300px;
  overflow-y: auto;
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.selection-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 10px;
}

.image-item {
  position: relative;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.3s;
}

.image-item.active {
  border-color: #409EFF;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.6);
}

.image-item.selected {
  border-color: #67C23A;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.6);
}

.image-item.active.selected {
  border-color: #E6A23C;
  box-shadow: 0 0 8px rgba(230, 162, 60, 0.6);
}

.checkbox-wrapper {
  position: absolute;
  top: 5px;
  left: 5px;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.7);
  border-radius: 3px;
  padding: 2px;
}

.image-item img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  display: block;
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 4px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.image-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.remove-btn {
  padding: 2px;
  height: 20px;
  width: 20px;
}
</style>