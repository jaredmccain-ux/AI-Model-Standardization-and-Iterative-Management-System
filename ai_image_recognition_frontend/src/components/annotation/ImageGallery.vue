<template>
  <div class="image-gallery">
    <div class="gallery-header">
      <div class="gallery-title-row">
        <h3>已上传的图片 · 共 {{ images.length }} 张，已标注 {{ annotatedCount }} 张</h3>
        <el-select v-model="filterOption" placeholder="筛选" size="small" style="width: 110px;" @change="emitFilter">
          <el-option label="全部" value="all"></el-option>
          <el-option label="原图" value="origin"></el-option>
          <el-option label="增广图" value="augmented"></el-option>
          <el-option label="已标注" value="annotated"></el-option>
          <el-option label="未标注" value="unannotated"></el-option>
        </el-select>
      </div>
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
        v-for="item in displayedItems" 
        :key="item.index"
        class="image-item"
        :class="{ active: currentIndex === item.index, selected: selectedImages.includes(item.index) }"
        @click="selectImage(item.index, $event)"
      >
        <div class="checkbox-wrapper" @click.stop>
          <el-checkbox v-model="item.image.selected" @change="updateSelection(item.index)"></el-checkbox>
        </div>
        <img :src="item.image.url" :alt="item.image.name" />
        <div class="image-overlay">
          <span class="image-name">{{ item.image.name }}</span>
          <el-button 
            type="danger" 
            size="small" 
            circle 
            @click.stop="removeImage(item.index)"
            class="remove-btn"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="annotation-badge" v-if="getStats(item.index).count > 0">
          <span class="badge-count">{{ getStats(item.index).count }}个框</span>
          <span class="badge-saved" v-if="getStats(item.index).saved">已保存</span>
        </div>
        <div class="augmented-badge" v-if="item.image.isAugmented">增广</div>
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
  },
  /** 每张图的标注数量与是否已保存，与 images 索引对应 */
  annotationStats: {
    type: Array,
    default: () => []
  },
  /** 筛选：all / annotated / unannotated */
  filterOption: {
    type: String,
    default: 'all'
  }
});

const emit = defineEmits(['select', 'remove', 'batchAnnotate', 'batchExport', 'batchClearAnnotations', 'batchDelete', 'update:filterOption']);

const filterOption = ref(props.filterOption);
watch(() => props.filterOption, (v) => { filterOption.value = v; });

function getStats(index) {
  const s = props.annotationStats[index];
  return s ? { count: s.count || 0, saved: !!s.saved } : { count: 0, saved: false };
}

const annotatedCount = computed(() => {
  return (props.annotationStats || []).filter(s => s && (s.count || 0) > 0).length;
});

const displayedIndices = computed(() => {
  const stats = props.annotationStats;
  const filter = filterOption.value;
  const images = props.images;
  if (filter === 'all') return images.map((_, i) => i);
  return images
    .map((_, i) => i)
    .filter(i => {
      const count = (stats[i] && stats[i].count) || 0;
      const isAug = images[i] && images[i].isAugmented === true;
      if (filter === 'origin') return !isAug;
      if (filter === 'augmented') return isAug;
      if (filter === 'annotated') return count > 0;
      if (filter === 'unannotated') return count === 0;
      return true;
    });
});

const displayedItems = computed(() =>
  displayedIndices.value.map(index => ({ index, image: props.images[index] }))
);

function emitFilter() {
  emit('update:filterOption', filterOption.value);
}

// 多选相关状态
const selectedImages = ref([]);
const selectAll = ref(false);

watch(() => props.images, (newImages) => {
  newImages.forEach(image => {
    if (image.selected === undefined) image.selected = false;
  });
}, { immediate: true, deep: true });

const handleSelectAll = (val) => {
  displayedItems.value.forEach(({ index }) => {
    props.images[index].selected = val;
  });
  updateSelectedImages();
};

const updateSelection = (index) => {
  updateSelectedImages();
  selectAll.value = displayedItems.value.length > 0 && displayedItems.value.every(item => props.images[item.index].selected);
};

const updateSelectedImages = () => {
  selectedImages.value = props.images
    .map((image, index) => image.selected ? index : -1)
    .filter(index => index !== -1);
};

const selectImage = (index, event) => {
  if (event && event.ctrlKey) {
    props.images[index].selected = !props.images[index].selected;
    updateSelection(index);
  } else {
    emit('select', index);
  }
};

const removeImage = (index) => {
  emit('remove', index);
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

.gallery-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.annotation-badge {
  position: absolute;
  top: 28px;
  right: 5px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.badge-count {
  background: rgba(103, 194, 58, 0.95);
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-saved {
  background: rgba(64, 158, 255, 0.95);
  color: #fff;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
}

.augmented-badge {
  position: absolute;
  top: 28px;
  left: 5px;
  z-index: 9;
  background: rgba(230, 162, 60, 0.95);
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
