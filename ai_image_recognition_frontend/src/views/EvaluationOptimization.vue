<template>
  <div class="evaluation-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span class="title">模型评估与优化</span>
          <el-button type="info" plain circle @click="showGuide = true">
            <el-icon><QuestionFilled /></el-icon>
          </el-button>
        </div>
      </template>

      <!-- 评估表单 -->
      <div class="evaluation-form-section">
        <h3>启动评估任务</h3>
        <el-form :model="evaluationRequest" label-width="120px" class="demo-ruleForm">
          <el-form-item label="模型ID:">
            <el-input v-model="evaluationRequest.model_id" placeholder="请输入模型ID（如 yolov8n）" />
          </el-form-item>
          
          <el-form-item label="IOU阈值:">
            <el-input-number 
              v-model="evaluationRequest.iou_threshold" 
              :precision="2" 
              :step="0.05" 
              :max="1" 
              :min="0"
              style="width: 100%"
            />
          </el-form-item>

          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item label="一键导入:">
                <el-upload
                  class="upload-demo"
                  action="#"
                  :auto-upload="false"
                  :on-change="(file) => handleFileChange(file, 'combined')"
                  :limit="1"
                  accept=".json"
                  style="width: 100%"
                >
                  <el-button type="warning" plain style="width: 100%">上传训练生成的 evaluation_data.json</el-button>
                  <template #tip>
                    <div class="el-upload__tip">同时包含预测结果和真实标注的合并文件</div>
                  </template>
                </el-upload>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="预测数据:">
                <el-upload
                  class="upload-demo"
                  action="#"
                  :auto-upload="false"
                  :on-change="(file) => handleFileChange(file, 'predictions')"
                  :limit="1"
                  accept=".json"
                >
                  <el-button type="primary" plain>上传预测结果 JSON</el-button>
                  <template #tip>
                    <div class="el-upload__tip">格式: [{ "class_name": "...", "box": [x1,y1,x2,y2], "confidence": 0.9 }]</div>
                  </template>
                </el-upload>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="真实标注:">
                <el-upload
                  class="upload-demo"
                  action="#"
                  :auto-upload="false"
                  :on-change="(file) => handleFileChange(file, 'groundTruths')"
                  :limit="1"
                  accept=".json"
                >
                  <el-button type="success" plain>上传真实标注 JSON</el-button>
                  <template #tip>
                    <div class="el-upload__tip">格式: [{ "class_name": "...", "box": [x1,y1,x2,y2] }]</div>
                  </template>
                </el-upload>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item>
            <el-button type="primary" :loading="loading" @click="startEvaluation" size="large">
              {{ loading ? '模型评估计算中...' : '开始执行评估' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 评估结果展示区 -->
      <div v-if="evaluationResult" class="result-section">
        <el-divider content-position="left">评估结果报告</el-divider>


        
        <div class="status-header">
          <el-tag :type="getStatusType(evaluationResult.status)" effect="dark" size="large">
            状态: {{ getStatusText(evaluationResult.status) }}
          </el-tag>
          <span class="eval-id">评估ID: {{ evaluationResult.evaluation_id }}</span>
        </div>

        <div v-if="evaluationResult.status === 'completed'" class="completed-results">
          <!-- 核心指标卡片 -->
          <div class="metrics-grid">
            <div class="metric-item">
              <span class="label">mAP@0.5</span>
              <span class="value">{{ evaluationResult.metrics.mAP50.toFixed(4) }}</span>
            </div>
            <div class="metric-item">
              <span class="label">mAP@0.5:0.95</span>
              <span class="value">{{ evaluationResult.metrics.mAP50_95.toFixed(4) }}</span>
            </div>
            <div class="metric-item">
              <span class="label">精确率 (Precision)</span>
              <span class="value">{{ evaluationResult.metrics.precision.toFixed(4) }}</span>
            </div>
            <div class="metric-item">
              <span class="label">召回率 (Recall)</span>
              <span class="value">{{ evaluationResult.metrics.recall.toFixed(4) }}</span>
            </div>
            <div class="metric-item">
              <span class="label">F1 分数</span>
              <span class="value">{{ evaluationResult.metrics.f1_score.toFixed(4) }}</span>
            </div>
          </div>

          <el-row :gutter="24">
            <!-- 左侧：LLM 分析 -->
            <el-col :span="14">
              <div class="llm-analysis-card">
                <div class="analysis-header">
                  <el-icon><MagicStick /></el-icon>
                  <span>LLM 智能优化建议</span>
                </div>
                <div class="analysis-content" v-if="evaluationResult.llm_analysis">
                  <div v-html="formatLLMAnalysis(evaluationResult.llm_analysis)"></div>
                </div>
                <div class="analysis-content empty" v-else>
                  正在生成智能分析报告，请稍候...
                </div>
              </div>
            </el-col>
            
            <!-- 右侧：PR 曲线图 -->
            <el-col :span="10">
              <div v-if="evaluationResult.pr_curve_image" class="image-card">
                <div class="analysis-header">
                  <el-icon><Picture /></el-icon>
                  <span>Precision-Recall 曲线图</span>
                </div>
                <el-image 
                  :src="'data:image/png;base64,' + evaluationResult.pr_curve_image" 
                  fit="contain"
                  :preview-src-list="['data:image/png;base64,' + evaluationResult.pr_curve_image]"
                >
                  <template #placeholder>
                    <div class="image-slot">加载中...</div>
                  </template>
                </el-image>
              </div>
            </el-col>
          </el-row>
        </div>

        <div v-if="evaluationResult.status === 'failed'" class="error-alert">
          <el-alert
            title="评估任务失败"
            type="error"
            :description="evaluationResult.error_message"
            show-icon
          />
        </div>
      </div>
    </el-card>

    <!-- 使用指南弹窗 -->
    <el-dialog
      v-model="showGuide"
      title="模型评估与优化 - 使用指南"
      width="60%"
      destroy-on-close
    >
      <div class="guide-content">
        <h4>1. 功能概述</h4>
        <p>本界面用于对 AI 模型的检测/分割效果进行定量分析。系统支持多种评估方式：</p>
        <ul>
            <li><strong>一键导入</strong>：直接导入训练任务自动生成的 <code>evaluation_data.json</code> 文件。</li>
            <li><strong>手动上传</strong>：分别上传预测结果和真实标注的 JSON 文件。</li>
        </ul>
        <p>系统会自动计算 mAP、Precision、Recall 等核心指标，并结合 LLM 大语言模型生成专业的优化建议报告。</p>

        <h4>2. 准备工作</h4>
        <p>您可以使用以下两种文件来源之一：</p>
        <ul>
          <li><strong>训练生成文件 (推荐)</strong>：在“模型开发”模块训练完成后，系统会自动生成 <code>evaluation_data.json</code> 文件（通常位于 <code>run/train/weights</code> 目录附近）。</li>
          <li><strong>手动准备文件</strong>：
            <ul>
                <li>预测结果 JSON：模型自动生成的标注数据（包含置信度）。</li>
                <li>真实标注 JSON：人工校对后的准确标注数据。</li>
            </ul>
          </li>
        </ul>

        <h4>3. 使用步骤</h4>
        <el-steps direction="vertical" :active="4" finish-status="success">
          <el-step title="配置参数" description="输入模型 ID（如 yolov8n）并设置 IOU 阈值（默认 0.5）。"></el-step>
          <el-step title="导入数据" description="点击“一键导入”上传 evaluation_data.json，或分别上传预测/标注文件。"></el-step>
          <el-step title="执行评估" description="点击“开始执行评估”，系统将自动计算各项指标并生成 LLM 报告。"></el-step>
          <el-step title="查看报告" description="评估完成后，您可以查看数值指标、PR 曲线图以及 LLM 提供的优化策略。结果会自动保存至系统设置路径。"></el-step>
        </el-steps>

        <h4>4. 核心指标说明</h4>
        <div class="metrics-desc">
          <p><strong>mAP@0.5</strong>：在 IOU 阈值为 0.5 时的平均精度均值，是衡量模型性能的核心指标。</p>
          <p><strong>mAP@0.5:0.95</strong>：在不同 IOU 阈值下的平均精度均值，反映模型定位的精确度。</p>
          <p><strong>Precision (精确率)</strong>：预测为正样本中实际为正样本的比例，衡量“查准”能力。</p>
          <p><strong>Recall (召回率)</strong>：实际正样本中被正确预测的比例，衡量“查全”能力。</p>
          <p><strong>LLM 智能分析</strong>：AI 专家会针对低分指标，从数据增强、参数调整等维度给出具体优化动作。</p>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="showGuide = false">我知道了</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue';
import { evaluationAPI } from '@/api/evaluation.js';
import { ElMessage } from 'element-plus';
import { MagicStick, Picture, QuestionFilled } from '@element-plus/icons-vue';

const showGuide = ref(false);
const loading = ref(false);
const evaluationRequest = ref({
  model_id: 'yolov8n',
  iou_threshold: 0.5,
});

const predictions = ref('');
const groundTruths = ref('');

const handleFileChange = (file, type) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const content = e.target.result;
      // 验证 JSON 格式
      const parsedData = JSON.parse(content);
      
      if (type === 'combined') {
        if (parsedData.predictions && parsedData.ground_truths) {
          predictions.value = JSON.stringify(parsedData.predictions);
          groundTruths.value = JSON.stringify(parsedData.ground_truths);
          
          if (parsedData.model_id) {
            evaluationRequest.value.model_id = parsedData.model_id;
          }
          
          ElMessage.success('成功导入合并的评估数据文件');
        } else {
          ElMessage.error('文件格式不正确，缺少 predictions 或 ground_truths 字段');
        }
      } else if (type === 'predictions') {
        predictions.value = content;
        ElMessage.success('预测数据上传并解析成功');
      } else {
        groundTruths.value = content;
        ElMessage.success('真实标注上传并解析成功');
      }
    } catch (err) {
      ElMessage.error('文件内容不是有效的 JSON 格式');
    }
  };
  reader.readAsText(file.raw);
};

