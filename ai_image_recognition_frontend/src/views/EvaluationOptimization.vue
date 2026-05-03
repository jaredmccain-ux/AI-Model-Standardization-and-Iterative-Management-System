<template>
  <div class="evaluation-page">
    <el-card class="header-card">
      <div class="header-top">
        <div>
          <h1 class="page-title">评估优化</h1>
          <div class="page-subtitle">从训练产物一键评估，并沉淀评估记录用于后续优化迭代</div>
        </div>
        <div class="header-actions">
          <el-button @click="refreshAll" :loading="loadingAny">刷新</el-button>
        </div>
      </div>
      <div class="project-line">
        <span class="label">当前项目</span>
        <el-tag v-if="currentProject" type="success">{{ currentProject.name }} ({{ currentProject.id }})</el-tag>
        <el-tag v-else type="info">未选择</el-tag>
      </div>
      <el-alert
        v-if="!currentProject"
        type="warning"
        show-icon
        title="未选择项目"
        description="请先在首页创建/选择项目，再进入评估优化。"
        style="margin-top: 12px;"
      />
    </el-card>

    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="一键评估" name="run">
        <el-row :gutter="16">
          <el-col :span="10">
            <el-card class="panel-card">
              <template #header>
                <div class="card-header">
                  <span>评估输入</span>
                  <el-button type="primary" plain @click="loadLatestEvaluationData" :disabled="!currentProject" :loading="loadingEvalData">
                    从最新训练产物加载
                  </el-button>
                </div>
              </template>

              <el-form label-width="110px">
                <el-form-item label="IOU 阈值">
                  <el-slider v-model="iouThreshold" :min="0.3" :max="0.9" :step="0.05" show-input />
                </el-form-item>
              </el-form>

              <div v-if="evaluationData" class="data-summary">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="model_id">{{ evaluationData.model_id || '未知' }}</el-descriptions-item>
                  <el-descriptions-item label="task_id">{{ evaluationData.task_id || '未知' }}</el-descriptions-item>
                  <el-descriptions-item label="predictions">{{ evaluationData.predictions?.length || 0 }}</el-descriptions-item>
                  <el-descriptions-item label="ground_truths">{{ evaluationData.ground_truths?.length || 0 }}</el-descriptions-item>
                </el-descriptions>
                <el-alert
                  v-if="(evaluationData.ground_truths?.length || 0) === 0"
                  type="warning"
                  show-icon
                  title="ground_truths 为 0"
                  description="这会导致评估结果全部为 0。通常原因是：验证集划分到了未标注图片，或 labels/val 下的 txt 为空。请回到“图像标注 → 导入到项目”，确保验证集图片有标注。"
                  style="margin-top: 10px;"
                />
              </div>
              <el-empty v-else description="未加载评估数据" :image-size="90" />

              <div style="margin-top: 14px; display: flex; justify-content: flex-end;">
                <el-button
                  type="primary"
                  @click="startEvaluation"
                  :disabled="!canStartEvaluation"
                  :loading="loadingEvaluation"
                >
                  {{ loadingEvaluation ? '评估中...' : '开始评估' }}
                </el-button>
              </div>
            </el-card>

            <el-card class="panel-card" style="margin-top: 16px;">
              <template #header>
                <div class="card-header">
                  <span>评估日志</span>
                  <el-tag v-if="polling" type="warning">轮询中</el-tag>
                </div>
              </template>
              <el-empty v-if="!evaluationResult" description="暂无评估任务" :image-size="80" />
              <div v-else class="log-box">
                <div class="log-line"><span class="k">evaluation_id</span><span class="v">{{ evaluationResult.evaluation_id }}</span></div>
                <div class="log-line"><span class="k">status</span><span class="v">{{ evaluationResult.status }}</span></div>
                <div class="log-line" v-if="evaluationResult.error_message"><span class="k">error</span><span class="v danger">{{ evaluationResult.error_message }}</span></div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="14">
            <el-card class="panel-card">
              <template #header>
                <div class="card-header">
                  <span>评估结果</span>
                  <el-tag v-if="evaluationResult?.status" :type="statusTagType">{{ statusLabel }}</el-tag>
                </div>
              </template>

              <el-empty v-if="!evaluationResult" description="暂无评估结果" :image-size="120" />

              <div v-else>
                <el-alert
                  v-if="evaluationResult.status === 'failed'"
                  type="error"
                  show-icon
                  title="评估失败"
                  :description="evaluationResult.error_message || '未知错误'"
                  style="margin-bottom: 12px;"
                />

                <div v-if="evaluationResult.status === 'completed'">
                  <el-row :gutter="12" style="margin-bottom: 12px;">
                    <el-col :span="6"><el-card class="metric-card"><div class="metric-k">mAP@0.5</div><div class="metric-v">{{ fmtNum(evaluationResult.metrics?.mAP50) }}</div></el-card></el-col>
                    <el-col :span="6"><el-card class="metric-card"><div class="metric-k">mAP@0.5:0.95</div><div class="metric-v">{{ fmtNum(evaluationResult.metrics?.mAP50_95) }}</div></el-card></el-col>
                    <el-col :span="6"><el-card class="metric-card"><div class="metric-k">Precision</div><div class="metric-v">{{ fmtNum(evaluationResult.metrics?.precision) }}</div></el-card></el-col>
                    <el-col :span="6"><el-card class="metric-card"><div class="metric-k">Recall</div><div class="metric-v">{{ fmtNum(evaluationResult.metrics?.recall) }}</div></el-card></el-col>
                  </el-row>

                  <el-divider content-position="left">PR 曲线</el-divider>
                  <div v-if="prCurveImage" class="pr-image-wrap">
                    <img :src="prCurveImage" alt="PR Curve" />
                  </div>
                  <el-empty v-else description="暂无 PR 曲线" :image-size="70" />

                  <el-divider content-position="left">分类别指标</el-divider>
                  <el-table :data="classMetricRows" height="240" style="width: 100%;">
                    <el-table-column prop="className" label="类别" min-width="160" />
                    <el-table-column prop="precision" label="Precision" width="120" />
                    <el-table-column prop="recall" label="Recall" width="120" />
                    <el-table-column prop="f1" label="F1" width="120" />
                    <el-table-column prop="ap" label="AP" width="120" />
                  </el-table>

                  <el-divider content-position="left">优化建议</el-divider>
                  <el-input
                    type="textarea"
                    :rows="10"
                    readonly
                    :model-value="evaluationResult.llm_analysis || ''"
                    placeholder="暂无分析报告"
                  />
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="历史评估" name="history">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>项目评估记录</span>
              <el-button @click="refreshHistory" :disabled="!currentProject" :loading="loadingHistory">刷新列表</el-button>
            </div>
          </template>

          <el-empty v-if="!currentProject" description="未选择项目" :image-size="90" />

          <div v-else>
            <el-table
              :data="projectEvaluations"
              style="width: 100%;"
              height="340"
              @row-click="selectHistoryRow"
            >
              <el-table-column prop="evaluation_id" label="evaluation_id" min-width="220" />
              <el-table-column prop="created_at" label="创建时间" min-width="180" />
              <el-table-column label="mAP50" width="120">
                <template #default="{ row }">{{ fmtNum(row.summary?.mAP50) }}</template>
              </el-table-column>
              <el-table-column label="mAP50_95" width="120">
                <template #default="{ row }">{{ fmtNum(row.summary?.mAP50_95) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button size="small" @click.stop="loadHistoryDetail(row.evaluation_id)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left">详情</el-divider>
            <el-empty v-if="!historyDetail" description="点击上方记录查看详情" :image-size="90" />
            <div v-else>
              <el-row :gutter="12" style="margin-bottom: 12px;">
                <el-col :span="6"><el-card class="metric-card"><div class="metric-k">mAP@0.5</div><div class="metric-v">{{ fmtNum(historyDetail.metrics?.mAP50) }}</div></el-card></el-col>
                <el-col :span="6"><el-card class="metric-card"><div class="metric-k">mAP@0.5:0.95</div><div class="metric-v">{{ fmtNum(historyDetail.metrics?.mAP50_95) }}</div></el-card></el-col>
                <el-col :span="6"><el-card class="metric-card"><div class="metric-k">Precision</div><div class="metric-v">{{ fmtNum(historyDetail.metrics?.precision) }}</div></el-card></el-col>
                <el-col :span="6"><el-card class="metric-card"><div class="metric-k">Recall</div><div class="metric-v">{{ fmtNum(historyDetail.metrics?.recall) }}</div></el-card></el-col>
              </el-row>

              <el-input
                type="textarea"
                :rows="14"
                readonly
                :model-value="historyDetail.report_md || ''"
                placeholder="暂无报告"
              />
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { evaluationAPI } from '@/api/evaluation.js';
import { getCurrentProject } from '@/utils/projectManager.js';

