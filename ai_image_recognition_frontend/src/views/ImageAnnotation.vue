<template>
  <div class="page-container">
    <div class="header-section">
      <div class="header-title-row">
        <h1>图像标注</h1>
        <div class="project-stats" v-if="uploadedImages.length > 0">
          <span>已标注 <strong>{{ projectStats.annotatedCount }}/{{ projectStats.totalImages }}</strong> 张</span>
          <span class="stats-sep">·</span>
          <span>共 <strong>{{ projectStats.totalBoxes }}</strong> 个目标</span>
          <span class="stats-sep">·</span>
          <span 
            class="stats-link" 
            v-if="projectStats.unannotatedCount > 0"
            @click="goToFirstUnannotated"
          >
            未标注 {{ projectStats.unannotatedCount }} 张
          </span>
        </div>
      </div>
      
      <!-- 第一行：上传按钮 -->
      <div class="toolbar-row" style="margin-bottom: 20px;">
        <div class="toolbar-left" style="display: flex; gap: 15px; align-items: center; flex-wrap: wrap; padding: 15px; background: #f5f7fa; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
          <div class="upload-section" style="display: flex; flex-direction: column; align-items: center; gap: 5px; min-width: 120px;">
            <el-upload
              class="upload-demo"
              action="#"
              :on-change="handleFileChange"
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              multiple
            >
              <el-button type="primary" size="large" plain>
                <el-icon><Plus /></el-icon>
                上传图片
              </el-button>
            </el-upload>
            <span class="upload-tip" style="font-size: 12px; color: #606266;">支持多张图片上传</span>
          </div>
          
          <div class="upload-section" style="display: flex; flex-direction: column; align-items: center; gap: 5px; min-width: 120px;">
            <el-upload
              class="upload-demo"
              action="#"
              :on-change="handleAnnotationImport"
              :auto-upload="false"
              :show-file-list="false"
              accept=".json,.txt,.xml"
              multiple
            >
              <el-button type="info" size="large" plain>
                <el-icon><Document /></el-icon>
                导入标注
              </el-button>
            </el-upload>
            <span class="upload-tip" style="font-size: 12px; color: #606266;">JSON/TXT/XML格式</span>
          </div>
          
          <div class="upload-section" style="display: flex; flex-direction: column; align-items: center; gap: 5px; min-width: 120px;">
            <el-button 
              type="success" 
              @click="importAnnotatedImages" 
              size="large"
            >
              <el-icon><Upload /></el-icon>
              批量导入
            </el-button>
            <span class="upload-tip" style="font-size: 12px; color: #606266;">图片+标注文件</span>
          </div>
        </div>
      </div>
      
      <!-- 第二行：标注模式选择 -->
      <div class="toolbar-row">
        <div class="mode-selection">
          <span class="mode-label">标注模式：</span>
          <el-radio-group v-model="annotationMode" @change="handleModeChange">
            <el-radio-button label="manual">手动标注</el-radio-button>
            <el-radio-button label="auto">自动标注</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      
      <!-- 第三行：自动标注工具和模型选择 -->
      <div v-if="annotationMode === 'auto'" class="toolbar-row annotation-tools">
        <el-select v-model="selectedTool" placeholder="选择标注类型" style="width: 180px; margin-right: 10px;" @change="handleToolChange">
          <el-option label="目标检测" value="object_detection"></el-option>
          <el-option label="图像分类" value="image_classification"></el-option>
          <el-option label="图像分割" value="image_segmentation"></el-option>
        </el-select>
        <el-select
          v-model="selectedModel"
          placeholder="选择模型"
          style="width: 220px; margin-right: 10px;"
          :loading="modelsLoading"
          :disabled="isDownloadingModel"
          @change="handleModelChange"
          @visible-change="(visible) => visible && onModelSelectOpen()"
        >
          <el-option
            v-for="model in availableModels"
            :key="model.value"
            :label="model.label"
            :value="model.value"
          />
        </el-select>
        <el-button type="success" plain @click="showImportModelDialog" :disabled="modelsLoading || isDownloadingModel">
          导入自己的模型
        </el-button>
        <el-button
          type="primary"
          @click="autoAnnotate"
          :disabled="!currentImageFile || !selectedTool || !selectedModel || isDownloadingModel"
          :loading="isAutoAnnotating"
        >
          AI自动标注
        </el-button>
      </div>

      <!-- 第三行：手动标注操作按钮 -->
      <div v-else-if="annotationMode === 'manual'" class="toolbar-row">
        <div class="manual-tools" style="display: flex; gap: 10px; align-items: center;">
          <el-select v-model="selectedTool" placeholder="选择标注工具" style="width: 180px; margin-right: 10px;">
            <el-option label="矩形框" value="object_detection"></el-option>
            <el-option label="旋转框(OBB)" value="object_detection_obb"></el-option>
          </el-select>
          <el-button @click="undoAnnotation" :disabled="annotationHistoryPast.length === 0" title="撤销 (Ctrl+Z)">
            撤销
          </el-button>
          <el-button @click="redoAnnotation" :disabled="annotationHistoryFuture.length === 0" title="重做 (Ctrl+Shift+Z)">
            重做
          </el-button>
          <el-button type="primary" @click="saveCurrentAnnotations" :disabled="currentAnnotations.length === 0">
            保存当前标注
          </el-button>
        </div>
      </div>

      <!-- 导入模型弹窗（放在 v-if/v-else-if 链之后，避免打断相邻关系） -->
      <el-dialog v-model="importModelDialogVisible" title="导入自己的模型" width="480px" :close-on-click-modal="false">
        <el-form :model="importModelForm" label-width="100px">
          <el-form-item label="模型文件" required>
            <el-upload :auto-upload="false" :limit="1" :on-change="onImportModelFileChange" accept=".pt,.pth,.onnx">
              <el-button type="primary" size="small">选择文件 (.pt / .pth / .onnx)</el-button>
            </el-upload>
            <div v-if="importModelForm.file" class="import-model-file-name">{{ importModelForm.file.name }}</div>
          </el-form-item>
          <el-form-item label="模型名称" required>
            <el-input v-model="importModelForm.name" placeholder="便于识别的名称" maxlength="64" show-word-limit />
          </el-form-item>
          <el-form-item label="任务类型" required>
            <el-select v-model="importModelForm.task" placeholder="选择任务类型" style="width: 100%">
              <el-option label="目标检测" value="detection" />
              <el-option label="图像分割" value="segmentation" />
              <el-option label="图像分类" value="classification" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="importModelDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="importModelUploading" @click="submitImportModel">导入</el-button>
        </template>
      </el-dialog>
      
      <!-- 标注工具使用说明 -->
      <div class="annotation-tips">
        <el-collapse>
          <el-collapse-item title="标注工具使用说明">
            <div class="tips-content">
              <h4>矩形框</h4>
              <ul>
                <li>选择「矩形框」后，在图片上左键拖拽绘制；松开后输入标签。</li>
                <li>点击框可拖拽移动，拖动四角调整大小；右键点击框可删除。</li>
              </ul>
              <h4>旋转框(OBB)</h4>
              <ul>
                <li>选择「旋转框(OBB)」后，左键拖拽绘制初始矩形，松开后输入标签。</li>
                <li>点击框可移动，拖动四角调大小，拖动顶部绿色圆点旋转；橙色线表示旋转框，蓝色为普通矩形。</li>
              </ul>
              <h4>画布操作</h4>
              <ul>
                <li>Ctrl + 滚轮：缩放画布；空格 + 左键拖拽：平移画布。</li>
                <li>右上角可点击「+」「−」「1:1」调节缩放。</li>
              </ul>
              <h4>快捷键</h4>
              <ul>
                <li>Esc：取消当前正在绘制的框。</li>
                <li>Delete / Backspace：删除当前选中的标注。</li>
                <li>Ctrl+Z：撤销；Ctrl+Shift+Z：重做（仅当前图片，最多约 20 步）。</li>
                <li>A / D 或 ← / →：上一张 / 下一张图片。</li>
              </ul>
            </div>
          </el-collapse-item>
          <el-collapse-item title="智能体数据增广">
            <div class="augmentation-section">
              <p class="augmentation-tip">在上方图片库中勾选要增广的图片，输入指令后点击「执行增广」。增广后的图片会追加到列表末尾；可在指令中写“生成2张/三张”等控制每张输入图的输出数量（最多6张，模型能力不足时会提示）。</p>
              <el-input
                v-model="augmentationInstruction"
                type="textarea"
                :rows="3"
                placeholder="例如：增加光照变化、添加轻微高斯噪声、水平翻转、逆时针旋转90度、提高对比度"
                class="augmentation-input"
              />
              <div class="augmentation-presets">
                <el-button size="small" @click="augmentationInstruction = '增加亮度，亮度倍数约1.2'">光照增强</el-button>
                <el-button size="small" @click="augmentationInstruction = '添加轻微高斯噪声，噪声标准差0.02'">添加噪声</el-button>
                <el-button size="small" @click="augmentationInstruction = '水平翻转'">水平翻转</el-button>
                <el-button size="small" @click="augmentationInstruction = '逆时针旋转90度'">旋转90°</el-button>
                <el-button size="small" @click="augmentationInstruction = '提高对比度，对比度倍数1.3'">提高对比度</el-button>
                <el-button size="small" @click="augmentationInstruction = '轻微高斯模糊，核大小3'">轻微模糊</el-button>
              </div>
              <el-button
                type="primary"
                :loading="isAugmenting"
                :disabled="uploadedImages.length === 0"
                @click="runAugmentation"
                class="augmentation-submit"
              >
                {{ isAugmenting ? '增广中…' : '执行增广' }}
              </el-button>
              <!-- 增广结果展示栏：仅展示本次会话中增广得到的图片 -->
              <div v-if="augmentedDisplayList.length > 0" class="augmented-results-panel">
                <div class="augmented-results-title">增广结果展示 · 共 {{ augmentedDisplayList.length }} 张</div>
                <div class="augmented-results-grid">
                  <div
                    v-for="entry in augmentedDisplayList"
                    :key="entry.globalIndex"
                    class="augmented-result-item"
                    :class="{ active: currentImageIndex === entry.globalIndex }"
                    @click="selectImage(entry.globalIndex)"
                  >
                    <img :src="entry.url" :alt="entry.name" />
                    <div class="augmented-result-info">
                      <span class="augmented-result-name" :title="entry.name">{{ entry.name }}</span>
                      <span v-if="entry.sourceName" class="augmented-result-source">原图：{{ entry.sourceName }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <!-- 第四行：清除和导出按钮 -->
      <div class="toolbar-row action-buttons">
        <el-button 
          type="warning" 
          @click="clearAnnotations" 
          :disabled="!currentAnnotations.length" 
          style="margin-right: 10px;"
        >
          清除标注
        </el-button>
        <el-select v-model="exportFormat" placeholder="选择格式" style="width: 120px; margin-right: 10px;">
          <el-option label="JSON" value="json"></el-option>
          <el-option label="COCO" value="coco"></el-option>
          <el-option label="Pascal VOC" value="voc"></el-option>
          <el-option label="YOLO" value="yolo"></el-option>
          <el-option label="DOTA (OBB)" value="dota"></el-option>
          <el-option label="CSV" value="csv"></el-option>
          <el-option label="YAML" value="yaml"></el-option>
        </el-select>
        <el-button 
          type="success" 
          @click="exportAnnotations" 
          :disabled="!currentAnnotations.length"
        >
          导出标注结果
        </el-button>
      </div>
    </div>

    <div class="content-section">
      <!-- 图片切换控制条，在顶部固定显示 -->
      <div class="image-navigation" v-if="uploadedImages.length > 0">
        <div class="nav-controls">
          <el-button 
            type="text" 
            :disabled="currentImageIndex <= 0"
            @click="previousImage"
            icon="ArrowLeft"
          >
            上一张
          </el-button>
          <span class="image-counter">
            {{ currentImageIndex + 1 }} / {{ uploadedImages.length }}
          </span>
          <el-button 
            type="text" 
            :disabled="currentImageIndex >= uploadedImages.length - 1"
            @click="nextImage"
            icon="ArrowRight"
          >
            下一张
          </el-button>
        </div>
        <!-- 简单的缩略图切换器 -->
        <div class="thumbnail-nav">
          <div 
            v-for="(image, index) in uploadedImages.slice(0, 6)" 
            :key="index"
            class="thumbnail-item"
            :class="{ active: index === currentImageIndex }"
            @click="selectImage(index)"
          >
            <img :src="image.url" :alt="image.name" />
          </div>
          <div class="thumbnail-more" v-if="uploadedImages.length > 6">
            +{{ uploadedImages.length - 6 }}
          </div>
        </div>
      </div>
      
      <!-- 图片库组件：放在画布上方 -->
      <div class="image-gallery-container" v-if="uploadedImages.length > 0">
        <ImageGallery 
          ref="imageGalleryRef"
          :images="uploadedImages"
          :currentIndex="currentImageIndex"
          :annotationStats="annotationStats"
          :filterOption="galleryFilter"
          @update:filterOption="galleryFilter = $event"
          @select="selectImage"
          @remove="removeImage"
          @batchAnnotate="handleBatchAnnotate"
          @batchExport="batchExportAnnotations"
          @batchClearAnnotations="handleBatchClearAnnotations"
          @batchDelete="handleBatchDelete"
        />
      </div>
      <div v-else class="upload-placeholder">
        <p>暂无上传的图片</p>
      </div>
      
      <!-- 主内容区域：当前图片显示 -->
      <div class="main-content">
        <div class="image-display-section">
          <div v-if="uploadedImages.length === 0" class="placeholder">
            <p>请上传图片开始使用AI标注</p>
          </div>
          <div v-else-if="!currentImageUrl" class="placeholder">
            <p>请选择一张图片进行AI标注</p>
          </div>
          <div v-else class="image-container">
            <div class="current-image-info">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4>{{ currentImage ? currentImage.name : '未选择图片' }}</h4>
                <div v-if="currentImage" style="display: flex; align-items: center; gap: 10px;">
                  <el-badge :value="currentAnnotations.length" type="success" show-zero>
                    <span style="color: #606266;">标注数</span>
                  </el-badge>
                  <span v-if="annotationMode === 'manual' && savedAnnotations[currentImageIndex]" style="color: #67c23a;">
                    ✓ 已保存
                  </span>
                </div>
              </div>
              <div class="annotation-status" v-if="currentAnnotations.length > 0">
                已标注：{{ currentAnnotations.length }} 个目标 {{ annotationMode === 'manual' ? '(手动)' : '(AI自动)' }}
              </div>
            </div>
            
            <!-- 使用标注画布组件（key 随当前图片变化，切换图片时强制重挂载以正确绘制该图片的标注） -->
            <AnnotationCanvas 
              :key="currentImageIndex >= 0 ? currentImageIndex : 'none'"
              :imageUrl="currentImageUrl"
              :imageName="currentImage?.name"
              :annotations="currentAnnotations"
              :selectedTool="selectedTool"
              :selected-annotation-index="selectedAnnotationIndexForCanvas"
              @update:annotations="updateAnnotations"
              @polygon-completed="handlePolygonCompleted"
            />
          </div>
        </div>

        <!-- 标注框信息栏：始终预留区域，有标注时展示列表 -->
        <div class="annotation-list-wrapper" :class="{ 'has-annotations': currentAnnotations.length > 0 }">
          <AnnotationList 
            v-if="currentAnnotations.length > 0" 
            :annotations="currentAnnotations" 
            :initialVisible="annotationsVisible"
            :selected-index="selectedAnnotationIndexForCanvas"
            @toggle="annotationsVisible = !annotationsVisible"
            @select="selectedAnnotationIndexForCanvas = $event"
          />
          <div v-else class="annotation-list-empty">
            <span>当前图片暂无标注，绘制框后可在此查看标注信息</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineOptions({ name: 'ImageAnnotation' });
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox, ElUpload, ElButton, ElSelect, ElOption, ElOptionGroup, ElCheckboxGroup, ElCheckbox, ElInput, ElForm, ElFormItem, ElDialog, ElRadioGroup, ElRadio, ElBadge } from 'element-plus';
import { Plus, Document, Upload } from '@element-plus/icons-vue';
import { exportAnnotationData, saveSingleAnnotation, saveBatchAnnotations, deleteAnnotation, getImageAnnotations } from '@/api/annotation.js';
import { visioFirmAPI } from '@/api/visioFirm.js';
import { runAugmentation as runAugmentationAPI } from '@/api/augmentation.js';
import { getUserConfig, saveUserConfig } from '@/utils/configManager.js';