const evaluationResult = ref(null);

const getStatusType = (status) => {
  switch (status) {
    case 'completed': return 'success';
    case 'running': return 'primary';
    case 'failed': return 'danger';
    case 'pending': return 'info';
    default: return '';
  }
};

const getStatusText = (status) => {
  const map = {
    'completed': '评估完成',
    'running': '正在分析指标...',
    'failed': '评估失败',
    'pending': '等待处理'
  };
  return map[status] || status;
};

const formatLLMAnalysis = (text) => {
  if (!text) return '';
  // 简单的格式化，将换行符转换为 <br>，支持 markdown 风格的列表
  return text.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
};

const startEvaluation = async () => {
  try {
    // 检查是否已上传文件
    if (!predictions.value || !groundTruths.value) {
      ElMessage.warning('请先上传预测结果和真实标注的 JSON 文件');
      return;
    }

    // 解析 JSON 校验
    let parsedPredictions, parsedGroundTruths;
    try {
      parsedPredictions = JSON.parse(predictions.value);
      parsedGroundTruths = JSON.parse(groundTruths.value);
    } catch (e) {
      ElMessage.error('解析文件失败，请确保上传的是有效的 JSON 文件');
      return;
    }

    loading.value = true;
    evaluationResult.value = null;

    const requestData = {
      model_id: evaluationRequest.value.model_id,
      iou_threshold: evaluationRequest.value.iou_threshold,
      predictions: parsedPredictions.map(p => ({
        image_id: p.image_id || 'unknown',
        class_name: p.class_name,
        box: p.box,
        confidence: p.confidence
      })),
      ground_truths: parsedGroundTruths.map(gt => ({
        image_id: gt.image_id || 'unknown',
        class_name: gt.class_name,
        box: gt.box
      })),
      task_id: null
    };

    const response = await evaluationAPI.startEvaluation(evaluationRequest.value.model_id, requestData);
    const evaluationId = response.data.evaluation_id;
    
    // 轮询获取结果
    pollForResult(evaluationId);

  } catch (error) {
    console.error('启动评估失败:', error);
    ElMessage.error('启动评估失败: ' + (error.response?.data?.detail || error.message));
    loading.value = false;
  }
};

