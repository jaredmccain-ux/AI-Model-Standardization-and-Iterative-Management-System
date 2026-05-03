<template>
  <div class="settings-page">
    <el-card class="header-card">
      <h1>系统设置</h1>
      <p>配置系统全局参数</p>
    </el-card>

    <el-card class="settings-form-card" style="margin-top: 20px;">
      <el-form :model="settings" label-width="150px" v-loading="loading">
        <el-form-item label="模型训练输出路径">
          <div style="display: flex; width: 100%; gap: 10px;">
            <el-input v-model="settings.training_output_path" placeholder="例如: runs/train" style="flex: 1;">
               <template #append>
                  <el-button :icon="Folder" @click="selectOutputFolder" title="选择文件夹" />
               </template>
            </el-input>
            <el-button type="primary" @click="saveSetting('training_output_path')">保存</el-button>
          </div>
          <div class="form-tip">指定模型训练结果（权重、日志等）的默认保存目录。支持绝对路径或相对路径。</div>
        </el-form-item>
        
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder } from '@element-plus/icons-vue'
import axios from 'axios'
import { getApiUrl } from '@/config/api.js'

const loading = ref(false)
const settings = reactive({
  training_output_path: ''
})

const selectOutputFolder = async () => {
  try {
    const response = await axios.get(`${getApiUrl()}/api/settings/select-path`)
    if (response.data.path) {
      settings.training_output_path = response.data.path
    }
  } catch (error) {
    console.error('选择路径失败:', error)
    ElMessage.error('无法打开文件夹选择器')
  }
}

const fetchSettings = async () => {
  loading.value = true
  try {
    const response = await axios.get(`${getApiUrl()}/api/settings/`)
    const data = response.data
    // Convert array to object for easier binding
    data.forEach(item => {
      // Allow dynamic keys or pre-defined keys
      settings[item.key] = item.value
    })
  } catch (error) {
    console.error('获取设置失败:', error)
    ElMessage.error('获取设置失败')
  } finally {
    loading.value = false
  }
}

const saveSetting = async (key) => {
  try {
    await axios.post(`${getApiUrl()}/api/settings/`, {
      key: key,
      value: settings[key],
      description: key === 'training_output_path' ? '模型训练结果输出路径' : ''
    })
    ElMessage.success('设置已保存')
  } catch (error) {
    console.error('保存设置失败:', error)
    ElMessage.error('保存设置失败')
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.settings-page {
  padding: 20px;
}
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