// 导入组件
import AnnotationCanvas from '@/components/annotation/AnnotationCanvas.vue';
import AnnotationList from '@/components/annotation/AnnotationList.vue';
import ImageGallery from '@/components/annotation/ImageGallery.vue';

// 状态管理
const uploadedImages = ref([]);
const currentImageIndex = ref(-1);
const currentImageFile = ref(null); // 当前选中的图片文件对象
const selectedTool = ref('object_detection'); // 默认使用矩形框标注
const isAutoAnnotating = ref(false);
const currentAnnotations = ref([]);
const annotatedImageUrl = ref('');
const annotationsVisible = ref(true);
const selectedModel = ref(''); // 当前使用的模型
const imageAnnotations = ref({}); // 存储每张图片的标注结果，格式为 {imageIndex: annotations}，注意：这是对象不是数组！
const annotationMode = ref('manual'); // 'manual' 或 'auto'
const exportFormat = ref('json'); // 导出格式，默认为JSON
const savedAnnotations = ref({}); // 已保存的标注数据，用于恢复，注意：这是对象不是数组！
const galleryFilter = ref('all'); // 图片库筛选：all / annotated / unannotated / origin / augmented

// 增广结果展示用：仅包含本会话中增广得到的图片（含在列表中的全局索引，便于点击跳转）
const augmentedDisplayList = computed(() => {
  return uploadedImages.value
    .map((img, idx) => ({ ...img, globalIndex: idx }))
    .filter((item) => item.isAugmented === true);
});

// 撤销/重做：当前图片的标注历史栈（最多 20 步）
const MAX_ANNOTATION_HISTORY = 20;
const annotationHistoryPast = ref([]);   // 过去状态，undo 时从栈顶取出
const annotationHistoryFuture = ref([]); // 重做栈，redo 时从栈顶取出

// 标注列表与画布联动：当前在列表中选中的标注索引（画布会高亮该项）
const selectedAnnotationIndexForCanvas = ref(-1);

// 智能体数据增广
const imageGalleryRef = ref(null);
const augmentationInstruction = ref('');
const isAugmenting = ref(false);

// 用户配置
const userConfig = ref(getUserConfig());

// 类别管理
const categories = ref(['person', 'car', 'dog', 'cat']); // 默认类别

// 可用模型列表（展示用：{ value, label, isLocal, source }）
const availableModels = ref([]);
// 从 API 拉取的全量模型列表
const apiModelsList = ref([]);
const modelsLoading = ref(false);
const isDownloadingModel = ref(false);
// 导入模型弹窗
const importModelDialogVisible = ref(false);
const importModelForm = ref({ file: null, name: '', task: 'detection' });
const importModelUploading = ref(false);

// 标注类型 -> 后端 task 字段
const TOOL_TO_TASK = {
  object_detection: 'detection',
  image_classification: 'classification',
  image_segmentation: 'segmentation'
};

// 兜底静态模型（API 失败时用）
const modelsByTypeFallback = {
  object_detection: [
    { value: 'YOLO', label: 'YOLOv8-nano (内置)', source: 'builtin', isLocal: true },
    { value: 'FasterRCNN', label: 'Faster R-CNN (内置)', source: 'builtin', isLocal: true },
    { value: 'SSD', label: 'SSD (内置)', source: 'builtin', isLocal: true },
    { value: 'yolov8n', label: 'YOLOv8-nano', source: 'catalog', isLocal: false },
    { value: 'yolov8s', label: 'YOLOv8-small', source: 'catalog', isLocal: false },
    { value: 'yolov8m', label: 'YOLOv8-medium', source: 'catalog', isLocal: false },
    { value: 'yolov8l', label: 'YOLOv8-large', source: 'catalog', isLocal: false }
  ],
  image_classification: [
    { value: 'ResNet', label: 'ResNet50 (内置)', source: 'builtin', isLocal: true },
    { value: 'EfficientNet', label: 'EfficientNet (内置)', source: 'builtin', isLocal: true },
    { value: 'yolov8n-cls', label: 'YOLOv8-nano-Cls', source: 'catalog', isLocal: false }
  ],
  image_segmentation: [
    { value: 'YOLO-Seg', label: 'YOLOv8-Seg (内置)', source: 'builtin', isLocal: true },
    { value: 'SAM', label: 'SAM 分割一切 (内置)', source: 'builtin', isLocal: true },
    { value: 'MaskRCNN', label: 'Mask R-CNN (内置)', source: 'builtin', isLocal: true },
    { value: 'yolov8n-seg', label: 'YOLOv8-nano-Seg', source: 'catalog', isLocal: false },
    { value: 'yolov8s-seg', label: 'YOLOv8-small-Seg', source: 'catalog', isLocal: false }
  ]
};

// 定义computed属性
const currentImage = computed(() => {
  return currentImageIndex.value >= 0 ? uploadedImages.value[currentImageIndex.value] : null;
});

// currentImageFile已在其他位置定义

// 使用已定义的availableModels ref

const currentImageUrl = computed(() => {
  return annotatedImageUrl.value || currentImage.value?.url || '';
});

// 图片库：每张图的标注数量与是否已保存（与 uploadedImages 索引对应）
const annotationStats = computed(() => {
  const list = uploadedImages.value;
  return list.map((_, i) => ({
    count: (imageAnnotations.value[i] || []).length,
    saved: !!savedAnnotations.value[i]
  }));
});

// 项目进度统计
const projectStats = computed(() => {
  const total = uploadedImages.value.length;
  let annotatedCount = 0;
  let totalBoxes = 0;
  for (let i = 0; i < total; i++) {
    const n = (imageAnnotations.value[i] || []).length;
    if (n > 0) annotatedCount++;
    totalBoxes += n;
  }
  return {
    totalImages: total,
    annotatedCount,
    unannotatedCount: total - annotatedCount,
    totalBoxes
  };
});

// 跳转到第一张未标注的图片
function goToFirstUnannotated() {
  for (let i = 0; i < uploadedImages.value.length; i++) {
    if (!(imageAnnotations.value[i] || []).length) {
      selectImage(i);
      return;
    }
  }
}

// 从后端拉取模型列表
async function fetchModels() {
  modelsLoading.value = true;
  try {
    const list = await visioFirmAPI.getModels();
    apiModelsList.value = Array.isArray(list) ? list : [];
  } catch (e) {
    console.error('拉取模型列表失败:', e);
    apiModelsList.value = [];
  } finally {
    modelsLoading.value = false;
  }
}

// 打开模型下拉时重新拉取列表，以便反映「已删除」等状态变化
async function onModelSelectOpen() {
  await fetchModels();
  refreshAvailableModels();
}

// 根据当前 selectedTool 刷新可用模型选项
function refreshAvailableModels() {
  const task = TOOL_TO_TASK[selectedTool.value];
  if (apiModelsList.value.length > 0 && task) {
    const filtered = apiModelsList.value.filter(m => (m.task || '').toLowerCase() === task);
    availableModels.value = filtered.map(m => ({
      value: m.id,
      label: m.name,
      isLocal: m.isLocal,
      source: m.source
    }));
  } else {
    availableModels.value = (modelsByTypeFallback[selectedTool.value] || []).map(m => ({
      ...m,
      isLocal: m.isLocal === true,
      source: m.source || 'builtin'
    }));
  }
  if (availableModels.value.length > 0 && !availableModels.value.some(m => m.value === selectedModel.value)) {
    selectedModel.value = availableModels.value[0].value;
  }
}

// 工具类型变更处理
const handleToolChange = () => {
  refreshAvailableModels();
};

// 模型选择变更：目录模型始终允许用户自行选择是否重新下载到本地
async function handleModelChange(modelValue) {
  const item = availableModels.value.find(m => m.value === modelValue);
  if (!item || item.source !== 'catalog') return;
  try {
    const action = await ElMessageBox.confirm(
      '该模型可按需重新下载到本地。\n\n点击「下载到本地」后将直接弹出保存路径选择。',
      '模型加载方式',
      {
        confirmButtonText: '下载到本地',
        cancelButtonText: '暂不下载',
        type: 'info',
        distinguishCancelAndClose: true
      }
    );
    if (action !== 'confirm') return;
    isDownloadingModel.value = true;
    try {
      await visioFirmAPI.saveModelFileAs(modelValue);
      ElMessage.success('模型已重新下载并保存到您选择的路径');
    } catch (saveErr) {
      if (saveErr?.name === 'AbortError' || saveErr === 'cancel' || saveErr === 'close') {
        ElMessage.info('已取消下载');
        return;
      }
      ElMessage.warning(saveErr?.message || '下载或保存失败');
    }
    await fetchModels();
    refreshAvailableModels();
  } catch (e) {
    if (e === 'cancel') {
      ElMessage.info('已选择暂不下载');
      return;
    }
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e?.message || '下载失败');
  } finally {
    isDownloadingModel.value = false;
  }
}

function showImportModelDialog() {
  importModelForm.value = { file: null, name: '', task: TOOL_TO_TASK[selectedTool.value] || 'detection' };
  importModelDialogVisible.value = true;
}
function onImportModelFileChange(file) {
  importModelForm.value.file = file?.raw || file;
}
async function submitImportModel() {
  if (!importModelForm.value.file) {
    ElMessage.warning('请选择模型文件');
    return;
  }
  if (!importModelForm.value.name?.trim()) {
    ElMessage.warning('请填写模型名称');
    return;
  }
  importModelUploading.value = true;
  try {
    const res = await visioFirmAPI.uploadModel(
      importModelForm.value.file,
      importModelForm.value.name.trim(),
      importModelForm.value.task
    );
    if (res?.model?.id) {
      ElMessage.success('模型导入成功');
      importModelDialogVisible.value = false;
      await fetchModels();
      refreshAvailableModels();
      selectedModel.value = res.model.id;
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导入失败');
  } finally {
    importModelUploading.value = false;
  }
}

// AI自动标注（使用 visiofirm 接口，支持内置/目录/用户上传模型）
const autoAnnotate = async () => {
  if (!currentImageFile.value) {
    ElMessage.warning('请先选择一张图片');
    return;
  }
  if (!selectedTool.value || !selectedModel.value) {
    ElMessage.warning('请先选择标注工具和模型');
    return;
  }

  isAutoAnnotating.value = true;
  try {
    ElMessage.info('正在分析图片，请稍候...');
    const formData = new FormData();
    formData.append('image', currentImageFile.value);
    formData.append('tool', selectedTool.value);
    formData.append('model', selectedModel.value);
    formData.append('categories', JSON.stringify(categories.value));
    const response = await visioFirmAPI.autoAnnotate(formData);

    if (response.data && response.data.annotations) {
      const annotations = response.data.annotations;
      
      try {
        // 确保标注数据格式正确（兼容 visiofirm 返回格式与旧 Label Studio 格式）
        const processedAnnotations = annotations.map(ann => {
          const newAnn = { ...ann };
          // visiofirm 直接返回的 bbox / classification / polygon
          if (newAnn.type === 'bbox' && newAnn.bbox && typeof newAnn.bbox === 'object') {
            return {
              type: 'bbox',
              label: newAnn.label || 'unknown',
              confidence: newAnn.confidence ?? 1.0,
              bbox: {
                x: parseFloat(newAnn.bbox.x ?? 0),
                y: parseFloat(newAnn.bbox.y ?? 0),
                width: parseFloat(newAnn.bbox.width ?? 0),
                height: parseFloat(newAnn.bbox.height ?? 0)
              }
            };
          }
          if (newAnn.type === 'classification') {
            return {
              type: 'classification',
              label: newAnn.label || newAnn.class_name || '',
              confidence: newAnn.confidence ?? 0
            };
          }
          if ((newAnn.type === 'polygon' || newAnn.points) && Array.isArray(newAnn.points)) {
            return {
              type: 'polygon',
              label: newAnn.label || 'unknown',
              confidence: newAnn.confidence ?? 1.0,
              points: newAnn.points
            };
          }
          // 后端返回的 Label Studio 格式（rectanglelabels + value.x/y/width/height）转为画布需要的 bbox 格式
          if (newAnn.type === 'rectanglelabels' && newAnn.value) {
              return {
                type: 'bbox',
                label: (newAnn.value.rectanglelabels && newAnn.value.rectanglelabels[0]) || 'unknown',
                bbox: {
                  x: parseFloat(newAnn.value.x ?? 0),
                  y: parseFloat(newAnn.value.y ?? 0),
                  width: parseFloat(newAnn.value.width ?? 0),
                  height: parseFloat(newAnn.value.height ?? 0)
                },
                confidence: newAnn.confidence ?? 1.0
              };
            }
            
            // 图像分类：后端返回 class_name + confidence，转为画布需要的 type: 'classification' + label
            const hasBbox = newAnn.bbox && (typeof newAnn.bbox === 'object' ? (newAnn.bbox.width != null && newAnn.bbox.height != null) : Array.isArray(newAnn.bbox) && newAnn.bbox.length >= 4);
            const hasPoints = Array.isArray(newAnn.points) && newAnn.points.length >= 3;
            if (!hasBbox && !hasPoints && newAnn.class_name != null && newAnn.confidence != null) {
              return {
                type: 'classification',
                label: newAnn.class_name,
                confidence: parseFloat(newAnn.confidence)
              };
            }
            
            // 图像分割：后端返回 class_name + confidence + points，转为画布需要的 type: 'polygon'
            if (hasPoints) {
              return {
                type: 'polygon',
                label: newAnn.class_name ?? newAnn.label ?? 'unknown',
                confidence: newAnn.confidence != null ? parseFloat(newAnn.confidence) : 1.0,
                points: newAnn.points
              };
            }
            
            // 仅当确实有 bbox 或后续会标准化出 bbox 时才设为 bbox，避免把分类/分割误设为 bbox
            if (newAnn.type === undefined && (newAnn.bbox != null || newAnn.value != null)) {
              newAnn.type = 'bbox';
            }
            
            // 确保bbox对象格式正确
            if (newAnn.bbox && typeof newAnn.bbox === 'object' && !Array.isArray(newAnn.bbox)) {
              // 确保bbox对象的坐标值为数字
              const bbox = {
                x: parseFloat(newAnn.bbox.x || 0),
                y: parseFloat(newAnn.bbox.y || 0),
                width: parseFloat(newAnn.bbox.width || 0),
                height: parseFloat(newAnn.bbox.height || 0)
              };
              
              // 检查是否需要将像素坐标转换为百分比坐标
              // 如果坐标值看起来像像素坐标（大于100），则转换为百分比
              if (bbox.x > 100 || bbox.y > 100 || bbox.width > 100 || bbox.height > 100) {
                // 假设当前图片尺寸为1000x1000进行比例调整
                // 实际应用中，应该从图片元素获取真实尺寸
                const imgWidth = 1000;
                const imgHeight = 1000;
                
                // 转换为百分比坐标
                newAnn.bbox = {
                  x: (bbox.x / imgWidth) * 100,
                  y: (bbox.y / imgHeight) * 100,
                  width: (bbox.width / imgWidth) * 100,
                  height: (bbox.height / imgHeight) * 100
                };
              } else {
                // 已经是百分比坐标或小数值，直接使用
                newAnn.bbox = bbox;
              }
            } else if (Array.isArray(newAnn.bbox)) {
              // 处理数组格式的bbox
              const bboxArray = newAnn.bbox.map(val => parseFloat(val || 0));
              
              // 检查是否需要转换为百分比坐标
              if (bboxArray.some(val => val > 100)) {
                // 假设当前图片尺寸为1000x1000进行比例调整
                const imgWidth = 1000;
                const imgHeight = 1000;
                
                // 处理COCO格式的bbox [x, y, width, height]
                if (bboxArray.length === 4) {
                  newAnn.bbox = {
                    x: (bboxArray[0] / imgWidth) * 100,
                    y: (bboxArray[1] / imgHeight) * 100,
                    width: (bboxArray[2] / imgWidth) * 100,
                    height: (bboxArray[3] / imgHeight) * 100
                  };
                }
              } else if (bboxArray.length === 4) {
                // 已经是百分比坐标的数组格式，转换为对象格式
                newAnn.bbox = {
                  x: bboxArray[0],
                  y: bboxArray[1],
                  width: bboxArray[2],
                  height: bboxArray[3]
                };
              }
            }
            
            return newAnn;
          });
        
        // 更新标注结果
        currentAnnotations.value = [...processedAnnotations];
        
        // 同时更新AI标注结果存储（用新对象替换以触发响应式，切换图片时能正确显示）
        if (currentImageIndex.value >= 0) {
          imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...processedAnnotations] };
        }
        
        ElMessage.success(`标注完成！检测到 ${annotations.length} 个对象`);
        
        // 清除之前的标注图片URL
        annotatedImageUrl.value = '';
        
        // 如果后端返回了标注后的图片，则更新URL
        if (response.data.annotated_image) {
          annotatedImageUrl.value = response.data.annotated_image;
        }
      } catch (formatError) {
        console.error('处理标注数据时出错:', formatError);
        ElMessage.error('处理标注数据时出错: ' + formatError.message);
      }
    } else {
      currentAnnotations.value = [];
      // 同时清除AI标注结果存储
      if (currentImageIndex.value >= 0) {
        imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [] };
      }
      ElMessage.info('未能检测到任何对象');
    }
  } catch (error) {
    ElMessage.error('标注失败: ' + (error.response?.data?.detail || error.message));
    console.error('Annotation error:', error);
  } finally {
    isAutoAnnotating.value = false;
  }
};

