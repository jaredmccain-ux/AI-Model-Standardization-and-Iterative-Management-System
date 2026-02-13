<template>
  <div class="model-development">
    <el-card class="header-card">
      <h1>模型开发</h1>
      <p>AI模型训练与管理平台，支持常规训练、增量训练、冻结策略、知识蒸馏训练</p>
    </el-card>

    <el-row :gutter="20">
      <!-- 左侧：训练配置 -->
      <el-col :span="12">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>训练配置</span>
              <el-button type="primary" @click="startTraining" :loading="isTraining">
                {{ isTraining ? '训练中...' : '开始训练' }}
              </el-button>
            </div>
          </template>

          <el-form :model="trainingConfig" :rules="rules" ref="configForm" label-width="120px">
            <!-- 训练类型选择 -->
            <el-form-item label="训练类型" prop="trainingType">
              <el-radio-group v-model="trainingConfig.trainingType" @change="onTrainingTypeChange">
                <el-radio-button label="regular">常规训练</el-radio-button>
                <el-radio-button label="incremental">增量训练</el-radio-button>
                <el-radio-button label="freeze_strategy">冻结策略</el-radio-button>
                <el-radio-button label="distillation">知识蒸馏</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <!-- 基础配置 -->
            <el-form-item label="任务类型" prop="task">
              <el-select v-model="trainingConfig.task" placeholder="选择任务类型">
                <el-option label="目标检测" value="detect"></el-option>
                <el-option label="图像分割" value="segment"></el-option>
                <el-option label="图像分类" value="classify"></el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="模型规模" prop="model_type">
              <el-select v-model="trainingConfig.model_type" placeholder="选择模型规模">
                <el-option label="YOLOv8n (最小)" value="n"></el-option>
                <el-option label="YOLOv8s (小型)" value="s"></el-option>
                <el-option label="YOLOv8m (中型)" value="m"></el-option>
                <el-option label="YOLOv8l (大型)" value="l"></el-option>
                <el-option label="YOLOv8x (超大)" value="x"></el-option>
              </el-select>
            </el-form-item>

            <!-- 优化后的数据集文件上传 -->
            <el-form-item label="数据集文件" prop="data_path">
              <div class="file-upload-container">
                <!-- 手动输入路径或选择本地文件 -->
                <div style="display: flex; gap: 10px; margin-bottom: 10px; width: 100%;">
                  <el-input 
                    v-model="trainingConfig.data_path" 
                    placeholder="请输入数据集YAML文件的绝对路径，或使用右侧按钮选择"
                    clearable
                  >
                    <template #prefix>
                      <el-icon><document /></el-icon>
                    </template>
                  </el-input>
                  <el-button @click="selectLocalFile" type="primary" plain title="在服务器端打开文件选择器 (仅限本地部署)">
                    <el-icon><folder-opened /></el-icon> 选择本地文件
                  </el-button>
                </div>
              </div>
            </el-form-item>

            <!-- 增量训练特有配置 -->
            <template v-if="trainingConfig.trainingType === 'incremental'">
              <el-form-item label="基础模型" prop="base_model_path" :rules="[{ required: true, message: '请选择基础模型文件', trigger: 'change' }]">
                <div style="display: flex; gap: 10px; width: 100%;">
                  <el-input v-model="trainingConfig.base_model_path" placeholder="基础模型路径 (.pt)"></el-input>
                  <el-button @click="selectBaseModelFile" type="primary" plain title="选择本地文件">
                    <el-icon><folder-opened /></el-icon>
                  </el-button>
                </div>
              </el-form-item>

              <el-form-item label="旧数据配置" prop="old_data_path" :rules="[{ required: true, message: '请输入旧数据集YAML路径', trigger: 'blur' }]">
                 <div style="display: flex; gap: 10px; width: 100%;">
                   <el-input v-model="trainingConfig.old_data_path" placeholder="旧数据集YAML路径 (必填，用于防止遗忘)"></el-input>
                   <el-button @click="selectLocalOldFile" type="primary" plain title="选择本地文件">
                     <el-icon><folder-opened /></el-icon>
                   </el-button>
                 </div>
              </el-form-item>

              <el-form-item label="新增类别">
                <el-tag
                  v-for="(tag, index) in trainingConfig.new_classes"
                  :key="index"
                  closable
                  @close="removeNewClass(index)"
                  style="margin-right: 8px; margin-bottom: 8px;"
                >
                  {{ tag }}
                </el-tag>
                <el-input
                  v-if="inputVisible"
                  ref="inputRef"
                  v-model="inputValue"
                  class="input-new-tag"
                  size="small"
                  @keyup.enter="handleInputConfirm"
                  @blur="handleInputConfirm"
                />
                <el-button v-else class="button-new-tag" size="small" @click="showInput">
                  + 添加类别
                </el-button>
              </el-form-item>
            </template>

            <!-- 知识蒸馏特有配置 -->
            <template v-if="trainingConfig.trainingType === 'distillation'">
              <el-form-item label="教师模型" prop="teacher_model_path" :rules="[{ required: true, message: '请输入教师模型路径', trigger: 'change' }]">
                <div style="display: flex; gap: 10px; width: 100%;">
                  <el-input v-model="trainingConfig.teacher_model_path" placeholder="教师模型权重路径 (.pt)"></el-input>
                  <el-button @click="selectTeacherModelFile" type="primary" plain title="选择本地文件">
                    <el-icon><folder-opened /></el-icon>
                  </el-button>
                </div>
              </el-form-item>

              <el-form-item label="旧数据配置" prop="old_data_path">
                <div style="display: flex; gap: 10px; width: 100%;">
                  <el-input v-model="trainingConfig.old_data_path" placeholder="旧数据集YAML路径 (用于回放)"></el-input>
                  <el-button @click="selectLocalOldFile" type="primary" plain title="选择本地文件">
                    <el-icon><folder-opened /></el-icon>
                  </el-button>
                </div>
              </el-form-item>

              <el-divider content-position="left">蒸馏参数</el-divider>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="温度 (T)">
                    <el-input-number v-model="trainingConfig.distill_temperature" :min="1" :step="0.5"></el-input-number>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                   <el-form-item label="分类权重">
                    <el-input-number v-model="trainingConfig.distill_cls_weight" :min="0" :step="0.1"></el-input-number>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="回归权重">
                    <el-input-number v-model="trainingConfig.distill_reg_weight" :min="0" :step="0.1"></el-input-number>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                   <el-form-item label="特征权重">
                    <el-input-number v-model="trainingConfig.distill_feat_weight" :min="0" :step="0.1"></el-input-number>
                  </el-form-item>
                </el-col>
              </el-row>

               <el-divider content-position="left">高级选项</el-divider>
               <el-form-item label="一致性训练">
                 <el-switch v-model="trainingConfig.enable_consistency" active-text="启用强弱增强一致性"></el-switch>
               </el-form-item>
               
               <el-form-item label="旧样本回放">
                  <el-tooltip content="旧样本在Batch中的比例" placement="top">
                    <el-slider v-model="trainingConfig.replay_ratio" :min="0" :max="0.5" :step="0.05" show-input></el-slider>
                  </el-tooltip>
               </el-form-item>
            </template>

            <!-- 训练参数 -->
            <el-form-item label="训练轮数" prop="epochs">
              <el-input-number v-model="trainingConfig.epochs" :min="1" :max="1000" :step="1"></el-input-number>
            </el-form-item>

            <el-form-item label="图像尺寸" prop="imgsz">
              <el-select v-model="trainingConfig.imgsz" placeholder="选择图像尺寸">
                <el-option label="320" :value="320"></el-option>
                <el-option label="640" :value="640"></el-option>
                <el-option label="1280" :value="1280"></el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="批次大小" prop="batch">
              <el-input-number v-model="trainingConfig.batch" :min="1" :max="64" :step="1"></el-input-number>
            </el-form-item>

            <el-form-item label="早停耐心" prop="patience">
              <el-input-number v-model="trainingConfig.patience" :min="5" :max="100" :step="1"></el-input-number>
            </el-form-item>

            <!-- 冻结策略配置 -->
            <template v-if="trainingConfig.trainingType === 'freeze_strategy'">
              <el-form-item label="启用冻结策略">
                <el-switch v-model="trainingConfig.use_freeze_strategy"></el-switch>
              </el-form-item>

              <el-form-item label="最小阶段轮数" v-if="trainingConfig.use_freeze_strategy">
                <el-input-number v-model="trainingConfig.min_epochs_per_stage" :min="5" :max="50" :step="1"></el-input-number>
              </el-form-item>
            </template>

            <el-form-item label="项目名称" prop="name">
              <el-input v-model="trainingConfig.name" placeholder="输入项目名称（可选）"></el-input>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：训练状态和结果 -->
      <el-col :span="12">
        <!-- 训练状态 -->
        <el-card class="status-card" style="margin-bottom: 20px;">
          <template #header>
            <span>训练状态</span>
          </template>

          <div v-if="currentTask">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="任务ID">{{ currentTask.task_id }}</el-descriptions-item>
              <el-descriptions-item label="训练类型">{{ getTrainingTypeLabel(currentTask.training_type) }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getStatusType(currentTask.status)">{{ getStatusLabel(currentTask.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="进度">
                <el-progress :percentage="currentTask.progress" :status="currentTask.status === 'failed' ? 'exception' : undefined"></el-progress>
              </el-descriptions-item>
              <el-descriptions-item label="当前轮数">{{ currentTask.current_epoch }} / {{ currentTask.total_epochs }}</el-descriptions-item>
              <el-descriptions-item label="开始时间">{{ formatTime(currentTask.started_at) }}</el-descriptions-item>
            </el-descriptions>

            <div style="margin-top: 16px;" v-if="currentTask.status === 'running'">
              <el-button type="danger" @click="cancelTraining">取消训练</el-button>
            </div>

            <div style="margin-top: 16px;" v-if="currentTask.error_message">
              <el-alert title="训练错误" type="error" :description="currentTask.error_message" show-icon></el-alert>
            </div>
          </div>

          <el-empty v-else description="暂无训练任务" :image-size="100"></el-empty>
        </el-card>

        <!-- 训练日志 -->
        <el-card class="log-card">
          <template #header>
            <div class="card-header">
              <span>训练日志</span>
              <el-button size="small" @click="refreshLogs" :loading="logsLoading">刷新</el-button>
            </div>
          </template>

          <div class="log-container" ref="logContainer">
            <div v-if="trainingLogs.length > 0">
              <div v-for="(log, index) in trainingLogs" :key="index" class="log-item">
                {{ log }}
              </div>
            </div>
            <el-empty v-else description="暂无日志" :image-size="80"></el-empty>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 训练历史 -->
    <el-card class="history-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>训练历史</span>
          <el-button size="small" @click="refreshTasks">刷新</el-button>
        </div>
      </template>

      <el-table :data="trainingTasks" style="width: 100%" v-loading="tasksLoading">
        <el-table-column prop="task_id" label="任务ID" width="200" show-overflow-tooltip></el-table-column>
        <el-table-column prop="training_type" label="训练类型" width="120">
          <template #default="scope">
            {{ getTrainingTypeLabel(scope.row.training_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="scope">
            <el-progress :percentage="scope.row.progress" :show-text="false" :stroke-width="8"></el-progress>
            <span style="margin-left: 8px;">{{ scope.row.progress.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="result_path" label="结果路径" show-overflow-tooltip></el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" @click="viewTaskDetails(scope.row)">详情</el-button>
            <el-button size="small" type="danger" @click="cancelTask(scope.row.task_id)" v-if="scope.row.status === 'running'">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="taskDetailVisible" title="任务详情" width="60%">
      <div v-if="selectedTask">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ selectedTask.task_id }}</el-descriptions-item>
          <el-descriptions-item label="训练类型">{{ getTrainingTypeLabel(selectedTask.training_type) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedTask.status)">{{ getStatusLabel(selectedTask.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="进度">{{ selectedTask.progress.toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(selectedTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(selectedTask.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(selectedTask.completed_at) }}</el-descriptions-item>
          <el-descriptions-item label="结果路径">{{ selectedTask.result_path || '暂无' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px;" v-if="selectedTask.metrics && Object.keys(selectedTask.metrics).length > 0">
          <h4>训练指标</h4>
          <el-descriptions :column="3" border>
            <el-descriptions-item v-for="(value, key) in selectedTask.metrics" :key="key" :label="key">
              {{ typeof value === 'number' ? value.toFixed(4) : value }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Document, Cpu, FolderOpened } from '@element-plus/icons-vue'
import axios from 'axios'

// 响应式数据
const isTraining = ref(false)
const inputVisible = ref(false)
const inputValue = ref('')
const inputRef = ref()
const configForm = ref()
const logContainer = ref()
const logsLoading = ref(false)
const tasksLoading = ref(false)
const taskDetailVisible = ref(false)
const selectedTask = ref(null)
const currentTask = ref(null)
const trainingTasks = ref([])
const trainingLogs = ref([])
const pollingTimer = ref(null)

// 训练配置
const trainingConfig = reactive({
  trainingType: 'regular',
  task: 'detect',
  model_type: 's',
  data_path: '',
  epochs: 50,
  imgsz: 640,
  batch: 8,
  patience: 15,
  use_freeze_strategy: true,
  min_epochs_per_stage: 15,
  name: '',
  base_model_path: '',
  new_classes: [],
  // 增量训练
  old_data_path: '',
  
  // 蒸馏训练
  teacher_model_path: '',
  distill_temperature: 2.0,
  distill_cls_weight: 1.0,
  distill_reg_weight: 2.0,
  distill_feat_weight: 5.0,
  enable_consistency: false,
  replay_ratio: 0.2
})

// 表单验证规则
const rules = {
  trainingType: [{ required: true, message: '请选择训练类型', trigger: 'change' }],
  task: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  model_type: [{ required: true, message: '请选择模型规模', trigger: 'change' }],
  data_path: [{ required: true, message: '请输入数据集路径', trigger: 'blur' }],
  epochs: [{ required: true, message: '请输入训练轮数', trigger: 'blur' }],
  imgsz: [{ required: true, message: '请选择图像尺寸', trigger: 'change' }],
  batch: [{ required: true, message: '请输入批次大小', trigger: 'blur' }],
  // teacher_model_path 规则在template中动态添加
}

// 导入API配置
import { API_BASE_URL, switchToFallback, getApiUrl } from '@/config/api.js'

// API基础URL - 现在使用getApiUrl()函数获取动态地址

// 方法
const onTrainingTypeChange = () => {
  // 重置特定配置
  if (trainingConfig.trainingType !== 'incremental') {
    trainingConfig.base_model_path = ''
    trainingConfig.new_classes = []
  }
  if (trainingConfig.trainingType !== 'freeze_strategy') {
    trainingConfig.use_freeze_strategy = true
    trainingConfig.min_epochs_per_stage = 15
  }
  if (trainingConfig.trainingType !== 'distillation') {
    trainingConfig.teacher_model_path = ''
  }
}

const selectDataFile = () => {
  // 这里可以集成文件选择器
  ElMessage.info('请手动输入数据集YAML文件路径')
}

const selectLocalFile = async () => {
  try {
    const response = await axios.get(`${getApiUrl()}/api/training/select-local-file`)
    if (response.data.path) {
      trainingConfig.data_path = response.data.path
      ElMessage.success('已选择文件: ' + response.data.path)
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('无法打开文件选择对话框，请手动输入路径')
  }
}

const selectLocalOldFile = async () => {
  try {
    const response = await axios.get(`${getApiUrl()}/api/training/select-local-file`)
    if (response.data.path) {
      trainingConfig.old_data_path = response.data.path
      ElMessage.success('已选择旧数据文件: ' + response.data.path)
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('无法打开文件选择对话框，请手动输入路径')
  }
}

const selectBaseModelFile = async () => {
  try {
    const response = await axios.get(`${getApiUrl()}/api/training/select-local-file`, {
      params: { file_type: 'model' }
    })
    if (response.data.path) {
      trainingConfig.base_model_path = response.data.path
      ElMessage.success('已选择基础模型: ' + response.data.path)
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('无法打开文件选择对话框，请手动输入路径')
  }
}

const selectTeacherModelFile = async () => {
  try {
    const response = await axios.get(`${getApiUrl()}/api/training/select-local-file`, {
      params: { file_type: 'model' }
    })
    if (response.data.path) {
      trainingConfig.teacher_model_path = response.data.path
      ElMessage.success('已选择教师模型: ' + response.data.path)
    }
  } catch (error) {
    console.error('选择文件失败:', error)
    ElMessage.error('无法打开文件选择对话框，请手动输入路径')
  }
}

const showInput = () => {
  inputVisible.value = true
  nextTick(() => {
    inputRef.value.input.focus()
  })
}

const handleInputConfirm = () => {
  if (inputValue.value) {
    trainingConfig.new_classes.push(inputValue.value)
  }
  inputVisible.value = false
  inputValue.value = ''
}

const removeNewClass = (index) => {
  trainingConfig.new_classes.splice(index, 1)
}

// 文件上传处理方法 (已废弃，改用本地文件选择)

const getFileName = (path) => {
  if (!path) return ''
  return path.split(/[\\/]/).pop() || path
}

const startTraining = async () => {
  try {
    await configForm.value.validate()
    
    isTraining.value = true
    
    const endpoint = {
      regular: '/api/training/regular',
      incremental: '/api/training/incremental',
      freeze_strategy: '/api/training/freeze-strategy',
      distillation: '/api/training/distillation'
    }[trainingConfig.trainingType]
    
    const response = await axios.post(`${getApiUrl()}${endpoint}`, trainingConfig)
    
    ElMessage.success('训练任务已启动')
    
    // 开始轮询任务状态
    startPolling(response.data.task_id)
    
  } catch (error) {
    console.error('启动训练失败:', error)
    ElMessage.error('启动训练失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isTraining.value = false
  }
}

const startPolling = (taskId) => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
  
  pollingTimer.value = setInterval(async () => {
    try {
      const response = await axios.get(`${getApiUrl()}/api/training/tasks/${taskId}`)
      currentTask.value = response.data
      
      // 如果任务完成，停止轮询
      if (['completed', 'failed', 'cancelled'].includes(response.data.status)) {
        clearInterval(pollingTimer.value)
        pollingTimer.value = null
        
        // 刷新任务列表
        refreshTasks()
        
        // 显示完成消息
        if (response.data.status === 'completed') {
          ElMessage.success('训练完成！')
        } else if (response.data.status === 'failed') {
          ElMessage.error('训练失败！')
        }
      }
      
      // 刷新日志
      refreshLogs()
      
    } catch (error) {
      console.error('获取任务状态失败:', error)
      
      // 智能错误处理
      if (error.message.includes('Network Error')) {
        // 尝试切换到备用API
        const switched = switchToFallback();
        if (switched) {
          console.warn('网络连接问题，已切换到备用服务器');
          // 下一次轮询会使用新的API地址
        }
      }
    }
  }, 2000) // 每2秒轮询一次
}

const cancelTraining = async () => {
  if (!currentTask.value) return
  
  try {
    await ElMessageBox.confirm('确定要取消当前训练任务吗？', '确认取消', {
      type: 'warning'
    })
    
    await axios.post(`${getApiUrl()}/api/training/tasks/${currentTask.value.task_id}/cancel`)
    ElMessage.success('训练任务已取消')
    
    // 停止轮询
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
    
    refreshTasks()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消训练失败:', error)
      ElMessage.error('取消训练失败')
    }
  }
}

const refreshLogs = async () => {
  if (!currentTask.value) return
  
  try {
    logsLoading.value = true
    const response = await axios.get(`${getApiUrl()}/api/training/tasks/${currentTask.value.task_id}/logs`)
    trainingLogs.value = response.data.logs
    
    // 自动滚动到底部
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
    
  } catch (error) {
    console.error('获取日志失败:', error)
    
    // 智能错误处理
    if (error.message.includes('Network Error')) {
      // 尝试切换到备用API
      const switched = switchToFallback();
      if (switched) {
        console.warn('网络连接问题，已切换到备用服务器');
      }
    }
  } finally {
    logsLoading.value = false
  }
}

const refreshTasks = async () => {
  try {
    tasksLoading.value = true
    const response = await axios.get(`${getApiUrl()}/api/training/tasks`)
    trainingTasks.value = response.data
  } catch (error) {
    console.error('获取任务列表失败:', error)
    
    // 智能错误处理
    if (error.message.includes('Network Error')) {
      // 尝试切换到备用API
      const switched = switchToFallback();
      if (switched) {
        ElMessage.warning('网络连接问题，已切换到备用服务器，正在重试...');
        // 延迟一秒后重试
        setTimeout(() => {
          refreshTasks();
        }, 1000);
        return;
      }
      ElMessage.error('获取任务列表失败，请检查网络连接或稍后重试');
    } else {
      ElMessage.error('获取任务列表失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    tasksLoading.value = false
  }
}

const viewTaskDetails = (task) => {
  selectedTask.value = task
  taskDetailVisible.value = true
}

const cancelTask = async (taskId) => {
  try {
    await ElMessageBox.confirm('确定要取消这个训练任务吗？', '确认取消', {
      type: 'warning'
    })
    
    await axios.post(`${getApiUrl()}/api/training/tasks/${taskId}/cancel`)
    ElMessage.success('任务已取消')
    refreshTasks()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消任务失败:', error)
      ElMessage.error('取消任务失败')
    }
  }
}

// 辅助方法
const getTrainingTypeLabel = (type) => {
  const labels = {
    regular: '常规训练',
    incremental: '增量训练',
    freeze_strategy: '冻结策略',
    distillation: '知识蒸馏'
  }
  return labels[type] || type
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return types[status] || 'info'
}

const formatTime = (timeStr) => {
  if (!timeStr) return '暂无'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  refreshTasks()
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
})
</script>

<style scoped>
.model-development {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-card {
  height: fit-content;
}

.status-card, .log-card {
  height: fit-content;
}

.log-container {
  height: 300px;
  overflow-y: auto;
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
}

.log-item {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  margin-bottom: 4px;
  white-space: pre-wrap;
}

.input-new-tag {
  width: 90px;
  margin-left: 8px;
  vertical-align: bottom;
}

.button-new-tag {
  margin-left: 8px;
  height: 32px;
  line-height: 30px;
  padding-top: 0;
  padding-bottom: 0;
}

.history-card {
  margin-top: 20px;
}

:deep(.el-progress-bar__outer) {
  background-color: #e4e7ed;
}

:deep(.el-progress-bar__inner) {
  transition: width 0.3s ease;
}

/* 新增的文件上传样式 */
.file-upload-container {
  width: 100%;
}

.dataset-upload, .model-upload {
  width: 100%;
}

.dataset-upload :deep(.el-upload-dragger) {
  width: 100%;
  height: 120px;
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: auto;
  transition: border-color 0.3s;
}

.dataset-upload :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
}

.model-upload :deep(.el-upload-dragger) {
  width: 100%;
  height: 120px;
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color 0.3s;
}

.model-upload :deep(.el-upload-dragger:hover) {
  border-color: #67c23a;
}

.file-path-display {
  margin-top: 12px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.file-path-display .el-tag {
  margin-right: 8px;
}

.file-full-path {
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

:deep(.el-upload__tip) {
  font-size: 12px;
  color: #606266;
  margin-top: 7px;
}
</style>