const currentPollingInterval = ref(null);
const pollingCounter = ref(0);
const maxPollingAttempts = 30;

onUnmounted(() => {
  stopPolling();
});

const stopPolling = () => {
  if (currentPollingInterval.value) {
    clearInterval(currentPollingInterval.value);
    currentPollingInterval.value = null;
  }
  pollingCounter.value = 0;
};

const pollForResult = (evaluationId) => {
  stopPolling();
  
  currentPollingInterval.value = setInterval(async () => {
    try {
      pollingCounter.value++;
      
      if (pollingCounter.value > maxPollingAttempts) {
        ElMessage.warning('评估任务耗时较长，请稍后刷新列表查看结果');
        stopPolling();
        loading.value = false;
        return;
      }
      
      const response = await evaluationAPI.getEvaluationResult(evaluationId, evaluationRequest.value.model_id);
      const result = response.data;
      evaluationResult.value = result;
      
      if (result.status === 'completed' || result.status === 'failed') {
        stopPolling();
        loading.value = false;
        if (result.status === 'completed') {
          ElMessage.success('模型评估任务已完成，智能报告已生成');
        }
      }
    } catch (error) {
      console.error('获取评估结果失败:', error);
      stopPolling();
      loading.value = false;
    }
  }, 2000);
};
</script>

<style scoped>
.evaluation-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 40px);
}

.title {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.evaluation-form-section {
  margin-bottom: 40px;
}

.evaluation-form-section h3 {
  margin-bottom: 20px;
  color: #606266;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.result-section {
  margin-top: 30px;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
}

.eval-id {
  color: #909399;
  font-size: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-item {
  background-color: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 15px;
  text-align: center;
  transition: all 0.3s;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.metric-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 15px 0 rgba(0,0,0,0.1);
}

.metric-item .label {
  display: block;
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-item .value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.llm-analysis-card, .image-card {
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  overflow: hidden;
  height: 100%;
}

.analysis-header {
  background-color: #f0f9eb;
  padding: 12px 15px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: #67c23a;
  border-bottom: 1px solid #e1f3d8;
}

.image-card .analysis-header {
  background-color: #ecf5ff;
  color: #409eff;
  border-bottom: 1px solid #d9ecff;
}

.analysis-content {
  padding: 20px;
  line-height: 1.8;
  color: #444;
  white-space: pre-wrap;
  font-size: 14px;
}

.el-image {
  padding: 10px;
  width: 100%;
  height: auto;
  min-height: 300px;
}

.error-alert {
  margin-top: 20px;
}

.guide-content h4 {
  margin: 15px 0 10px;
  color: #303133;
}

.guide-content p, .guide-content ul {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.guide-content ul {
  padding-left: 20px;
}

.metrics-desc {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  border-left: 4px solid #909399;
}

.metrics-desc p {
  margin-bottom: 5px;
}

.el-steps {
  margin: 20px 0;
  padding-left: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>