// 通过加载图片获取真实宽高（用于导出 COCO/VOC/DOTA 等需要像素尺寸的格式）
const getImageDimensions = (url) => {
  return new Promise((resolve) => {
    if (!url) {
      resolve({ width: 0, height: 0 });
      return;
    }
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth || 0, height: img.naturalHeight || 0 });
    img.onerror = () => resolve({ width: 0, height: 0 });
    img.src = url;
  });
};

// 导出标注结果
const exportAnnotations = async () => {
  if (currentAnnotations.value.length === 0) {
    ElMessage.warning('没有可导出的标注结果');
    return;
  }
  
  const { width, height } = await getImageDimensions(currentImage.value?.url);
  const exportData = {
    image: currentImage.value?.name,
    annotations: currentAnnotations.value,
    tool: selectedTool.value,
    width,
    height
  };
  
  const { content, mimeType, extension } = exportAnnotationData(exportData, exportFormat.value);
  const exportFileName = `${currentImage.value?.name.split('.')[0]}_annotations.${extension}`;
  
  // 检查浏览器是否支持File System Access API
  if (window.showSaveFilePicker) {
    try {
      // 让用户选择保存位置
      const handle = await window.showSaveFilePicker({
        suggestedName: exportFileName,
        types: [{
          description: `${exportFormat.value.toUpperCase()} File`,
          accept: {
            [mimeType]: [`.${extension}`]
          }
        }]
      });
      
      // 创建文件并写入内容
      const writable = await handle.createWritable();
      await writable.write(content);
      await writable.close();
      
      ElMessage.success(`标注结果已导出为${exportFormat.value.toUpperCase()}格式`);
        
        // 保存导出路径
        userConfig.value.lastExportPath = handle.name;
        saveUserConfig(userConfig.value);
    } catch (error) {
      // 检查是否是用户取消了保存操作
      if (error.name === 'AbortError' || error.message.includes('cancel')) {
        console.log('用户取消了保存操作');
        return; // 用户取消操作，直接返回
      }
      
      // 如果是其他错误，使用传统的下载方式
      console.log('使用传统下载方式:', error);
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', url);
      linkElement.setAttribute('download', exportFileName);
      linkElement.click();
      URL.revokeObjectURL(url);
      
      ElMessage.success(`标注结果已导出为${exportFormat.value.toUpperCase()}格式`);
    }
  } else {
    // 如果浏览器不支持File System Access API，使用传统的下载方式
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', url);
    linkElement.setAttribute('download', exportFileName);
    linkElement.click();
    URL.revokeObjectURL(url);
    
    ElMessage.success(`标注结果已导出为${exportFormat.value.toUpperCase()}格式`);
  }
};

// 批量导出标注结果
const batchExportAnnotations = async (selectedIndices) => {
  // 如果没有提供索引，则使用所有有标注的图片
  const indicesToExport = selectedIndices || 
    Object.keys(imageAnnotations.value).map(key => parseInt(key));
  
  if (indicesToExport.length === 0) {
    ElMessage.warning('没有选择要导出的图片');
    return;
  }
  
  // 保存当前图片的标注结果
  if (currentImageIndex.value >= 0 && currentAnnotations.value.length > 0) {
    imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...currentAnnotations.value] };
  }
  
  // 计算有标注的图片数量
  const annotatedImages = indicesToExport.filter(index => 
    imageAnnotations.value[index] && imageAnnotations.value[index].length > 0
  );
  
  if (annotatedImages.length === 0) {
    ElMessage.warning('选中的图片中没有标注结果可导出');
    return;
  }
  
  // 创建一个ZIP文件
  const JSZip = (await import('jszip')).default;
  const zip = new JSZip();
  
  // 1. 收集全局类别 (这对 YOLO 和 YAML 导出至关重要，确保 ID 一致)
  const allCategories = new Set();
  annotatedImages.forEach(index => {
    if (imageAnnotations.value[index]) {
      imageAnnotations.value[index].forEach(annotation => {
        if (annotation.label) {
            // 修复逻辑：移除标签中的置信度信息 (如 "person (0.95)" -> "person")
            // 假设格式为 "label (conf)"，我们需要提取 "label"
            let cleanLabel = annotation.label;
            const match = cleanLabel.match(/^(.+)\s\(\d+(\.\d+)?\)$/);
            if (match) {
                cleanLabel = match[1];
            }
            allCategories.add(cleanLabel);
        }
      });
    }
  });
  const globalCategoriesList = Array.from(allCategories).sort(); // 排序以保证 ID 稳定
  
  if (exportFormat.value === 'yolo') {
    zip.file('classes.txt', globalCategoriesList.join('\n'));
  }

  // 2. 如果是 YAML 导出，生成数据集配置 (dataset.yaml)
  if (exportFormat.value === 'yaml') {
      // 这里的逻辑需要修正：不再为每张图生成独立的yaml，而是只生成一个 dataset.yaml
      // 以及对应的 label txt 文件
      const yamlContent = generateDatasetYAML(globalCategoriesList);
      zip.file('dataset.yaml', yamlContent);
      
      // 生成 label txt 文件
      // 我们需要简单地划分 train/val，或者默认全部放在 train，
      // 但为了用户体验，我们应该生成对应的目录结构。
      // 简单策略：前80%作为train，后20%作为val
      const splitIndex = Math.floor(annotatedImages.length * 0.8);
      
      annotatedImages.forEach((index, i) => {
        const image = uploadedImages.value[index];
        if (!image) return;
        
        // 决定是 train 还是 val
        const split = i < splitIndex ? 'train' : 'val';
        
        // 构造导出数据...
        // 这里需要重新获取尺寸等，稍微重构一下循环体
      });

      for (let i = 0; i < annotatedImages.length; i++) {
        const index = annotatedImages[i];
        const image = uploadedImages.value[index];
        if (!image) continue;
        
        let width = 0, height = 0;
        try {
            // 这里可能无法获取所有图片的尺寸，如果图片未加载
            // 但 exportAnnotationData 需要 width/height 吗？对于 YOLO 格式，不需要 (它使用相对坐标)
            // 只有当内部 bbox 是绝对像素时才需要，但我们的内部 bbox 是百分比
            // 所以 width/height 可以传 0 或任意值，只要 percentBboxToPixel 不被错误调用
            // 实际上 convertToYOLO 只需要百分比，不需要像素尺寸
        } catch (e) {}

        const exportData = {
          image: image.name,
          annotations: imageAnnotations.value[index].map(ann => {
              // 清洗标签
              let cleanLabel = ann.label;
              if (cleanLabel) {
                  const match = cleanLabel.match(/^(.+)\s\(\d+(\.\d+)?\)$/);
                  if (match) {
                      cleanLabel = match[1];
                  }
              }
              return { ...ann, label: cleanLabel };
          }),
          tool: selectedTool.value,
          width: 100, // 传假值即可，百分比转换不需要真实尺寸
          height: 100
        };
        
        // 转换为 YOLO 格式内容
        const { content } = exportAnnotationData(exportData, 'yolo', globalCategoriesList);
        
        // 决定分组：前80% train，后20% val
        const split = i < Math.floor(annotatedImages.length * 0.8) ? 'train' : 'val';
        
        // 保存路径：labels/{split}/xxx.txt
        zip.file(`labels/${split}/${image.name.split('.')[0]}.txt`, content);
        
        // 同时在 images 目录下生成对应的空文件占位，或者说明文件
        // 实际上用户需要手动把图片分到 images/train 和 images/val
        // 我们生成一个辅助脚本或列表文件可能更好？
        // 暂时只生成 labels 结构
      }
      
      // 提示用户
      zip.file('images/train/README.txt', 'Please put the first 80% of your images here.');
      zip.file('images/val/README.txt', 'Please put the last 20% of your images here.');
      
  } else {
    // 其他格式保持原样 (如 json, xml 等还是单独文件)
    if (exportFormat.value === 'yolo') {
        zip.file('classes.txt', globalCategoriesList.join('\n'));
    }
    
    for (const index of annotatedImages) {
        const image = uploadedImages.value[index];
        if (!image) continue;
        
        let width = 0, height = 0;
        try {
            const dims = await getImageDimensions(image.url);
            width = dims.width;
            height = dims.height;
        } catch (e) {}

        const exportData = {
          image: image.name,
          annotations: imageAnnotations.value[index].map(ann => {
              // 同样需要清洗每个标注的 label，以便与全局列表匹配
              let cleanLabel = ann.label;
              if (cleanLabel) {
                  const match = cleanLabel.match(/^(.+)\s\(\d+(\.\d+)?\)$/);
                  if (match) {
                      cleanLabel = match[1];
                  }
              }
              return { ...ann, label: cleanLabel };
          }),
          tool: selectedTool.value,
          width,
          height
        };
        
        const { content, extension } = exportAnnotationData(exportData, exportFormat.value, globalCategoriesList);
        const fileName = `${image.name.split('.')[0]}_annotations.${extension}`;
        zip.file(fileName, content);
    }
  }
  
  // 生成ZIP文件
  zip.generateAsync({ type: 'blob' }).then(async (content) => {
    const zipFileName = `batch_annotations_${exportFormat.value}.zip`;
    
    // 检查浏览器是否支持File System Access API
    if (window.showSaveFilePicker) {
      try {
        // 让用户选择保存位置
        const handle = await window.showSaveFilePicker({
          suggestedName: zipFileName,
          types: [{
            description: 'ZIP File',
            accept: {
              'application/zip': ['.zip']
            }
          }]
        });
        
        // 创建文件并写入内容
        const writable = await handle.createWritable();
        await writable.write(content);
        await writable.close();
        
        ElMessage.success(`成功导出 ${annotatedImages.length} 个${exportFormat.value.toUpperCase()}格式的标注结果`);
        
        // 保存导出路径
        userConfig.value.lastExportPath = handle.name;
        saveUserConfig(userConfig.value);
      } catch (error) {
        // 检查是否是用户取消了保存操作
        if (error.name === 'AbortError' || error.message.includes('cancel')) {
          console.log('用户取消了保存操作');
          return; // 用户取消操作，直接返回
        }
        
        // 如果是其他错误，使用传统的下载方式
        console.log('使用传统下载方式:', error);
        const url = URL.createObjectURL(content);
        const link = document.createElement('a');
        link.href = url;
        link.download = zipFileName;
        link.click();
        
        // 释放URL
        setTimeout(() => URL.revokeObjectURL(url), 100);
        
        ElMessage.success(`成功导出 ${annotatedImages.length} 个${exportFormat.value.toUpperCase()}格式的标注结果`);
      }
    } else {
      // 如果浏览器不支持File System Access API，使用传统的下载方式
      const url = URL.createObjectURL(content);
      const link = document.createElement('a');
      link.href = url;
      link.download = zipFileName;
      link.click();
      
      // 释放URL
      setTimeout(() => URL.revokeObjectURL(url), 100);
      
      ElMessage.success(`成功导出 ${annotatedImages.length} 个${exportFormat.value.toUpperCase()}格式的标注结果`);
    }
  }).catch(error => {
    console.error('创建ZIP文件失败:', error);
    ElMessage.error('导出失败: ' + error.message);
  });
};

// 文件上传处理
const handleFileChange = async (file) => {
  // 检查文件类型
  if (!file.raw.type.startsWith('image/')) {
    ElMessage.error('只能上传图片文件!');
    return;
  }
  
  // 创建文件URL
  const fileURL = URL.createObjectURL(file.raw);
  
  // 添加到图片列表
  uploadedImages.value.push({
    file: file.raw,
    name: file.name,
    url: fileURL
  });
  
  // 初始化该图片的标注数组
  const newIndex = uploadedImages.value.length - 1;
  imageAnnotations.value = { ...imageAnnotations.value, [newIndex]: [] };
  
  // 如果是第一张图片，自动选中；不自动从后端拉取标注，避免新图显示旧会话的标注
  if (uploadedImages.value.length === 1) {
    currentImageIndex.value = 0;
    currentImageFile.value = file.raw;
    currentAnnotations.value = [];
  }
  
  ElMessage.success(`成功上传图片: ${file.name}`);
};

