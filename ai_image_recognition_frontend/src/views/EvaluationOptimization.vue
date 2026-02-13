<template>
  <div class="evaluation-container">
    <h1>模型评估与优化</h1>

    <!-- 评估表单 -->
    <div class="evaluation-form">
      <h2>启动评估</h2>
      <form @submit.prevent="startEvaluation">
        <div class="form-group">
          <label for="model-id">模型ID:</label>
          <input type="text" id="model-id" v-model="evaluationRequest.model_id" required>
        </div>
        <div class="form-group">
          <label for="iou-threshold">IOU阈值:</label>
          <input type="number" id="iou-threshold" v-model.number="evaluationRequest.iou_threshold" step="0.05" min="0" max="1" required>
        </div>
        <div class="form-group">
          <label for="predictions">预测数据 (JSON):</label>
          <textarea id="predictions" v-model="predictions" rows="5" required></textarea>
        </div>
        <div class="form-group">
          <label for="ground-truths">真实标注 (JSON):</label>
          <textarea id="ground-truths" v-model="groundTruths" rows="5" required></textarea>
        </div>
        <button type="submit" :disabled="loading">
          {{ loading ? '评估中...' : '开始评估' }}
        </button>
      </form>
    </div>

    <!-- 评估结果 -->
    <div v-if="evaluationResult" class="evaluation-result">
      <h2>评估结果 (ID: {{ evaluationResult.evaluation_id }})</h2>
      <p><strong>状态:</strong> {{ evaluationResult.status }}</p>
      <div v-if="evaluationResult.status === 'completed'">
        <p><strong>mAP@0.5:</strong> {{ evaluationResult.mAP50.toFixed(4) }}</p>
        <p><strong>mAP@0.5:0.95:</strong> {{ evaluationResult.mAP50_95.toFixed(4) }}</p>
        <p><strong>精确率:</strong> {{ evaluationResult.precision.toFixed(4) }}</p>
        <p><strong>召回率:</strong> {{ evaluationResult.recall.toFixed(4) }}</p>
        <p><strong>F1分数:</strong> {{ evaluationResult.f1_score.toFixed(4) }}</p>
        
        <!-- PR曲线 -->
        <div v-if="prCurveImage">
          <h3>PR曲线</h3>
          <img :src="prCurveImage" alt="PR Curve">
        </div>
      </div>
      <div v-if="evaluationResult.status === 'failed'">
        <p><strong>错误信息:</strong> {{ evaluationResult.error_message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue';
import { evaluationAPI } from '@/api/evaluation.js';

const loading = ref(false);
const evaluationRequest = ref({
  model_id: 'yolov8n',
  iou_threshold: 0.5,
});
const predictions = ref(JSON.stringify([
  { class_name: 'person', box: [10, 10, 50, 50], confidence: 0.9 },
  { class_name: 'car', box: [60, 60, 100, 100], confidence: 0.85 }
], null, 2));
const groundTruths = ref(JSON.stringify([
  { class_name: 'person', box: [12, 12, 48, 48] },
  { class_name: 'car', box: [65, 65, 95, 95] }
], null, 2));
const evaluationResult = ref(null);
const prCurveImage = ref(null);

const startEvaluation = async () => {
  loading.value = true;
  evaluationResult.value = null;
  prCurveImage.value = null;

  try {
    // 解析JSON字符串并转换为正确的格式
    const parsedPredictions = JSON.parse(predictions.value);
    const parsedGroundTruths = JSON.parse(groundTruths.value);
    
    // 构建与后端EvaluationRequest模型匹配的请求数据
    const requestData = {
      // 后端EvaluationRequest模型需要model_id字段
      model_id: evaluationRequest.value.model_id,
      iou_threshold: evaluationRequest.value.iou_threshold,
      predictions: parsedPredictions.map(p => ({
        class_name: p.class_name,
        box: p.box,
        confidence: p.confidence
      })),
      ground_truths: parsedGroundTruths.map(gt => ({
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
    loading.value = false;
  }
};

// 使用ref存储当前轮询的interval ID和计数器
const currentPollingInterval = ref(null);
const pollingCounter = ref(0);
const maxPollingAttempts = 30; // 最多轮询30次，约1分钟

// 组件卸载时清除轮询
onUnmounted(() => {
  stopPolling();
});

// 停止轮询的辅助函数
const stopPolling = () => {
  if (currentPollingInterval.value) {
    clearInterval(currentPollingInterval.value);
    currentPollingInterval.value = null;
  }
  pollingCounter.value = 0;
};

const pollForResult = (evaluationId) => {
  // 停止任何现有的轮询
  stopPolling();
  
  // 开始新的轮询
  currentPollingInterval.value = setInterval(async () => {
    try {
      // 增加计数器
      pollingCounter.value++;
      
      // 如果超过最大尝试次数，停止轮询
      if (pollingCounter.value > maxPollingAttempts) {
        console.warn('评估轮询超时，已停止轮询');
        stopPolling();
        loading.value = false;
        return;
      }
      
      const response = await evaluationAPI.getEvaluationResult(evaluationId, evaluationRequest.value.model_id);
      const result = response.data;

      // 更新结果，无论状态如何
      evaluationResult.value = result;
      
      // 检查是否完成或失败
      if (result.status === 'completed' || result.status === 'failed') {
        stopPolling();
        loading.value = false;
        
        if (result.status === 'completed' && result.pr_curve_data) {
          // 后端应返回base64编码的PR曲线图像
          prCurveImage.value = `data:image/png;base64,${result.pr_curve_data}`;
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
  font-family: sans-serif;
}

.evaluation-form {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
}

input[type="text"],
input[type="number"],
textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

button {
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background-color: #ccc;
}

.evaluation-result {
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

.evaluation-result img {
  max-width: 100%;
  height: auto;
}
</style>