const activeTab = ref('run');
const currentProject = ref(getCurrentProject());

const iouThreshold = ref(0.5);
const evaluationData = ref(null);
const evaluationResult = ref(null);

const loadingEvalData = ref(false);
const loadingEvaluation = ref(false);
const loadingHistory = ref(false);

const projectEvaluations = ref([]);
const historyDetail = ref(null);

const polling = ref(false);
const pollingTimer = ref(null);
const pollingAttempts = ref(0);
const maxPollingAttempts = 60;

const loadingAny = computed(() => loadingEvalData.value || loadingEvaluation.value || loadingHistory.value);

const canStartEvaluation = computed(() => {
  const preds = evaluationData.value?.predictions;
  const gts = evaluationData.value?.ground_truths;
  return (
    !!currentProject.value?.id &&
    !!evaluationData.value?.model_id &&
    Array.isArray(preds) &&
    Array.isArray(gts) &&
    preds.length > 0 &&
    gts.length > 0
  );
});

const prCurveImage = computed(() => {
  const raw = evaluationResult.value?.pr_curve_image;
  if (!raw) return null;
  return `data:image/png;base64,${raw}`;
});

const statusLabel = computed(() => {
  const s = evaluationResult.value?.status;
  if (s === 'pending') return '等待中';
  if (s === 'running') return '运行中';
  if (s === 'completed') return '已完成';
  if (s === 'failed') return '失败';
  return s || '未知';
});