// 标注文件导入处理
const handleAnnotationImport = async (file) => {
  // 保存导入路径
  if (file.raw) {
    userConfig.value.lastImportPath = file.raw.name;
    saveUserConfig(userConfig.value);
  }
  try {
    const fileExtension = file.raw.name.split('.').pop().toLowerCase();
    const reader = new FileReader();
    
    reader.onload = async (e) => {
      try {
        let annotations = [];
        const content = e.target.result;
        
        // 根据文件类型解析标注数据
        if (fileExtension === 'json') {
          const parsedData = JSON.parse(content);
          
          // 检查是否是用户提供的特定格式（包含image、annotations和tool字段）
          if (parsedData.annotations && Array.isArray(parsedData.annotations)) {
            annotations = parsedData.annotations.map((ann, index) => {
              // 处理用户特定格式的标注数据（rectanglelabels类型）
              if (ann.type === 'rectanglelabels' && ann.value) {
                return {
                  id: `imported-${index}`,
                  type: 'bbox',
                  label: ann.value.rectanglelabels ? ann.value.rectanglelabels[0] : 'unknown',
                  bbox: {
                    x: parseFloat(ann.value.x || 0),
                    y: parseFloat(ann.value.y || 0),
                    width: parseFloat(ann.value.width || 0),
                    height: parseFloat(ann.value.height || 0)
                  },
                  confidence: 1.0
                };
              }
              // 处理系统导出格式的标注数据（已包含bbox对象）
              else if (ann.type === 'bbox' && ann.bbox) {
                return {
                  id: ann.id || `imported-${index}`,
                  type: 'bbox',
                  label: ann.label || 'unknown',
                  bbox: {
                    x: parseFloat(ann.bbox.x || 0),
                    y: parseFloat(ann.bbox.y || 0),
                    width: parseFloat(ann.bbox.width || 0),
                    height: parseFloat(ann.bbox.height || 0)
                  },
                  confidence: parseFloat(ann.confidence || 1.0)
                };
              }
              return ann;
            });
          }
          // 检查是否是COCO格式
          else if (parsedData.images && parsedData.annotations) {
            // 尝试获取当前图片的ID（假设是第一个图片）
            const currentImage = parsedData.images[0];
            if (currentImage) {
              // 查找当前图片的标注
              const imageId = currentImage.id;
              const imageAnnotations = parsedData.annotations.filter(ann => ann.image_id === imageId);
              
              // 处理COCO格式的标注
              annotations = imageAnnotations.map((ann, index) => {
                // 获取类别名称
                let label = 'unknown';
                if (parsedData.categories) {
                  const category = parsedData.categories.find(cat => cat.id === ann.category_id);
                  label = category ? category.name : `class_${ann.category_id}`;
                }
                
                return {
                  id: `imported-${index}`,
                  type: 'bbox',
                  label: label,
                  bbox: {
                    // COCO格式: [x, y, width, height]（像素坐标）
                    x: ann.bbox[0],
                    y: ann.bbox[1],
                    width: ann.bbox[2],
                    height: ann.bbox[3]
                  },
                  confidence: ann.score || 1.0
                };
              });
            }
          }
          // 检查是否是YOLO JSON格式
          else if (Array.isArray(parsedData) && parsedData.length > 0 && parsedData[0].bbox) {
            annotations = parsedData.map((ann, index) => ({
              id: `imported-${index}`,
              type: 'bbox',
              label: ann.name || ann.class || `class_${ann.class_id || index}`,
              bbox: {
                x: parseFloat(ann.bbox[0] || 0),
                y: parseFloat(ann.bbox[1] || 0),
                width: parseFloat(ann.bbox[2] || 0),
                height: parseFloat(ann.bbox[3] || 0)
              },
              confidence: ann.confidence || ann.score || 1.0
            }));
          }
          // 其他JSON格式
          else {
            annotations = parsedData.annotations || [];
          }
        } else if (fileExtension === 'txt' || fileExtension === 'csv') {
          const lines = content.split('\n').filter(line => line.trim() && !line.startsWith('#'));
          
          if (lines.length > 0) {
            // 尝试检测格式类型
            const firstLine = lines[0].trim();
            
            // 检测YOLO格式（使用空格分隔，通常第一列为类别ID）
            if (firstLine.split(/\s+/).length >= 5) {
              // 尝试获取图片尺寸（如果有）
              let imgWidth = 1000; // 默认值
              let imgHeight = 1000; // 默认值
              
              if (currentImageIndex.value >= 0 && uploadedImages.value[currentImageIndex.value]) {
                const img = new Image();
                img.src = uploadedImages.value[currentImageIndex.value].url;
                if (img.complete) {
                  imgWidth = img.width;
                  imgHeight = img.height;
                }
              }
              
              // 处理YOLO格式标注
              annotations = lines.map((line, index) => {
                const values = line.trim().split(/\s+/).map(v => parseFloat(v));
                if (values.length >= 5) {
                  // YOLO格式: class_id center_x center_y width height（归一化坐标）
                  const classId = values[0];
                  const centerX = values[1] * 100; // 转换为百分比
                  const centerY = values[2] * 100;
                  const width = values[3] * 100;
                  const height = values[4] * 100;
                  
                  // 转换为左上角坐标
                  return {
                    id: `imported-${index}`,
                    type: 'bbox',
                    label: `class_${classId}`,
                    bbox: {
                      x: centerX - (width / 2),
                      y: centerY - (height / 2),
                      width: width,
                      height: height
                    },
                    confidence: values[5] || 1.0
                  };
                }
                return null;
              }).filter(Boolean);
            }
            // 检测CSV格式（使用逗号分隔）
            else if (firstLine.split(',').length >= 5) {
              // 第一行是表头
              const headers = firstLine.split(',').map(h => h.trim().toLowerCase());
              
              for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim());
                if (values.length >= 5) {
                  // 尝试根据表头确定字段位置
                  let labelIndex = headers.indexOf('label') !== -1 ? headers.indexOf('label') : 
                                  headers.indexOf('class') !== -1 ? headers.indexOf('class') : 0;
                  let xIndex = headers.indexOf('x') !== -1 ? headers.indexOf('x') : 
                              headers.indexOf('xmin') !== -1 ? headers.indexOf('xmin') : 1;
                  let yIndex = headers.indexOf('y') !== -1 ? headers.indexOf('y') : 
                              headers.indexOf('ymin') !== -1 ? headers.indexOf('ymin') : 2;
                  let widthIndex = headers.indexOf('width') !== -1 ? headers.indexOf('width') : 
                                  headers.indexOf('xmax') !== -1 ? headers.indexOf('xmax') : 3;
                  let heightIndex = headers.indexOf('height') !== -1 ? headers.indexOf('height') : 
                                   headers.indexOf('ymax') !== -1 ? headers.indexOf('ymax') : 4;
                  
                  let x = parseFloat(values[xIndex]);
                  let y = parseFloat(values[yIndex]);
                  let width = parseFloat(values[widthIndex]);
                  let height = parseFloat(values[heightIndex]);
                  
                  // 处理xmax/ymax格式（转换为width/height）
                  if (headers.indexOf('xmax') !== -1 && headers.indexOf('ymax') !== -1) {
                    width = width - x;
                    height = height - y;
                  }
                  
                  annotations.push({
                    id: `imported-${i}`,
                    type: 'bbox',
                    label: values[labelIndex] || `class_${i}`,
                    bbox: {
                      x: x,
                      y: y,
                      width: width,
                      height: height
                    },
                    confidence: 1.0
                  });
                }
              }
            }
          }
        } else if (fileExtension === 'xml') {
          // 简单的XML解析，处理Pascal VOC格式
          const parser = new DOMParser();
          const xmlDoc = parser.parseFromString(content, 'text/xml');
          
          // 处理Pascal VOC格式
          const objects = xmlDoc.getElementsByTagName('object');
          for (let i = 0; i < objects.length; i++) {
            const obj = objects[i];
            const label = obj.getElementsByTagName('name')[0]?.textContent;
            const bndbox = obj.getElementsByTagName('bndbox')[0];
            
            if (label && bndbox) {
              const xmin = parseFloat(bndbox.getElementsByTagName('xmin')[0]?.textContent);
              const ymin = parseFloat(bndbox.getElementsByTagName('ymin')[0]?.textContent);
              const xmax = parseFloat(bndbox.getElementsByTagName('xmax')[0]?.textContent);
              const ymax = parseFloat(bndbox.getElementsByTagName('ymax')[0]?.textContent);
              
              annotations.push({
                id: `imported-${i}`,
                type: 'bbox',
                label: label,
                bbox: {
                  x: xmin,
                  y: ymin,
                  width: xmax - xmin,
                  height: ymax - ymin
                },
                confidence: 1.0
              });
            }
          }
          
          // 如果没有找到Pascal VOC格式的标注，尝试其他XML格式
          if (annotations.length === 0) {
            const annotationsElements = xmlDoc.getElementsByTagName('annotation');
            for (let i = 0; i < annotationsElements.length; i++) {
              const ann = annotationsElements[i];
              const label = ann.getAttribute('label') || ann.getAttribute('class') || `class_${i}`;
              const x = parseFloat(ann.getAttribute('x') || 0);
              const y = parseFloat(ann.getAttribute('y') || 0);
              const width = parseFloat(ann.getAttribute('width') || 0);
              const height = parseFloat(ann.getAttribute('height') || 0);
              
              if (width > 0 && height > 0) {
                annotations.push({
                  id: `imported-${i}`,
                  type: 'bbox',
                  label: label,
                  bbox: {
                    x: x,
                    y: y,
                    width: width,
                    height: height
                  },
                  confidence: parseFloat(ann.getAttribute('confidence') || 1.0)
                });
              }
            }
          }
        }
        
        // 确保标注数据格式正确
        const processedAnnotations = annotations.map(ann => {
          // 创建新对象而不是修改原对象
          const newAnn = { ...ann };
          
          // 标准化标注数据格式
          if (newAnn.type === undefined) {
            newAnn.type = 'bbox';
          }
          
          // 确保bbox对象格式正确
          if (newAnn.bbox && typeof newAnn.bbox === 'object' && !Array.isArray(newAnn.bbox)) {
            // 确保bbox对象的坐标值为数字
            const bbox = {
              x: parseFloat(newAnn.bbox.x || 0),
              y: parseFloat(newAnn.bbox.y || 0),
              width: parseFloat(newAnn.bbox.width || 0),
              height: parseFloat(newAnn.bbox.height || 0)
            };
            
            // 检查是否需要将像素坐标转换为百分比坐标
            // 如果坐标值看起来像像素坐标（大于100），则转换为百分比
            if (bbox.x > 100 || bbox.y > 100 || bbox.width > 100 || bbox.height > 100) {
              // 尝试获取当前图片的实际尺寸
              let imgWidth = 1000; // 默认值
              let imgHeight = 1000; // 默认值
              
              // 如果当前有选中的图片，尝试获取其实际尺寸
              if (currentImageIndex.value >= 0 && uploadedImages.value[currentImageIndex.value]) {
                const img = new Image();
                img.src = uploadedImages.value[currentImageIndex.value].url;
                
                // 如果图片已经加载完成，使用实际尺寸
                if (img.complete) {
                  imgWidth = img.width;
                  imgHeight = img.height;
                } else {
                  // 否则使用默认尺寸，但记录日志
                  console.warn('图片尚未完全加载，使用默认尺寸进行坐标转换');
                }
              }
              
              console.log(`使用图片尺寸 ${imgWidth}x${imgHeight} 进行坐标转换`);
              
              // 转换为百分比坐标
              newAnn.bbox = {
                x: (bbox.x / imgWidth) * 100,
                y: (bbox.y / imgHeight) * 100,
                width: (bbox.width / imgWidth) * 100,
                height: (bbox.height / imgHeight) * 100
              };
              
              console.log(`坐标转换前: x=${bbox.x}, y=${bbox.y}, width=${bbox.width}, height=${bbox.height}`);
              console.log(`坐标转换后: x=${newAnn.bbox.x}, y=${newAnn.bbox.y}, width=${newAnn.bbox.width}, height=${newAnn.bbox.height}`);
            } else {
              // 已经是百分比坐标或小数值，直接使用
              newAnn.bbox = bbox;
            }
          } else if (Array.isArray(newAnn.bbox)) {
            // 处理数组格式的bbox
            const bboxArray = newAnn.bbox.map(val => parseFloat(val || 0));
            
            // 检查是否需要转换为百分比坐标
            if (bboxArray.some(val => val > 100)) {
              // 尝试获取当前图片的实际尺寸
              let imgWidth = 1000; // 默认值
              let imgHeight = 1000; // 默认值
              
              // 如果当前有选中的图片，尝试获取其实际尺寸
              if (currentImageIndex.value >= 0 && uploadedImages.value[currentImageIndex.value]) {
                const img = new Image();
                img.src = uploadedImages.value[currentImageIndex.value].url;
                
                // 如果图片已经加载完成，使用实际尺寸
                if (img.complete) {
                  imgWidth = img.width;
                  imgHeight = img.height;
                }
              }
              
              console.log(`使用图片尺寸 ${imgWidth}x${imgHeight} 进行数组格式坐标转换`);
              
              // 处理COCO格式的bbox [x, y, width, height]
              if (bboxArray.length === 4) {
                newAnn.bbox = {
                  x: (bboxArray[0] / imgWidth) * 100,
                  y: (bboxArray[1] / imgHeight) * 100,
                  width: (bboxArray[2] / imgWidth) * 100,
                  height: (bboxArray[3] / imgHeight) * 100
                };
              }
            } else if (bboxArray.length === 4) {
              // 已经是百分比坐标的数组格式，转换为对象格式
              newAnn.bbox = {
                x: bboxArray[0],
                y: bboxArray[1],
                width: bboxArray[2],
                height: bboxArray[3]
              };
            }
          }
          
          // 确保标注有ID
          if (!newAnn.id) {
            newAnn.id = `imported-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
          }
          
          // 确保标注有标签
          if (!newAnn.label) {
            newAnn.label = 'unknown';
          }
          
          // 确保有置信度
          if (newAnn.confidence === undefined) {
            newAnn.confidence = 1.0;
          }
          
          return newAnn;
        }).filter(ann => ann && ann.bbox && ann.bbox.width > 0 && ann.bbox.height > 0); // 过滤掉无效标注
        
        // 检查当前是否有选中的图片
        if (currentImageIndex.value >= 0) {
          currentAnnotations.value = [...processedAnnotations];
          imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...processedAnnotations] };
          // 不写入 savedAnnotations，导入的标注需点击「保存当前标注」后才持久化
          ElMessage.success(`成功导入 ${processedAnnotations.length} 个标注，请点击「保存当前标注」后生效`);
        } else {
          ElMessage.warning('请先选择一张图片，然后再导入标注文件');
        }
      } catch (error) {
        console.error('解析标注文件失败:', error);
        ElMessage.error('解析标注文件失败: ' + error.message);
      }
    };
    
    // 读取文件内容
    reader.readAsText(file.raw);
  } catch (error) {
    console.error('导入标注文件失败:', error);
    ElMessage.error('导入标注文件失败: ' + error.message);
  }
};

// 导入图片+标注（同时导入）
const importAnnotatedImages = async () => {
  ElMessage.info('请选择图片文件和对应的标注文件（文件名需匹配）');
  
  try {
    // 检查浏览器是否支持文件系统API（目录选择）
    if (window.showDirectoryPicker) {
      try {
        const dirHandle = await window.showDirectoryPicker({
          mode: 'read',
          startIn: userConfig.value.lastImportPath || 'desktop'
        });
        
        const files = [];
        
        // 递归遍历目录获取所有文件
        async function processDirectory(handle) {
          for await (const entry of handle.values()) {
            if (entry.kind === 'file') {
              const file = await entry.getFile();
              // 只处理图片和标注文件
              if (file.type.startsWith('image/') || ['.json', '.txt', '.xml', '.csv'].some(ext => entry.name.endsWith(ext))) {
                files.push(file);
              }
            } else if (entry.kind === 'directory') {
              await processDirectory(entry);
            }
          }
        }
        
        await processDirectory(dirHandle);
        
        // 保存导入路径
        userConfig.value.lastImportPath = dirHandle.name;
        saveUserConfig(userConfig.value);
        
        if (files.length > 0) {
          // 使用传统的文件输入方式处理文件
          const fileInput = document.createElement('input');
          fileInput.type = 'file';
          fileInput.multiple = true;
          fileInput.accept = 'image/*,.json,.txt,.xml,.csv';
          
          // 创建FileList模拟对象
          const fileList = {
            length: files.length,
            [Symbol.iterator]: function* () {
              for (const file of files) yield file;
            }
          };
          
          // 添加索引访问
          files.forEach((file, index) => {
            fileList[index] = file;
          });
          
          // 创建模拟事件对象
          const event = { target: { files: fileList } };
          
          // 手动处理文件
          await processImportedFiles(event);
          return;
        } else {
          ElMessage.warning('选择的目录中没有找到图片或标注文件');
          return;
        }
      } catch (error) {
        console.log('使用传统文件选择方式:', error);
        // 继续使用传统方式
      }
    }
  } catch (error) {
    console.error('导入图片和标注失败:', error);
    ElMessage.error('导入图片和标注失败: ' + error.message);
  }
    
    // 创建一个隐藏的文件输入
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.accept = 'image/*,.json,.txt,.xml,.csv'; // 添加CSV支持
  
  fileInput.onchange = async (event) => {
    const files = event.target.files;
    if (files.length === 0) return;
    
    console.log('=== 开始批量导入图片和标注 ===');
    console.log('选择的文件数量:', files.length);
    console.log('所有选择的文件:', Array.from(files).map(f => ({ name: f.name, type: f.type })));
    
    // 保存原始导入前的状态，用于调试
    console.log('导入前的状态:');
    console.log('uploadedImages长度:', uploadedImages.value.length);
    console.log('currentImageIndex:', currentImageIndex.value);
    console.log('currentAnnotations长度:', currentAnnotations.value.length);
    console.log('imageAnnotations键值对:', Object.keys(imageAnnotations.value).map(key => ({ 
      index: key, 
      length: imageAnnotations.value[key]?.length || 0 
    })));
    console.log('savedAnnotations键值对:', Object.keys(savedAnnotations.value).map(key => ({ 
      index: key, 
      length: savedAnnotations.value[key]?.length || 0 
    })));
    
    // 分离图片文件和标注文件
    const imageFiles = [];
    const annotationFiles = {}; // 按图片名存储标注文件
    
    console.log('\n=== 开始分离文件 ===');
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileName = file.name;
      const fileExtension = fileName.split('.').pop().toLowerCase();
      
      console.log(`文件 ${i}:`, {
        name: fileName,
        type: file.type,
        extension: fileExtension
      });
      
      if (file.type.startsWith('image/')) {
        imageFiles.push(file);
        console.log(`  → 识别为图片文件`);
      } else if (['json', 'txt', 'xml', 'csv'].includes(fileExtension)) {
        // 标注文件，使用不带扩展名的文件名作为键（转小写以支持大小写不敏感匹配）
        const baseName = fileName.substring(0, fileName.lastIndexOf('.')).toLowerCase();
        annotationFiles[baseName] = file;
        console.log(`  → 识别为标注文件，基名(小写): "${baseName}"`);
        
        // 额外添加标注文件的可能匹配键，以增强匹配能力
        // 例如：对于0_annotations.json，也添加0_annotations作为键
        if (baseName.includes('_annotations')) {
          // 提取图片部分的基名（去掉_annotations后缀）
          const imagePartBaseName = baseName.replace('_annotations', '');
          annotationFiles[`${imagePartBaseName}_annotations`] = file;
          console.log(`  → 添加额外匹配键: "${imagePartBaseName}_annotations"`);
        }
      } else {
        console.log(`  → 未知文件类型，忽略`);
      }
    }
    
    console.log('\n=== 文件分离结果 ===');
    console.log('图片文件数量:', imageFiles.length);
    console.log('图片文件列表:', imageFiles.map(f => f.name));
    console.log('标注文件数量:', Object.keys(annotationFiles).length);
    console.log('标注文件映射:');
    Object.keys(annotationFiles).forEach(key => {
      console.log(`  "${key}" → ${annotationFiles[key].name}`);
    });
    
    if (imageFiles.length === 0) {
      ElMessage.warning('请至少选择一张图片');
      return;
    }
    
    // 处理图片和标注
    let importedImages = 0;
    let totalAnnotations = 0;
    
    console.log('\n=== 开始处理图片和标注 ===');
    
    for (const imageFile of imageFiles) {
      try {
        console.log('\n' + '='.repeat(60));
        console.log(`=== 处理图片: ${imageFile.name} ===`);
        console.log('='.repeat(60));
        
        // 创建图片URL
        const fileURL = URL.createObjectURL(imageFile);
        console.log('图片URL创建成功:', fileURL);
        
        // 添加到图片列表
        const newIndex = uploadedImages.value.length;
        console.log('新图片索引:', newIndex);
        
        // 记录当前数组状态
        console.log('添加图片前，uploadedImages长度:', uploadedImages.value.length);
        
        uploadedImages.value.push({
          file: imageFile,
          name: imageFile.name,
          url: fileURL
        });
        
        console.log('添加图片后，uploadedImages长度:', uploadedImages.value.length);
        console.log('最新的uploadedImages:', uploadedImages.value[uploadedImages.value.length - 1]);
        
        // 初始化标注数组（用新对象替换以触发响应式）
        imageAnnotations.value = { ...imageAnnotations.value, [newIndex]: [] };
        savedAnnotations.value = { ...savedAnnotations.value, [newIndex]: [] };
        
        console.log('初始化标注数组:');
        console.log('imageAnnotations[', newIndex, ']:', imageAnnotations.value[newIndex]);
        console.log('savedAnnotations[', newIndex, ']:', savedAnnotations.value[newIndex]);
        
        // 查找对应的标注文件（使用小写基名进行大小写不敏感匹配）
        const baseName = imageFile.name.substring(0, imageFile.name.lastIndexOf('.')).toLowerCase();
        console.log('查找标注文件，图片基名(小写):', `"${baseName}"`);
        console.log('可用的标注文件基名:', Object.keys(annotationFiles));
        
        // 尝试多种匹配模式，增强匹配能力：
        // 1. 完全匹配：图片基名直接匹配标注文件基名
        // 2. annotations后缀匹配：图片基名 + "_annotations" 匹配标注文件基名
        // 3. 文件名前缀匹配：处理类似0.jpg和0_annotations.json的情况
        let annotationFile = annotationFiles[baseName];
        
        if (!annotationFile) {
          // 尝试查找 {图片名}_annotations 模式的标注文件
          const annotationsBaseName = `${baseName}_annotations`;
          console.log('尝试查找标注文件，图片基名+_annotations(小写):', `"${annotationsBaseName}"`);
          annotationFile = annotationFiles[annotationsBaseName];
        }
        
        if (!annotationFile) {
          // 尝试更宽松的匹配：查找包含图片基名的标注文件
          const matchingKeys = Object.keys(annotationFiles).filter(key => 
            key.includes(baseName) || key.replace('_annotations', '') === baseName
          );
          
          if (matchingKeys.length > 0) {
            // 优先选择最短的匹配（最精确的匹配）
            const bestMatchKey = matchingKeys.sort((a, b) => a.length - b.length)[0];
            annotationFile = annotationFiles[bestMatchKey];
            console.log('宽松匹配找到标注文件，键:', bestMatchKey, '，文件名:', annotationFile.name);
          }
        }
        
        console.log('找到匹配的标注文件:', annotationFile ? annotationFile.name : '无');
        
        if (annotationFile) {
          console.log('✅ 找到匹配的标注文件:', annotationFile.name);
          
          // 读取并解析标注文件
          console.log('\n=== 开始解析标注文件 ===');
          const annotations = await parseAnnotationFile(annotationFile);
          console.log('\n=== 标注文件解析完成 ===');
          console.log('解析的标注数量:', annotations.length);
          console.log('解析的标注数据:', annotations);
          
          if (annotations.length > 0) {
            console.log('\n=== 应用标注数据 ===');
            
            // 保存标注到状态变量
            console.log('设置标注到状态变量，图片索引:', newIndex);
            
            imageAnnotations.value = { ...imageAnnotations.value, [newIndex]: [...annotations] };
            // 不写入 savedAnnotations，批量导入的标注需用户点击「保存当前标注」后才持久化
            console.log('状态变量更新后:');
            console.log('imageAnnotations[', newIndex, ']长度:', imageAnnotations.value[newIndex]?.length || 0);
            console.log('savedAnnotations[', newIndex, ']长度:', savedAnnotations.value[newIndex]?.length || 0);
            console.log('imageAnnotations[', newIndex, ']:', imageAnnotations.value[newIndex]);
            console.log('savedAnnotations[', newIndex, ']:', savedAnnotations.value[newIndex]);
            
            // 如果是当前显示的图片，也更新currentAnnotations
            if (newIndex === currentImageIndex.value) {
              console.log('🔄 当前显示的图片，更新currentAnnotations');
              currentAnnotations.value = [...annotations];
              console.log('currentAnnotations更新后长度:', currentAnnotations.value.length);
              console.log('currentAnnotations内容:', currentAnnotations.value);
            }
            
            totalAnnotations += annotations.length;
            console.log('累计标注数量:', totalAnnotations);
          } else {
            console.log('⚠️  标注文件解析成功，但没有包含有效的标注数据');
          }
        } else {
          console.log('❌ 未找到匹配的标注文件');
          
          // 检查是否有类似的文件名（用于调试）
          const availableKeys = Object.keys(annotationFiles);
          const similarKeys = availableKeys.filter(key => 
            key.includes(baseName) || baseName.includes(key)
          );
          
          if (similarKeys.length > 0) {
            console.log('ℹ️  发现类似的标注文件名:', similarKeys);
          }
        }
        
        importedImages++;
        console.log('\n✅ 图片处理完成，已导入图片数量:', importedImages);
        
      } catch (error) {
        console.error(`❌ 处理文件 ${imageFile.name} 时出错:`, error);
        console.error('错误堆栈:', error.stack);
        ElMessage.error(`处理文件 ${imageFile.name} 时出错: ${error.message}`);
      }
    }
    
    // 如果导入了图片，选择第一张
    if (importedImages > 0) {
      console.log('\n=== 批量导入完成，设置当前图片 ===');
      console.log('导入的图片数量:', importedImages);
      
      // 记录导入后的状态
       console.log('导入后的状态:');
       console.log('uploadedImages长度:', uploadedImages.value.length);
       console.log('imageAnnotations键值对:', Object.keys(imageAnnotations.value).map(key => ({ 
         index: key, 
         length: imageAnnotations.value[key]?.length || 0 
       })));
       console.log('savedAnnotations键值对:', Object.keys(savedAnnotations.value).map(key => ({ 
         index: key, 
         length: savedAnnotations.value[key]?.length || 0 
       })));
      
      // 设置当前图片为第一张
    currentImageIndex.value = 0;
    if (uploadedImages.value.length > 0) {
      currentImageFile.value = uploadedImages.value[0].file;
    }
    
    console.log('\n=== 设置当前图片为第一张 ===');
    console.log('currentImageIndex设置为:', currentImageIndex.value);
    console.log('当前图片名称:', uploadedImages.value[0]?.name);
    
    // 获取第一张图片的标注数据
    console.log('\n=== 获取第一张图片的标注数据 ===');
    
    // 检查标注数据是否存在（使用对象属性访问）
    const hasSavedAnnotations = savedAnnotations.value[0] && savedAnnotations.value[0].length > 0;
    const hasImageAnnotations = imageAnnotations.value[0] && imageAnnotations.value[0].length > 0;
    
    console.log('savedAnnotations[0]存在且有数据:', hasSavedAnnotations);
    console.log('imageAnnotations[0]存在且有数据:', hasImageAnnotations);
    console.log('savedAnnotations[0]:', savedAnnotations.value[0]);
    console.log('imageAnnotations[0]:', imageAnnotations.value[0]);
    
    // 确保从正确的来源获取标注数据
    const annotationsToUse = hasSavedAnnotations ? savedAnnotations.value[0] : 
                           (hasImageAnnotations ? imageAnnotations.value[0] : []);
                           
    console.log('当前图片索引:', currentImageIndex.value);
    console.log('检查所有可用的标注数据键:', {
      imageAnnotationsKeys: Object.keys(imageAnnotations.value),
      savedAnnotationsKeys: Object.keys(savedAnnotations.value)
    });
      
      console.log('选择的标注来源:', hasSavedAnnotations ? 'savedAnnotations' : (hasImageAnnotations ? 'imageAnnotations' : '空数组'));
      console.log('标注数据长度:', annotationsToUse.length);
      console.log('标注数据内容:', annotationsToUse);
      
      // 更新currentAnnotations
      currentAnnotations.value = [...annotationsToUse];
      
      console.log('\n=== 更新currentAnnotations ===');
      console.log('currentAnnotations更新后长度:', currentAnnotations.value.length);
      console.log('currentAnnotations内容:', currentAnnotations.value);
      
      // 强制触发AnnotationCanvas的重新渲染
      console.log('\n=== 强制触发重新渲染 ===');
      
      // 清除之前的标注图片URL，强制使用原始图片URL
      annotatedImageUrl.value = '';
      console.log('清除annotatedImageUrl以强制使用原始图片URL');
      
      // 触发computed属性的重新计算
      console.log('触发currentImageUrl重新计算:', currentImageUrl.value);
      
      // 仅更新 imageAnnotations（会话内显示）；不写入 savedAnnotations，只有点击「保存当前标注」才写入
      if (currentImageIndex.value >= 0) {
        imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...currentAnnotations.value] };
        console.log('同步更新 imageAnnotations');
      }
      
      // 强制AnnotationCanvas组件重新渲染的备用方案
      // 通过更新数组引用触发watch
      currentAnnotations.value = [...currentAnnotations.value];
      console.log('更新currentAnnotations引用以触发重新渲染');
      
      // 额外的强制渲染机制：短暂延迟后再次更新
      setTimeout(() => {
        console.log('延迟触发第二次重新渲染');
        currentAnnotations.value = [...currentAnnotations.value];
      }, 100);
    }
    
    ElMessage.success(`成功导入 ${importedImages} 张图片，共 ${totalAnnotations} 个标注`);
    
    console.log('\n=== 批量导入操作完全结束 ===');
  };
  
  // 触发文件选择
  fileInput.click();
};

// 解析标注文件
const parseAnnotationFile = (file) => {
  return new Promise((resolve, reject) => {
    try {
      const fileExtension = file.name.split('.').pop().toLowerCase();
      const reader = new FileReader();
      
      console.log('=== 开始解析标注文件 ===');
      console.log('文件名:', file.name);
      console.log('文件类型:', fileExtension);
      
      reader.onload = (e) => {
        try {
          let annotations = [];
          const content = e.target.result;
          
          console.log('文件内容长度:', content.length);
          console.log('文件内容前100字符:', content.substring(0, 100) + '...');
          
          // 根据文件类型解析标注数据
          if (fileExtension === 'json') {
            console.log('解析JSON格式标注文件');
            const parsedData = JSON.parse(content);
            
            // 检查是否是用户提供的特定格式（包含image、annotations和tool字段）
            if (parsedData.annotations && Array.isArray(parsedData.annotations)) {
              console.log('处理用户特定格式的JSON标注数据');
              annotations = parsedData.annotations.map((ann, index) => {
                // 处理用户特定格式的标注数据（rectanglelabels类型）
                if (ann.type === 'rectanglelabels' && ann.value) {
                  return {
                    id: `imported-${index}`,
                    type: 'bbox',
                    label: ann.value.rectanglelabels ? ann.value.rectanglelabels[0] : 'unknown',
                    bbox: {
                      x: parseFloat(ann.value.x || 0),
                      y: parseFloat(ann.value.y || 0),
                      width: parseFloat(ann.value.width || 0),
                      height: parseFloat(ann.value.height || 0)
                    },
                    confidence: 1.0
                  };
                }
                // 处理系统导出格式的标注数据（已包含bbox对象）
                else if (ann.type === 'bbox' && ann.bbox) {
                  return {
                    id: ann.id || `imported-${index}`,
                    type: 'bbox',
                    label: ann.label || 'unknown',
                    bbox: {
                      x: parseFloat(ann.bbox.x || 0),
                      y: parseFloat(ann.bbox.y || 0),
                      width: parseFloat(ann.bbox.width || 0),
                      height: parseFloat(ann.bbox.height || 0)
                    },
                    confidence: parseFloat(ann.confidence || 1.0)
                  };
                }
                return ann;
              });
            }
            // 检查是否是COCO格式
            else if (parsedData.images && parsedData.annotations) {
              console.log('处理COCO格式的JSON标注数据');
              // 尝试获取当前图片的ID（假设是第一个图片）
              const currentImage = parsedData.images[0];
              if (currentImage) {
                // 查找当前图片的标注
                const imageId = currentImage.id;
                const imageAnnotations = parsedData.annotations.filter(ann => ann.image_id === imageId);
                
                // 处理COCO格式的标注
                annotations = imageAnnotations.map((ann, index) => {
                  // 获取类别名称
                  let label = 'unknown';
                  if (parsedData.categories) {
                    const category = parsedData.categories.find(cat => cat.id === ann.category_id);
                    label = category ? category.name : `class_${ann.category_id}`;
                  }
                  
                  return {
                    id: `imported-${index}`,
                    type: 'bbox',
                    label: label,
                    bbox: {
                      // COCO格式: [x, y, width, height]（像素坐标）
                      x: ann.bbox[0],
                      y: ann.bbox[1],
                      width: ann.bbox[2],
                      height: ann.bbox[3]
                    },
                    confidence: ann.score || 1.0
                  };
                });
              }
            }
            // 检查是否是YOLO JSON格式
            else if (Array.isArray(parsedData) && parsedData.length > 0 && parsedData[0].bbox) {
              console.log('处理YOLO JSON格式的标注数据');
              annotations = parsedData.map((ann, index) => ({
                id: `imported-${index}`,
                type: 'bbox',
                label: ann.name || ann.class || `class_${ann.class_id || index}`,
                bbox: {
                  x: parseFloat(ann.bbox[0] || 0),
                  y: parseFloat(ann.bbox[1] || 0),
                  width: parseFloat(ann.bbox[2] || 0),
                  height: parseFloat(ann.bbox[3] || 0)
                },
                confidence: ann.confidence || ann.score || 1.0
              }));
            }
            // 处理其他JSON格式
            else if (Array.isArray(parsedData)) {
              console.log('处理数组格式的JSON标注数据');
              annotations = parsedData;
            } else {
              console.log('处理其他格式的JSON标注数据');
              annotations = [parsedData];
            }
          } else if (fileExtension === 'txt' || fileExtension === 'csv') {
            console.log('解析TXT/CSV格式标注文件');
            const lines = content.split('\n').filter(line => line.trim() && !line.startsWith('#'));
            
            if (lines.length > 0) {
              // 尝试检测格式类型
              const firstLine = lines[0].trim();
              
              // 检测YOLO格式（使用空格分隔，通常第一列为类别ID）
              if (firstLine.split(/\s+/).length >= 5) {
                console.log('处理YOLO格式标注数据');
                // 尝试获取图片尺寸（如果有）
                let imgWidth = 1000; // 默认值
                let imgHeight = 1000; // 默认值
                
                // 处理YOLO格式标注
                annotations = lines.map((line, index) => {
                  const values = line.trim().split(/\s+/).map(v => parseFloat(v));
                  if (values.length >= 5) {
                    // YOLO格式: class_id center_x center_y width height（归一化坐标）
                    const classId = values[0];
                    const centerX = values[1] * 100; // 转换为百分比
                    const centerY = values[2] * 100;
                    const width = values[3] * 100;
                    const height = values[4] * 100;
                    
                    // 转换为左上角坐标
                    return {
                      id: `imported-${index}`,
                      type: 'bbox',
                      label: `class_${classId}`,
                      bbox: {
                        x: centerX - (width / 2),
                        y: centerY - (height / 2),
                        width: width,
                        height: height
                      },
                      confidence: values[5] || 1.0
                    };
                  }
                  return null;
                }).filter(Boolean);
              }
              // 检测CSV格式（使用逗号分隔）
              else if (firstLine.split(',').length >= 5) {
                console.log('处理CSV格式标注数据');
                // 第一行是表头
                const headers = firstLine.split(',').map(h => h.trim().toLowerCase());
                console.log('CSV表头:', headers);
                
                for (let i = 1; i < lines.length; i++) {
                  const values = lines[i].split(',').map(v => v.trim());
                  console.log(`CSV行 ${i}:`, values);
                  
                  if (values.length >= 5) {
                    // 尝试根据表头确定字段位置
                    let labelIndex = headers.indexOf('label') !== -1 ? headers.indexOf('label') : 
                                    headers.indexOf('class') !== -1 ? headers.indexOf('class') : 0;
                    let xIndex = headers.indexOf('x') !== -1 ? headers.indexOf('x') : 
                                headers.indexOf('xmin') !== -1 ? headers.indexOf('xmin') : 1;
                    let yIndex = headers.indexOf('y') !== -1 ? headers.indexOf('y') : 
                                headers.indexOf('ymin') !== -1 ? headers.indexOf('ymin') : 2;
                    let widthIndex = headers.indexOf('width') !== -1 ? headers.indexOf('width') : 
                                    headers.indexOf('xmax') !== -1 ? headers.indexOf('xmax') : 3;
                    let heightIndex = headers.indexOf('height') !== -1 ? headers.indexOf('height') : 
                                     headers.indexOf('ymax') !== -1 ? headers.indexOf('ymax') : 4;
                    
                    let x = parseFloat(values[xIndex]);
                    let y = parseFloat(values[yIndex]);
                    let width = parseFloat(values[widthIndex]);
                    let height = parseFloat(values[heightIndex]);
                    
                    // 处理xmax/ymax格式（转换为width/height）
                    if (headers.indexOf('xmax') !== -1 && headers.indexOf('ymax') !== -1) {
                      width = width - x;
                      height = height - y;
                    }
                    
                    if (!isNaN(x) && !isNaN(y) && !isNaN(width) && !isNaN(height)) {
                      annotations.push({
                        id: `imported-${i}`,
                        type: 'bbox',
                        label: values[labelIndex] || `class_${i}`,
                        bbox: {
                          x: x,
                          y: y,
                          width: width,
                          height: height
                        },
                        confidence: 1.0
                      });
                      console.log(`创建CSV标注 ${i}:`, { label: values[labelIndex] || `class_${i}`, x, y, width, height });
                    }
                  }
                }
              }
            }
          } else if (fileExtension === 'xml') {
            console.log('解析XML格式标注文件');
            // 简单的XML解析，处理Pascal VOC格式
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(content, 'text/xml');
            
            // 处理Pascal VOC格式
            const objects = xmlDoc.getElementsByTagName('object');
            console.log('XML中找到的object元素数量:', objects.length);
            
            for (let i = 0; i < objects.length; i++) {
              const obj = objects[i];
              const label = obj.getElementsByTagName('name')[0]?.textContent;
              const bndbox = obj.getElementsByTagName('bndbox')[0];
              
              if (label && bndbox) {
                const xmin = parseFloat(bndbox.getElementsByTagName('xmin')[0]?.textContent);
                const ymin = parseFloat(bndbox.getElementsByTagName('ymin')[0]?.textContent);
                const xmax = parseFloat(bndbox.getElementsByTagName('xmax')[0]?.textContent);
                const ymax = parseFloat(bndbox.getElementsByTagName('ymax')[0]?.textContent);
                
                if (!isNaN(xmin) && !isNaN(ymin) && !isNaN(xmax) && !isNaN(ymax)) {
                  annotations.push({
                    id: `imported-${i}`,
                    type: 'bbox',
                    label: label,
                    bbox: {
                      x: xmin,
                      y: ymin,
                      width: xmax - xmin,
                      height: ymax - ymin
                    },
                    confidence: 1.0
                  });
                  console.log(`创建XML标注 ${i}:`, { label, xmin, ymin, xmax, ymax });
                }
              }
            }
            
            // 如果没有找到Pascal VOC格式的标注，尝试其他XML格式
            if (annotations.length === 0) {
              console.log('尝试解析其他XML格式标注数据');
              const annotationsElements = xmlDoc.getElementsByTagName('annotation');
              for (let i = 0; i < annotationsElements.length; i++) {
                const ann = annotationsElements[i];
                const label = ann.getAttribute('label') || ann.getAttribute('class') || `class_${i}`;
                const x = parseFloat(ann.getAttribute('x') || 0);
                const y = parseFloat(ann.getAttribute('y') || 0);
                const width = parseFloat(ann.getAttribute('width') || 0);
                const height = parseFloat(ann.getAttribute('height') || 0);
                
                if (width > 0 && height > 0) {
                  annotations.push({
                    id: `imported-${i}`,
                    type: 'bbox',
                    label: label,
                    bbox: {
                      x: x,
                      y: y,
                      width: width,
                      height: height
                    },
                    confidence: parseFloat(ann.getAttribute('confidence') || 1.0)
                  });
                  console.log(`创建通用XML标注 ${i}:`, { label, x, y, width, height });
                }
              }
            }
          }
          
          console.log('解析完成，原始标注数量:', annotations.length);
          console.log('原始标注数据:', annotations);
          
          // 确保标注数据格式正确
          const processedAnnotations = annotations.map(ann => {
            // 创建新对象而不是修改原对象
            const newAnn = { ...ann };
            
            // 标准化标注数据格式
            if (newAnn.type === undefined) {
              newAnn.type = 'bbox';
              console.log('设置默认类型为bbox');
            }
            
            // 确保bbox对象格式正确
            if (newAnn.bbox && typeof newAnn.bbox === 'object' && !Array.isArray(newAnn.bbox)) {
              // 确保bbox对象的坐标值为数字
              const bbox = {
                x: parseFloat(newAnn.bbox.x || 0),
                y: parseFloat(newAnn.bbox.y || 0),
                width: parseFloat(newAnn.bbox.width || 0),
                height: parseFloat(newAnn.bbox.height || 0)
              };
              
              // 检查是否需要将像素坐标转换为百分比坐标
              // 如果坐标值看起来像像素坐标（大于100），则转换为百分比
              if (bbox.x > 100 || bbox.y > 100 || bbox.width > 100 || bbox.height > 100) {
                // 尝试获取当前图片的实际尺寸
                let imgWidth = 1000; // 默认值
                let imgHeight = 1000; // 默认值
                
                // 转换为百分比坐标
                newAnn.bbox = {
                  x: (bbox.x / imgWidth) * 100,
                  y: (bbox.y / imgHeight) * 100,
                  width: (bbox.width / imgWidth) * 100,
                  height: (bbox.height / imgHeight) * 100
                };
              } else {
                newAnn.bbox = bbox;
              }
            } else if (Array.isArray(newAnn.bbox)) {
              // 处理数组格式的bbox
              const bboxArray = newAnn.bbox.map(val => parseFloat(val || 0));
              
              // 检查是否需要转换为百分比坐标
              if (bboxArray.some(val => val > 100)) {
                // 尝试获取当前图片的实际尺寸
                let imgWidth = 1000; // 默认值
                let imgHeight = 1000; // 默认值
                
                // 处理COCO格式的bbox [x, y, width, height]
                if (bboxArray.length === 4) {
                  newAnn.bbox = {
                    x: (bboxArray[0] / imgWidth) * 100,
                    y: (bboxArray[1] / imgHeight) * 100,
                    width: (bboxArray[2] / imgWidth) * 100,
                    height: (bboxArray[3] / imgHeight) * 100
                  };
                }
              } else if (bboxArray.length === 4) {
                // 已经是百分比坐标的数组格式，转换为对象格式
                newAnn.bbox = {
                  x: bboxArray[0],
                  y: bboxArray[1],
                  width: bboxArray[2],
                  height: bboxArray[3]
                };
              }
            }
            
            // 确保标注有ID
            if (!newAnn.id) {
              newAnn.id = `imported-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
            }
            
            // 确保标注有标签
            if (!newAnn.label) {
              newAnn.label = 'unknown';
            }
            
            // 确保有置信度
            if (newAnn.confidence === undefined) {
              newAnn.confidence = 1.0;
            }
            
            return newAnn;
          }).filter(ann => ann && ann.bbox && ann.bbox.width > 0 && ann.bbox.height > 0); // 过滤掉无效标注
          
          console.log('\n=== 标注文件解析完成 ===');
          console.log('处理后标注数量:', processedAnnotations.length);
          console.log('处理后标注数据:', processedAnnotations);
          
          resolve(processedAnnotations);
        } catch (error) {
          console.error('解析标注文件内容时出错:', error);
          reject(error);
        }
      };
      
      reader.onerror = (error) => {
        console.error('读取标注文件时出错:', error);
        reject(new Error('读取文件失败'));
      };
      
      // 读取文件内容
      reader.readAsText(file);
    } catch (error) {
      console.error('解析标注文件时出错:', error);
      reject(error);
    }
  });
};

