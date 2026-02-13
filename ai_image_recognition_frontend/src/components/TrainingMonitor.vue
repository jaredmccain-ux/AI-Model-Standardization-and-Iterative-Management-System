<template>
  <div class="training-monitor">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>训练监控面板</span>
          <el-button size="small" @click="refreshStatus" :loading="loading">
            刷新状态
          </el-button>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="总任务数" :value="status.total_tasks" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="运行中" :value="status.running_tasks" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="已完成" :value="status.completed_tasks" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="失败" :value="status.failed_tasks" />
        </el-col>
      </el-row>

      <div style="margin-top: 20px;">
        <el-tag :type="status.service_status === 'running' ? 'success' : 'danger'">
          服务状态: {{ status.service_status === 'running' ? '正常' : '异常' }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { trainingAPI } from '../api/training'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const status = ref({
  total_tasks: 0,
  running_tasks: 0,
  completed_tasks: 0,
  failed_tasks: 0,
  service_status: 'unknown'
})

const refreshStatus = async () => {
  try {
    loading.value = true
    const response = await trainingAPI.getTrainingStatus()
    status.value = response.data
  } catch (error) {
    console.error('获取训练状态失败:', error)
    ElMessage.error('获取训练状态失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refreshStatus()
  // 每30秒自动刷新一次
  setInterval(refreshStatus, 30000)
})
</script>

<style scoped>
.training-monitor {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>