const statusTagType = computed(() => {
  const s = evaluationResult.value?.status;
  if (s === 'completed') return 'success';
  if (s === 'failed') return 'danger';
  if (s === 'running') return 'warning';
  return 'info';
});

const classMetricRows = computed(() => {
  const classMetrics = evaluationResult.value?.metrics?.class_metrics || {};
  const rows = [];
  for (const [className, m] of Object.entries(classMetrics)) {
    rows.push({
      className,
      precision: fmtNum(m?.precision),
      recall: fmtNum(m?.recall),
      f1: fmtNum(m?.f1_score),
      ap: fmtNum(m?.ap),
    });
  }
  rows.sort((a, b) => String(a.className).localeCompare(String(b.className)));
  return rows;
});

function fmtNum(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '-';
  return n.toFixed(4);
}

function stopPolling() {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value);
    pollingTimer.value = null;
  }
  polling.value = false;
  pollingAttempts.value = 0;
}

async function pollResult(evaluationId, modelId) {
  stopPolling();
  polling.value = true;
  pollingTimer.value = setInterval(async () => {
    try {
      pollingAttempts.value += 1;
      if (pollingAttempts.value > maxPollingAttempts) {
        stopPolling();
        loadingEvaluation.value = false;
        ElMessage.warning('评估轮询超时，请稍后在历史记录中查看');
        return;
      }
      const resp = await evaluationAPI.getEvaluationResult(evaluationId, modelId);
      evaluationResult.value = resp.data;
      if (['completed', 'failed'].includes(resp.data.status)) {
        stopPolling();
        loadingEvaluation.value = false;
        refreshHistory();
      }
    } catch (e) {
      console.error('轮询评估结果失败:', e);
      stopPolling();
      loadingEvaluation.value = false;
      ElMessage.error('获取评估结果失败');
    }
  }, 2000);
}

async function loadLatestEvaluationData() {
  currentProject.value = getCurrentProject();
  if (!currentProject.value?.id) {
    ElMessage.warning('请先在首页创建/选择项目');
    return;
  }
  loadingEvalData.value = true;
  try {
    const resp = await evaluationAPI.getLatestEvaluationData(currentProject.value.id);
    evaluationData.value = resp.data?.data || null;
    if (!evaluationData.value) {
      ElMessage.warning('未找到可用的 evaluation_data.json');
    } else {
      ElMessage.success('已加载最新训练产物的评估数据');
    }
  } catch (e) {
    console.error('加载评估数据失败:', e);
    ElMessage.error('加载评估数据失败: ' + (e.response?.data?.detail || e.message));
  } finally {
    loadingEvalData.value = false;
  }
}