// 加载已有标注
const loadExistingAnnotations = async (imageIndex) => {
  if (imageIndex < 0 || imageIndex >= uploadedImages.value.length) return;
  
  try {
    const imageName = uploadedImages.value[imageIndex].name;
    const response = await getImageAnnotations(imageName);
    
    if (response.data && response.data.annotations && response.data.annotations.length > 0) {
      // 保存到已保存标注对象
      savedAnnotations.value[imageIndex] = response.data.annotations;
      
      // 如果是当前显示的图片，更新当前标注
      if (imageIndex === currentImageIndex.value) {
        currentAnnotations.value = [...response.data.annotations];
      }
      
      ElMessage.success(`加载到 ${response.data.annotations.length} 个已有标注`);
    }
  } catch (error) {
    console.error('加载已有标注失败:', error);
    // 不显示错误信息，因为没有标注是正常情况
  }
};

// 保存当前图片的标注
const saveCurrentAnnotations = async () => {
  if (currentImageIndex.value < 0 || currentAnnotations.value.length === 0) {
    ElMessage.warning('没有可保存的标注');
    return;
  }
  
  try {
    const imageName = uploadedImages.value[currentImageIndex.value].name;
    
    // 准备保存的标注数据
    const annotationsToSave = currentAnnotations.value.map(ann => ({
      image_name: imageName,
      category: ann.label, // 使用label作为category
      type: ann.type || 'bbox',
      bbox: {
        ...ann.bbox,
        angle: ann.type === 'obb' ? ann.bbox.angle || 0 : undefined // 保留OBB的angle
      },
      points: ann.points, // 添加多边形点数据
      confidence: ann.confidence || 1.0 // 人工标注的置信度默认为1
    }));
    
    // 确保调用接口时传递正确的参数格式
    const response = await saveBatchAnnotations({
      imageName,
      tool: selectedTool.value,
      annotations: annotationsToSave
    });
    
    // 更新已保存状态
    savedAnnotations.value[currentImageIndex.value] = [...currentAnnotations.value];
    
    ElMessage.success(`成功保存 ${annotationsToSave.length} 个标注`);
  } catch (error) {
    console.error('保存标注失败:', error);
    ElMessage.error('保存标注失败: ' + (error.response?.data?.detail || error.message));
  }
};

// 切换标注模式
const handleModeChange = async (mode) => {
  const previousMode = annotationMode.value;
  annotationMode.value = mode;
  
  // 如果从自动模式切换到手动模式，保留当前的AI标注结果
  // 然后再尝试加载已保存的手动标注（如果有）
  if (mode === 'manual' && previousMode === 'auto' && currentImageIndex.value >= 0) {
    // 先保存当前的AI标注结果
    const currentAIAnotations = [...currentAnnotations.value];
    
    // 尝试加载已保存的标注
    await loadExistingAnnotations(currentImageIndex.value);
    
    // 如果没有已保存的标注，则使用AI标注结果作为基础
    if (currentAnnotations.value.length === 0 && currentAIAnotations.length > 0) {
      currentAnnotations.value = currentAIAnotations;
      ElMessage.success(`已保留 ${currentAIAnotations.length} 个AI标注结果作为手动标注的基础`);
    }
  }
  // 如果直接从手动模式切换到手动模式（即重新选择），也尝试加载已有标注
  else if (mode === 'manual' && currentImageIndex.value >= 0) {
    await loadExistingAnnotations(currentImageIndex.value);
  }
  // 切换到自动标注时拉取模型列表并刷新下拉
  if (mode === 'auto') {
    if (apiModelsList.value.length === 0) await fetchModels();
    refreshAvailableModels();
  }
};