async function startEvaluation() {
  currentProject.value = getCurrentProject();
  if (!canStartEvaluation.value) {
    const preds = evaluationData.value?.predictions;
    const gts = evaluationData.value?.ground_truths;
    if (!Array.isArray(preds) || preds.length === 0) {
      ElMessage.warning('评估数据不完整：predictions 为空');
      return;
    }
    if (!Array.isArray(gts) || gts.length === 0) {
      ElMessage.warning('评估数据不完整：ground_truths 为空（验证集标签可能缺失或为空）');
      return;
    }
    ElMessage.warning('请先加载评估数据');
    return;
  }
  loadingEvaluation.value = true;
  evaluationResult.value = null;
  try {
    const payload = {
      model_id: evaluationData.value.model_id,
      task_id: evaluationData.value.task_id || null,
      project_id: currentProject.value.id,
      iou_threshold: Number(iouThreshold.value || 0.5),
      predictions: evaluationData.value.predictions,
      ground_truths: evaluationData.value.ground_truths,
    };
    const resp = await evaluationAPI.startEvaluation(evaluationData.value.model_id, payload);
    const evaluationId = resp.data?.evaluation_id;
    if (!evaluationId) {
      throw new Error('后端未返回 evaluation_id');
    }
    await pollResult(evaluationId, evaluationData.value.model_id);
  } catch (e) {
    console.error('启动评估失败:', e);
    loadingEvaluation.value = false;
    ElMessage.error('启动评估失败: ' + (e.response?.data?.detail || e.message));
  }
}

async function refreshHistory() {
  currentProject.value = getCurrentProject();
  if (!currentProject.value?.id) return;
  loadingHistory.value = true;
  try {
    const resp = await evaluationAPI.listProjectEvaluations(currentProject.value.id, 80);
    projectEvaluations.value = resp.data?.evaluations || [];
  } catch (e) {
    console.error('刷新历史评估失败:', e);
    ElMessage.error('刷新历史评估失败: ' + (e.response?.data?.detail || e.message));
  } finally {
    loadingHistory.value = false;
  }
}

async function loadHistoryDetail(evaluationId) {
  currentProject.value = getCurrentProject();
  if (!currentProject.value?.id) return;
  loadingHistory.value = true;
  try {
    const resp = await evaluationAPI.getProjectEvaluation(currentProject.value.id, evaluationId);
    historyDetail.value = resp.data || null;
  } catch (e) {
    console.error('加载评估详情失败:', e);
    ElMessage.error('加载评估详情失败: ' + (e.response?.data?.detail || e.message));
  } finally {
    loadingHistory.value = false;
  }
}

function selectHistoryRow(row) {
  if (!row?.evaluation_id) return;
  loadHistoryDetail(row.evaluation_id);
}

async function refreshAll() {
  currentProject.value = getCurrentProject();
  await refreshHistory();
}

onMounted(() => {
  refreshAll();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.evaluation-page {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #303133;
}

.page-subtitle {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}

.project-line {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.project-line .label {
  color: #606266;
  font-size: 13px;
}

.main-tabs {
  margin-top: 10px;
}

.panel-card {
  border-radius: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.data-summary {
  margin-top: 12px;
}

.metric-card {
  border-radius: 10px;
}

.metric-k {
  color: #909399;
  font-size: 12px;
}

.metric-v {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.pr-image-wrap {
  width: 100%;
  overflow: hidden;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
}

.pr-image-wrap img {
  width: 100%;
  display: block;
}

.log-box {
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 10px;
  border: 1px solid #ebeef5;
}

.log-line {
  display: flex;
  gap: 10px;
  padding: 4px 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
}

.log-line .k {
  width: 110px;
  color: #606266;
}

.log-line .v {
  color: #303133;
}

.log-line .v.danger {
  color: #f56c6c;
}
</style>