// 选择图片
const selectImage = async (index) => {
  if (index >= 0 && index < uploadedImages.value.length) {
    // 切换图片时清空当前图片的撤销/重做栈
    annotationHistoryPast.value = [];
    annotationHistoryFuture.value = [];
    // 保存当前图片的标注结果（用新对象替换以触发响应式，切换回来时能正确显示）
    if (currentImageIndex.value >= 0 && currentAnnotations.value.length > 0) {
      imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...currentAnnotations.value] };
    }
    
    currentImageIndex.value = index;
    // 更新当前图片文件对象
    currentImageFile.value = uploadedImages.value[index].file;
    
    // 先获取可能存在的各种标注结果
    const savedManualAnnotations = savedAnnotations.value[index] || [];
    const aiGeneratedAnnotations = imageAnnotations.value[index] || [];
    
    // 更新当前标注
    if (annotationMode.value === 'manual') {
      if (savedManualAnnotations.length > 0) {
        // 手动模式下优先使用已保存的手动标注
        currentAnnotations.value = [...savedManualAnnotations];
      } else if (aiGeneratedAnnotations.length > 0) {
        // 如果没有手动标注，但有AI标注结果，则使用AI标注结果作为手动标注的基础
        currentAnnotations.value = [...aiGeneratedAnnotations];
        ElMessage.info(`已使用 ${aiGeneratedAnnotations.length} 个AI标注结果作为手动标注的基础`);
      } else {
        // 都没有则使用当前会话的 imageAnnotations，不自动从后端拉取（避免新导入的图片因同名而加载到旧标注）
        currentAnnotations.value = [...aiGeneratedAnnotations];
      }
    } else if (annotationMode.value === 'auto') {
      // 自动模式下使用AI生成的标注
      currentAnnotations.value = [...aiGeneratedAnnotations];
    }
    
    // 清除标注图片URL
    annotatedImageUrl.value = '';
    
    ElMessage.info(`已选择图片: ${uploadedImages.value[index].name}`);
  }
};

// 移除图片
const removeImage = (index) => {
  if (index >= 0 && index < uploadedImages.value.length) {
    // 如果删除的是当前选中的图片，需要重置当前图片
    if (index === currentImageIndex.value) {
      currentImageIndex.value = -1;
      currentAnnotations.value = [];
      annotatedImageUrl.value = '';
      
      // 如果还有其他图片，选择第一张
      if (uploadedImages.value.length > 1) {
        const newIndex = index === 0 ? 1 : 0;
        setTimeout(() => selectImage(newIndex), 0);
      }
    } else if (index < currentImageIndex.value) {
      // 如果删除的图片在当前图片之前，需要调整当前图片索引
      currentImageIndex.value--;
    }
    
    // 释放URL对象
    URL.revokeObjectURL(uploadedImages.value[index].url);
    
    // 从列表中移除
    uploadedImages.value.splice(index, 1);
    
    ElMessage.success('已移除图片');
  }
};

// 清除标注
const clearAnnotations = () => {
  currentAnnotations.value = [];
  annotatedImageUrl.value = '';
  if (currentImageIndex.value >= 0) {
    if (annotationMode.value === 'manual' && savedAnnotations.value[currentImageIndex.value]) {
      const next = { ...savedAnnotations.value };
      delete next[currentImageIndex.value];
      savedAnnotations.value = next;
    }
    imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [] };
  }
  ElMessage.success('已清除所有标注');
};

// 智能体数据增广：根据指令对选中图片增广并追加到列表
const runAugmentation = async () => {
  let indices = imageGalleryRef.value?.getSelectedIndices?.() ?? [];
  if (indices.length === 0 && currentImageIndex.value >= 0) {
    indices = [currentImageIndex.value];
  }
  if (indices.length === 0) {
    ElMessage.warning('请在上方图片库勾选要增广的图片，或先选择当前图片');
    return;
  }
  const files = indices.map(i => uploadedImages.value[i].file).filter(Boolean);
  if (files.length === 0) {
    ElMessage.warning('无法获取选中图片文件');
    return;
  }
  isAugmenting.value = true;
  try {
    const data = await runAugmentationAPI(files, augmentationInstruction.value);
    const augmentedList = data.augmented || [];
    const tips = data.tips || [];
    let added = 0;
    for (let i = 0; i < augmentedList.length; i++) {
      const item = augmentedList[i];
      if (!item.image_base64) continue;
      const bin = Uint8Array.from(atob(item.image_base64), c => c.charCodeAt(0));
      const blob = new Blob([bin], { type: 'image/jpeg' });
      const url = URL.createObjectURL(blob);
      const name = item.filename || `aug_${Date.now()}_${added}.jpg`;
      const file = new File([blob], name, { type: 'image/jpeg' });
      const sourceIndex = Number.isInteger(item.source_index) ? item.source_index : i;
      const sourceName = files[sourceIndex]?.name ?? '';
      const newIndex = uploadedImages.value.length;
      uploadedImages.value.push({
        name,
        url,
        file,
        isAugmented: true,
        augmentedAt: Date.now(),
        sourceName: sourceName || undefined,
      });
      imageAnnotations.value = { ...imageAnnotations.value, [newIndex]: [] };
      savedAnnotations.value = { ...savedAnnotations.value, [newIndex]: [] };
      added++;
    }
    if (added > 0) {
      ElMessage.success(`增广完成，已添加 ${added} 张图片到列表`);
      if (tips.length > 0) {
        ElMessage.warning(tips.join('；'));
      }
    } else {
      ElMessage.warning('未得到可用的增广结果');
    }
  } catch (err) {
    console.error('增广失败:', err);
    ElMessage.error('增广失败: ' + (err.response?.data?.detail || err.message));
  } finally {
    isAugmenting.value = false;
  }
};

// 深拷贝当前标注列表（用于历史栈）
function deepCloneAnnotations(list) {
  return list.map(ann => ({
    ...ann,
    bbox: ann.bbox ? { ...ann.bbox } : undefined
  }));
}

// 在用户修改前把当前状态压入历史（仅对手动模式当前图片有效）
function pushAnnotationHistoryCurrent() {
  if (currentImageIndex.value < 0 || annotationMode.value !== 'manual') return;
  const snap = deepCloneAnnotations(currentAnnotations.value);
  annotationHistoryPast.value = [...annotationHistoryPast.value.slice(-(MAX_ANNOTATION_HISTORY - 1)), snap];
  annotationHistoryFuture.value = [];
}

// 撤销
function undoAnnotation() {
  if (annotationHistoryPast.value.length === 0) return;
  const prev = annotationHistoryPast.value.pop();
  annotationHistoryFuture.value = [...annotationHistoryFuture.value, deepCloneAnnotations(currentAnnotations.value)];
  currentAnnotations.value = prev;
  if (currentImageIndex.value >= 0) {
    imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...prev] };
  }
}

// 重做
function redoAnnotation() {
  if (annotationHistoryFuture.value.length === 0) return;
  const next = annotationHistoryFuture.value.pop();
  annotationHistoryPast.value = [...annotationHistoryPast.value, deepCloneAnnotations(currentAnnotations.value)];
  currentAnnotations.value = next;
  if (currentImageIndex.value >= 0) {
    imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...next] };
  }
}

// 更新标注
const updateAnnotations = (annotations) => {
  pushAnnotationHistoryCurrent();
  // 确保标注数据格式正确，创建新数组以触发响应式更新
  const processedAnnotations = annotations.map(ann => {
    const newAnn = { ...ann };
    
    // 标准化标注数据格式
    if (newAnn.type === undefined) {
      newAnn.type = 'bbox';
    }
    
    // 确保bbox对象格式正确
    if (newAnn.bbox) {
      if (typeof newAnn.bbox === 'object' && !Array.isArray(newAnn.bbox)) {
        // 保留所有关键属性，尤其是OBB的angle
        newAnn.bbox = {
          x: parseFloat(newAnn.bbox.x || 0),
          y: parseFloat(newAnn.bbox.y || 0),
          width: parseFloat(newAnn.bbox.width || 0),
          height: parseFloat(newAnn.bbox.height || 0),
          angle: newAnn.type === 'obb' ? parseFloat(newAnn.bbox.angle || 0) : undefined // 仅OBB保留angle
        };
      } else if (Array.isArray(newAnn.bbox) && newAnn.bbox.length === 4) {
        // 数组格式转对象时，OBB类型需额外处理angle（若有）
        newAnn.bbox = {
          x: parseFloat(newAnn.bbox[0] || 0),
          y: parseFloat(newAnn.bbox[1] || 0),
          width: parseFloat(newAnn.bbox[2] || 0),
          height: parseFloat(newAnn.bbox[3] || 0),
          angle: newAnn.type === 'obb' ? parseFloat(newAnn.bbox.angle || 0) : undefined
        };
      }
    }
    
    return newAnn;
  });
  
  // 使用处理后的标注数据，确保引用变化以触发Vue的响应式更新
  currentAnnotations.value = [...processedAnnotations];
};

// 处理多边形完成事件
const handlePolygonCompleted = (polygon) => {
  ElMessage.success('已添加多边形标注');
};

// 批量清除标注处理
const handleBatchClearAnnotations = (selectedIndices) => {
  if (!selectedIndices || selectedIndices.length === 0) {
    ElMessage.warning('请先选择要批量清除标注的图片');
    return;
  }
  
  ElMessageBox.confirm(
    `确定要清除选中的 ${selectedIndices.length} 张图片上的所有标注吗？图片不会被删除，仅清除标注数据。`,
    '批量清除标注',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    let nextImageAnnotations = { ...imageAnnotations.value };
    let nextSavedAnnotations = { ...savedAnnotations.value };
    for (const index of selectedIndices) {
      nextImageAnnotations[index] = [];
      nextSavedAnnotations[index] = [];
    }
    imageAnnotations.value = nextImageAnnotations;
    savedAnnotations.value = nextSavedAnnotations;
    if (selectedIndices.includes(currentImageIndex.value)) {
      currentAnnotations.value = [];
      annotatedImageUrl.value = '';
    }
    ElMessage.success(`已清除 ${selectedIndices.length} 张图片的标注`);
  }).catch(() => {});
};

// 批量删除处理
const handleBatchDelete = (selectedIndices) => {
  if (!selectedIndices || selectedIndices.length === 0) {
    ElMessage.warning('请先选择要批量删除的图片');
    return;
  }
  
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedIndices.length} 张图片吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    // 确保从大索引开始删除，避免索引混乱
    const sortedIndices = [...selectedIndices].sort((a, b) => b - a);
    
    for (const index of sortedIndices) {
      removeImage(index);
    }
    
    ElMessage.success(`已成功删除 ${selectedIndices.length} 张图片`);
  }).catch(() => {
    // 取消删除
  });
};

// 批量标注处理
const handleBatchAnnotate = async (selectedIndices) => {
  if (!selectedIndices || selectedIndices.length === 0) {
    ElMessage.warning('请先选择要批量标注的图片');
    return;
  }
  
  if (!selectedTool.value || !selectedModel.value) {
    ElMessage.warning('请先选择标注工具和模型');
    return;
  }
  
  isAutoAnnotating.value = true;
  let successCount = 0;
  let totalAnnotations = 0;
  
  try {
    ElMessage.info(`正在批量标注 ${selectedIndices.length} 张图片，请稍候...`);
    
    // 保存当前图片的标注结果
    if (currentImageIndex.value >= 0 && currentAnnotations.value.length > 0) {
      imageAnnotations.value = { ...imageAnnotations.value, [currentImageIndex.value]: [...currentAnnotations.value] };
    }
    
    // 批量处理选中的图片
    for (let i = 0; i < selectedIndices.length; i++) {
      const index = selectedIndices[i];
      const image = uploadedImages.value[index];
      
      if (!image || !image.file) continue;
      
      try {
        const formData = new FormData();
        formData.append('image', image.file);
        formData.append('tool', selectedTool.value);
        formData.append('model', selectedModel.value);
        formData.append('categories', JSON.stringify(categories.value));
        const response = await visioFirmAPI.autoAnnotate(formData);

        if (response.data && response.data.annotations && response.data.annotations.length > 0) {
          const annotations = response.data.annotations.map(ann => {
            const newAnn = { ...ann };
            if (newAnn.type === 'bbox' && newAnn.bbox && typeof newAnn.bbox === 'object') {
              return {
                type: 'bbox',
                label: newAnn.label || 'unknown',
                confidence: newAnn.confidence ?? 1.0,
                bbox: {
                  x: parseFloat(newAnn.bbox.x ?? 0),
                  y: parseFloat(newAnn.bbox.y ?? 0),
                  width: parseFloat(newAnn.bbox.width ?? 0),
                  height: parseFloat(newAnn.bbox.height ?? 0)
                }
              };
            }
            if (newAnn.type === 'classification') {
              return { type: 'classification', label: newAnn.label || newAnn.class_name || '', confidence: newAnn.confidence ?? 0 };
            }
            if ((newAnn.type === 'polygon' || newAnn.points) && Array.isArray(newAnn.points)) {
              return { type: 'polygon', label: newAnn.label || 'unknown', confidence: newAnn.confidence ?? 1.0, points: newAnn.points };
            }
            if (newAnn.type === 'rectanglelabels' && newAnn.value) {
              return {
                type: 'bbox',
                label: (newAnn.value.rectanglelabels && newAnn.value.rectanglelabels[0]) || 'unknown',
                bbox: {
                  x: parseFloat(newAnn.value.x ?? 0),
                  y: parseFloat(newAnn.value.y ?? 0),
                  width: parseFloat(newAnn.value.width ?? 0),
                  height: parseFloat(newAnn.value.height ?? 0)
                },
                confidence: newAnn.confidence ?? 1.0
              };
            }
            const hasBbox = newAnn.bbox && (typeof newAnn.bbox === 'object' ? (newAnn.bbox.width != null && newAnn.bbox.height != null) : Array.isArray(newAnn.bbox) && newAnn.bbox.length >= 4);
            const hasPoints = Array.isArray(newAnn.points) && newAnn.points.length >= 3;
            if (!hasBbox && !hasPoints && newAnn.class_name != null && newAnn.confidence != null) {
              return { type: 'classification', label: newAnn.class_name, confidence: parseFloat(newAnn.confidence) };
            }
            if (hasPoints) {
              return {
                type: 'polygon',
                label: newAnn.class_name ?? newAnn.label ?? 'unknown',
                confidence: newAnn.confidence != null ? parseFloat(newAnn.confidence) : 1.0,
                points: newAnn.points
              };
            }
            
            // 仅当确实有 bbox 时才设为 bbox
            if (newAnn.type === undefined && (newAnn.bbox != null || newAnn.value != null)) {
              newAnn.type = 'bbox';
            }
            
            // 确保bbox对象格式正确
            if (newAnn.bbox && typeof newAnn.bbox === 'object' && !Array.isArray(newAnn.bbox)) {
              // 确保bbox对象的坐标值为数字
              newAnn.bbox = {
                x: parseFloat(newAnn.bbox.x || 0),
                y: parseFloat(newAnn.bbox.y || 0),
                width: parseFloat(newAnn.bbox.width || 0),
                height: parseFloat(newAnn.bbox.height || 0)
              };
            } else if (Array.isArray(newAnn.bbox) && newAnn.bbox.length >= 4) {
              const arr = newAnn.bbox.map(val => parseFloat(val || 0));
              newAnn.bbox = { x: arr[0], y: arr[1], width: arr[2], height: arr[3] };
            }
            
            return newAnn;
          });
          
          // 保存标注结果（用新对象替换以触发响应式更新）
          imageAnnotations.value = { ...imageAnnotations.value, [index]: annotations };
          totalAnnotations += annotations.length;
          successCount++;
          
          // 如果是当前显示的图片，更新当前标注
          if (index === currentImageIndex.value) {
            currentAnnotations.value = [...annotations];
          }
        }
      } catch (error) {
        console.error(`标注图片 ${image.name} 失败:`, error);
        ElMessage.error(`图片 ${image.name} 标注失败: ${error.message}`);
      }
    }
    
    ElMessage.success(`批量标注完成！成功处理 ${successCount} 张图片，共生成 ${totalAnnotations} 个标注结果（可在手动模式下直接编辑）`);
  } catch (error) {
    ElMessage.error('批量标注失败: ' + (error.response?.data?.detail || error.message));
    console.error('Batch annotation error:', error);
  } finally {
    isAutoAnnotating.value = false;
  }
};



// 在组件挂载时初始化
onMounted(() => {
  selectedTool.value = 'object_detection';
  handleToolChange();
  window.addEventListener('keydown', globalNavKeydown);
});

// 触发批量标注所有图片
const triggerBatchAnnotate = async () => {
  if (uploadedImages.value.length === 0) {
    ElMessage.warning('请先上传图片');
    return;
  }
  
  if (!selectedTool.value || !selectedModel.value) {
    ElMessage.warning('请先选择标注工具和模型');
    return;
  }
  
  // 确认是否批量标注所有图片
  if (confirm(`确定要对所有 ${uploadedImages.value.length} 张图片进行批量标注吗？`)) {
    // 获取所有图片的索引
    const allIndices = uploadedImages.value.map((_, index) => index);
    // 调用批量标注处理函数
    await handleBatchAnnotate(allIndices);
  }
};

// 切换到上一张图片
const previousImage = () => {
  if (currentImageIndex.value > 0) {
    selectImage(currentImageIndex.value - 1);
  }
};

// 切换到下一张图片
const nextImage = () => {
  if (currentImageIndex.value < uploadedImages.value.length - 1) {
    selectImage(currentImageIndex.value + 1);
  }
};

// 全局快捷键：上一张/下一张（A/D 或 ←/→）；撤销 Ctrl+Z、重做 Ctrl+Shift+Z
const globalNavKeydown = (e) => {
  const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
  if (e.ctrlKey && e.key.toLowerCase() === 'z') {
    if (e.shiftKey) {
      if (annotationHistoryFuture.value.length > 0) {
        redoAnnotation();
        e.preventDefault();
      }
    } else {
      if (annotationHistoryPast.value.length > 0) {
        undoAnnotation();
        e.preventDefault();
      }
    }
    return;
  }
  if (uploadedImages.value.length === 0) return;
  if (e.key === 'ArrowLeft' || e.key.toLowerCase() === 'a') {
    previousImage();
    if (currentImageIndex.value > 0) e.preventDefault();
  } else if (e.key === 'ArrowRight' || e.key.toLowerCase() === 'd') {
    nextImage();
    if (currentImageIndex.value < uploadedImages.value.length - 1) e.preventDefault();
  }
};

watch(currentImageIndex, () => {
  selectedAnnotationIndexForCanvas.value = -1;
});

// 在组件卸载时清理
onUnmounted(() => {
  window.removeEventListener('keydown', globalNavKeydown);
  uploadedImages.value.forEach(image => {
    URL.revokeObjectURL(image.url);
  });
});
</script>

<style scoped>
/* 页面容器 */
.page-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow-x: hidden;
  overflow-y: auto;
  width: 100%;
  max-width: 100vw;
  box-sizing: border-box;
}

/* 头部区域 */
.header-section {
  flex-shrink: 0;
  margin-bottom: 20px;
  background-color: #f0f9ff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.header-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.header-title-row h1 {
  margin: 0;
  color: #1890ff;
  font-size: 24px;
}

.project-stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 14px;
  color: #606266;
}

.project-stats .stats-sep {
  color: #c0c4cc;
  user-select: none;
}

.project-stats .stats-link {
  color: #409eff;
  cursor: pointer;
  text-decoration: none;
}

.project-stats .stats-link:hover {
  text-decoration: underline;
}

/* 工具栏行布局 */
.toolbar-row {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar-left {
  flex-shrink: 0;
}

/* 标注模式选择样式 */
.mode-selection {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: #fff;
  padding: 10px 15px;
  border-radius: 6px;
  border: 1px solid #dcdfe6;
  width: fit-content;
}

.mode-label {
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
}

/* 标注工具样式 */
.import-model-file-name {
  margin-top: 6px;
  font-size: 12px;
  color: #606266;
}
.annotation-tools {
  background-color: #fff;
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #dcdfe6;
}

/* 手动标注工具样式 */
.manual-tools {
  background-color: #fff;
  padding: 10px 15px;
  border-radius: 6px;
  border: 1px solid #dcdfe6;
}

/* 操作按钮样式 */
.action-buttons {
  justify-content: flex-start;
  background-color: #fff;
  padding: 10px 15px;
  border-radius: 6px;
  border: 1px solid #dcdfe6;
}

/* 内容区域：避免浏览器缩放时横向溢出 */
.content-section {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

/* 图片导航栏样式 */
.image-navigation {
  background-color: #fff;
  padding: 10px 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.nav-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.image-counter {
  margin: 0 15px;
  font-weight: 500;
  color: #303133;
}

.thumbnail-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding: 5px 0;
}

.thumbnail-item {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.3s;
}

.thumbnail-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-item.active {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.thumbnail-more {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  background-color: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #909399;
  border: 1px dashed #dcdfe6;
}

/* 图片库容器 - 新布局 */
.image-gallery-container {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
  padding: 15px;
  overflow: hidden;
}

/* 主内容区域：图片区随图片自适应高度，整体可滚动，下方为标注信息栏 */
.main-content {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  min-height: min(60vh, 600px);
  max-height: 85vh;
  overflow-y: auto;
  overflow-x: hidden;
  width: 100%;
  box-sizing: border-box;
}

/* 图片显示区域：不限制高度，随图片尺寸自适应 */
.image-display-section {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

/* 标注框信息栏：紧跟图片区下方，有固定最小高度 */
.annotation-list-wrapper {
  flex-shrink: 0;
  min-height: 200px;
  margin-top: 0;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border-radius: 0 0 8px 8px;
}
.annotation-list-wrapper.has-annotations {
  min-height: 220px;
}
.annotation-list-wrapper :deep(.annotations-section) {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
}
.annotation-list-wrapper :deep(.annotations-list) {
  min-height: 120px;
  max-height: 320px;
  overflow-y: auto;
}
.annotation-list-empty {
  padding: 16px 20px;
  background: #fafafa;
  border: 1px dashed #e4e7ed;
  border-radius: 8px;
  color: #909399;
  font-size: 13px;
  text-align: center;
}

.current-image-info {
  flex-shrink: 0;
  margin-bottom: 10px;
  padding: 10px;
  background-color: #e6f7ff;
  border-radius: 4px;
}

.current-image-info h4 {
  margin: 0;
  color: #409eff;
  font-size: 16px;
}

.annotation-status {
  margin: 5px 0 0 0;
  color: #67c23a;
  font-size: 14px;
}

/* 图片容器：高度随图片自适应，不限制 */
.image-container {
  flex: 0 0 auto;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.image-display {
  flex: 1;
  min-height: 400px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: white;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  position: relative;
}

.image-wrapper {
  position: relative;
  display: inline-block;
}

.display-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
}

/* 占位符样式 */
.placeholder {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
  color: #909399;
  font-size: 16px;
}

/* 上传占位符样式 */
.upload-placeholder {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #fafafa;
  color: #999;
  border: 2px dashed #ccc;
  border-radius: 8px;
}

/* 图片项样式（用于图片库） */
.image-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.image-item:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10;
}

.image-item.active {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 图片覆盖层 */
.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  color: white;
  padding: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.image-item:hover .image-overlay {
  opacity: 1;
}

.image-name {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.remove-btn {
  width: 24px;
  height: 24px;
  padding: 0;
  margin-left: 8px;
}

.current-image-info {
  flex-shrink: 0;
  margin-bottom: 10px;
  padding: 10px;
  background-color: #e6f7ff;
  border-radius: 4px;
}

.current-image-info h4 {
  margin: 0;
  color: #409eff;
  font-size: 16px;
}

.annotation-status {
  margin: 5px 0 0 0;
  color: #67c23a;
  font-size: 14px;
}

.image-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.image-display {
  flex: 1;
  min-height: 400px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: white;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  position: relative;
}

.image-wrapper {
  position: relative;
  display: inline-block;
}

.display-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
  display: block;
}

.annotation-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: auto;
  z-index: 10;
}

.placeholder {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 2px dashed #ccc;
  border-radius: 8px;
  color: #999;
  min-height: 400px;
}

.tool-selection {
  margin-bottom: 10px;
}

.model-info {
  margin-bottom: 15px;
}

.model-info-card {
  background-color: #f0f9ff;
  padding: 8px 15px;
  border-radius: 4px;
  border-left: 4px solid #1890ff;
}

.model-label {
  font-weight: bold;
  margin-right: 10px;
  color: #606266;
}

.model-value {
  color: #1890ff;
  font-weight: 500;
}

.annotations-section {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 15px;
  margin-top: 20px;
  max-height: min(40vh, 500px);
  overflow-y: auto;
  overflow-x: hidden;
  transition: max-height 0.3s ease;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  width: 100%;
  box-sizing: border-box;
}

.annotations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.toggle-btn {
  padding: 2px;
}

.annotations-list {
  flex-shrink: 0;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fafafa;
  overflow-y: visible;
}

.annotations-list h3 {
  margin: 0 0 15px 0;
  color: #409eff;
}

.annotation-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15.625rem), 1fr));
  gap: 10px;
}

.annotation-item {
  background: white;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.annotation-type {
  font-weight: bold;
  color: #409eff;
  margin-bottom: 5px;
}

.annotation-details {
  font-size: 12px;
  color: #666;
}

/* 类别管理样式 */
.category-management {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f0f9ff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.category-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.category-item {
  margin-bottom: 5px;
}

.add-category {
  margin-top: 10px;
}

.category-input {
  width: 100px;
}

.button-new-category {
  margin-top: 5px;
}

/* 标注说明与增广区域整体 */
.annotation-tips {
  margin: 18px 0;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
}
.annotation-tips :deep(.el-collapse-item__header) {
  padding-left: 20px;
}
.annotation-tips :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}
.annotation-tips :deep(.el-collapse-item__content) {
  padding: 0;
}

/* 标注工具使用说明 - 内容区内边距 */
.tips-content {
  padding: 20px 24px 24px;
}
.tips-content h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #303133;
  font-weight: 600;
}
.tips-content h4:not(:first-child) {
  margin-top: 20px;
}
.tips-content ul {
  margin: 0 0 4px 0;
  padding-left: 22px;
  color: #606266;
  line-height: 1.65;
}
.tips-content li {
  margin-bottom: 6px;
}

.augmentation-section {
  padding: 20px 24px 24px;
}
.augmentation-tip {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 14px 0;
}
.augmentation-input {
  margin-bottom: 14px;
}
.augmentation-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}
.augmentation-submit {
  margin-top: 4px;
}

/* 增广结果展示栏 */
.augmented-results-panel {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
.augmented-results-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}
.augmented-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
  max-height: 200px;
  overflow-y: auto;
}
.augmented-result-item {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.augmented-result-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}
.augmented-result-item.active {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff;
}
.augmented-result-item img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  display: block;
}
.augmented-result-info {
  padding: 4px 6px;
  background: #f5f7fa;
  font-size: 11px;
  overflow: hidden;
}
.augmented-result-name {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #303133;
}
.augmented-result-source {
  display: block;
  color: #909399;
  font-size: 10px;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .main-layout {
    flex-direction: column;
  }
  
  .right-panel {
    max-width: none;
    min-width: auto;
    max-height: 300px;
  }
  
  .images-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 768px) {
  .images-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
