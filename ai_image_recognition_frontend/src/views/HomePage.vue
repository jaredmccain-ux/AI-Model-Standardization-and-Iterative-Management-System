<template>
  <div class="home-container">
    <section class="hero-section">
      <div class="hero-content">
        <p class="eyebrow">Visio AI Workflow</p>
        <h1 class="title">视觉类AI模型标准化迭代管理系统</h1>
        <p class="subtitle">
          集成 <span class="highlight">YOLOv8</span> 全流程开发、
          <span class="highlight">知识蒸馏</span> 与
          <span class="highlight">增量学习</span> 的一站式平台。
        </p>
        <p class="description">
          先创建或选择项目，再进入标注、训练和评估流程。项目级数据、训练产物和评估结果都统一收口管理。
        </p>
        <div class="action-buttons">
          <el-button type="primary" size="large" @click="navigateTo('/model-development', true)">
            开始模型训练
          </el-button>
          <el-button size="large" @click="navigateTo('/image-annotation', true)">
            数据标注
          </el-button>
        </div>
      </div>

      <div class="hero-visual">
        <div class="visual-card visual-card-top">
          <el-icon><Cpu /></el-icon>
          <div>
            <h4>知识蒸馏</h4>
            <p>Teacher -> Student</p>
          </div>
        </div>
        <div class="visual-core">
          <img src="/vite.svg" alt="AI Core" />
        </div>
        <div class="visual-card visual-card-middle">
          <el-icon><DataAnalysis /></el-icon>
          <div>
            <h4>LLM 评估</h4>
            <p>智能分析优化建议</p>
          </div>
        </div>
        <div class="visual-card visual-card-bottom">
          <el-icon><VideoPlay /></el-icon>
          <div>
            <h4>增量迭代</h4>
            <p>持续演进训练闭环</p>
          </div>
        </div>
      </div>
    </section>

    <section ref="projectSection" class="project-section">
      <el-card class="project-card" shadow="hover">
        <template #header>
          <div class="project-header">
            <div class="project-title">
              <el-icon><FolderOpened /></el-icon>
              <span>项目管理（推荐：先创建/选择项目，再按流程操作）</span>
            </div>
            <div v-if="currentProject" class="project-current">
              当前项目：<strong>{{ currentProject.name }}</strong>
            </div>
          </div>
        </template>

        <div class="project-actions">
          <el-input
            v-model="projectName"
            placeholder="输入项目名称，例如：缺陷检测_2026Q1"
            class="project-input"
            @keyup.enter="createProject"
          />
          <el-button type="primary" :loading="creating" @click="createProject">
            创建项目
          </el-button>
          <el-button :loading="loading" @click="loadProjects">
            刷新列表
          </el-button>
          <el-button
            v-if="currentProject"
            type="warning"
            plain
            @click="clearSelectedProject"
          >
            退出当前项目
          </el-button>
        </div>

        <el-empty
          v-if="!loading && projects.length === 0"
          description="暂无项目，请先创建一个。"
        />

        <div v-else class="project-list">
          <el-card
            v-for="project in projects"
            :key="project.project_id"
            class="project-item"
            shadow="never"
          >
            <div class="project-item-main">
              <div>
                <div class="project-item-name">{{ project.name }}</div>
                <div class="project-item-meta">
                  <span>ID: {{ project.project_id }}</span>
                  <span>更新时间：{{ formatTime(project.updated_at || project.created_at) }}</span>
                  <el-tag v-if="project.dataset_yaml_path" size="small" type="success">已生成数据集</el-tag>
                </div>
              </div>

              <div class="project-item-actions">
                <el-button size="small" type="primary" @click="selectProject(project)">
                  选择
                </el-button>
                <el-button size="small" @click="navigateTo('/image-annotation', true, project)">
                  进入标注
                </el-button>
                <el-button
                  size="small"
                  :loading="renamingProjectId === project.project_id"
                  @click="renameProject(project)"
                >
                  重命名
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :loading="deletingProjectId === project.project_id"
                  @click="deleteProject(project)"
                >
                  删除
                </el-button>
              </div>
            </div>
          </el-card>
        </div>
      </el-card>
    </section>

    <section class="highlights-section">
      <div class="highlight-item">
        <div class="icon-wrapper">
          <el-icon><Cpu /></el-icon>
        </div>
        <h3>高效训练</h3>
        <p>支持冻结策略与多模式训练，缩短迭代周期。</p>
      </div>
      <div class="highlight-item">
        <div class="icon-wrapper">
          <el-icon><UploadFilled /></el-icon>
        </div>
        <h3>数据闭环</h3>
        <p>标注、训练、评估全部围绕项目统一归档管理。</p>
      </div>
      <div class="highlight-item">
        <div class="icon-wrapper">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <h3>智能诊断</h3>
        <p>结合 LLM 报告快速定位指标短板和优化方向。</p>
      </div>
      <div class="highlight-item">
        <div class="icon-wrapper">
          <el-icon><VideoPlay /></el-icon>
        </div>
        <h3>持续迭代</h3>
        <p>增量训练与蒸馏能力帮助模型稳定演进。</p>
      </div>
    </section>

    <section ref="featuresSection" class="features-section">
      <h2 class="section-title">核心功能</h2>
      <div class="features-grid">
        <div class="feature-card" v-for="feature in features" :key="feature.route">
          <div class="feature-header">
            <el-icon :size="30">
              <component :is="feature.icon" />
            </el-icon>
            <h3>{{ feature.title }}</h3>
          </div>
          <p class="feature-description">{{ feature.description }}</p>
          <el-button type="primary" text @click="navigateTo(feature.route, true)">
            立即体验
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </section>

    <section class="workflow-section">
      <h2 class="section-title">标准化迭代流程</h2>
      <div class="workflow-grid">
        <div class="workflow-card" v-for="(step, index) in workflowSteps" :key="step.title">
          <div class="workflow-card-header">
            <span class="step-number">0{{ index + 1 }}</span>
            <el-icon class="step-icon">
              <component :is="step.icon" />
            </el-icon>
          </div>
          <div class="workflow-card-body">
            <h4>{{ step.title }}</h4>
            <p>{{ step.description }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowRight,
  Cpu,
  DataAnalysis,
  FolderOpened,
  Monitor,
  PictureFilled,
  UploadFilled,
  VideoPlay
} from '@element-plus/icons-vue'
import axios from 'axios'

import { getApiUrl } from '@/config/api.js'
import {
  getCurrentProject,
  setCurrentProject,
  clearCurrentProject as clearStoredCurrentProject
} from '@/utils/projectManager.js'

const router = useRouter()
const featuresSection = ref(null)
const projectSection = ref(null)

const projectName = ref('')
const projects = ref([])
const currentProject = ref(null)
const loading = ref(false)
const creating = ref(false)
const deletingProjectId = ref('')
const renamingProjectId = ref('')

const features = [
  {
    icon: PictureFilled,
    title: '图像标注',
    description: '围绕项目集中管理图片、标注数据和增广结果。',
    route: '/image-annotation'
  },
  {
    icon: Monitor,
    title: '模型开发',
    description: '配置训练策略、监控训练日志并沉淀模型产物。',
    route: '/model-development'
  },
  {
    icon: DataAnalysis,
    title: '评估优化',
    description: '生成指标报告并基于 LLM 分析给出优化建议。',
    route: '/evaluation-optimization'
  }
]

const workflowSteps = [
  { icon: UploadFilled, title: '数据准备', description: '导入图片并完成项目级标注管理。' },
  { icon: Cpu, title: '模型训练', description: '选择训练模式并启动迭代。' },
  { icon: DataAnalysis, title: '评估分析', description: '查看指标、PR 曲线与分析报告。' },
  { icon: VideoPlay, title: '迭代优化', description: '基于评估结果继续优化和增量更新。' }
]

const scrollToProjectSection = () => {
  projectSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const syncStoredProject = () => {
  const stored = getCurrentProject()
  if (!stored) {
    currentProject.value = null
    return
  }

  const matched = projects.value.find(project => project.project_id === stored.id)
  if (!matched) {
    clearStoredCurrentProject()
    currentProject.value = null
    return
  }

  currentProject.value = {
    id: matched.project_id,
    name: matched.name
  }
}

const loadProjects = async () => {
  try {
    loading.value = true
    const response = await axios.get(`${getApiUrl()}/api/projects`)
    projects.value = response.data.projects || []
    syncStoredProject()
  } catch (error) {
    projects.value = []
    ElMessage.error('获取项目列表失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const selectProject = (project, silent = false) => {
  const payload = {
    id: project.project_id,
    name: project.name
  }
  setCurrentProject(payload)
  currentProject.value = payload
  if (!silent) {
    ElMessage.success(`已切换到项目：${project.name}`)
  }
}

const createProject = async () => {
  if (!projectName.value.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }

  try {
    creating.value = true
    const formData = new FormData()
    formData.append('name', projectName.value.trim())
    const response = await axios.post(`${getApiUrl()}/api/projects`, formData)
    selectProject(response.data, true)
    projectName.value = ''
    await loadProjects()
    ElMessage.success('项目已创建并选中')
  } catch (error) {
    ElMessage.error('创建项目失败：' + (error.response?.data?.detail || error.message))
  } finally {
    creating.value = false
  }
}

const clearSelectedProject = () => {
  clearStoredCurrentProject()
  currentProject.value = null
  ElMessage.success('已退出当前项目')
}

const renameProject = async (project) => {
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '请输入新的项目名称',
      '重命名项目',
      {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputValue: project.name,
        inputPlaceholder: '例如：缺陷检测_2026Q2',
        inputValidator: (value) => {
          if (!value || !value.trim()) {
            return '项目名称不能为空'
          }
          if (value.trim() === project.name) {
            return '新名称不能与当前名称相同'
          }
          return true
        }
      }
    )
  } catch {
    return
  }

  try {
    renamingProjectId.value = project.project_id
    const formData = new FormData()
    formData.append('name', promptResult.value.trim())
    const response = await axios.put(
      `${getApiUrl()}/api/projects/${project.project_id}`,
      formData
    )

    if (currentProject.value?.id === project.project_id) {
      const payload = {
        id: project.project_id,
        name: response.data.name
      }
      setCurrentProject(payload)
      currentProject.value = payload
    }

    await loadProjects()
    ElMessage.success(`项目已重命名为：${response.data.name}`)
  } catch (error) {
    ElMessage.error('重命名项目失败：' + (error.response?.data?.detail || error.message))
  } finally {
    renamingProjectId.value = ''
  }
}

const deleteProject = async (project) => {
  try {
    await ElMessageBox.confirm(
      `确定删除项目「${project.name}」吗？该项目下的数据、训练结果和评估结果都会被永久删除。`,
      '删除项目',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  try {
    deletingProjectId.value = project.project_id
    await axios.delete(`${getApiUrl()}/api/projects/${project.project_id}`)

    if (currentProject.value?.id === project.project_id) {
      clearStoredCurrentProject()
      currentProject.value = null
    }

    await loadProjects()
    ElMessage.success(`已删除项目：${project.name}`)
  } catch (error) {
    ElMessage.error('删除项目失败：' + (error.response?.data?.detail || error.message))
  } finally {
    deletingProjectId.value = ''
  }
}

const navigateTo = async (route, requireProject = false, project = null) => {
  if (project) {
    selectProject(project, true)
  }

  if (requireProject && !currentProject.value?.id) {
    ElMessage.info('请先创建或选择项目')
    scrollToProjectSection()
    return
  }

  await router.push(route)
}

const formatTime = (value) => {
  if (!value) return '暂无'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(async () => {
  currentProject.value = getCurrentProject()
  await loadProjects()
})
</script>

<style scoped>
.home-container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px;
}

.hero-section {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 440px);
  gap: 32px;
  align-items: center;
  margin: 24px 0 48px;
}

.eyebrow {
  margin: 0 0 12px;
  color: #0f766e;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.title {
  margin: 0 0 18px;
  font-size: clamp(2.6rem, 5vw, 4.8rem);
  line-height: 1.02;
  font-weight: 900;
  color: #0f172a;
}

.subtitle {
  margin: 0 0 16px;
  font-size: 1.5rem;
  line-height: 1.45;
  color: #334155;
}

.description {
  margin: 0 0 28px;
  font-size: 1.08rem;
  line-height: 1.85;
  color: #475569;
  max-width: 720px;
}

.highlight {
  color: #409eff;
  font-weight: 800;
}

.action-buttons {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.hero-visual {
  position: relative;
  min-height: 420px;
  border-radius: 32px;
  background:
    radial-gradient(circle at top, rgba(64, 158, 255, 0.18), transparent 42%),
    linear-gradient(145deg, #f8fbff 0%, #eef5ff 52%, #f4f8fb 100%);
  border: 1px solid rgba(148, 163, 184, 0.2);
  overflow: hidden;
}

.visual-core {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.visual-core img {
  width: min(68%, 280px);
  filter: drop-shadow(0 22px 40px rgba(64, 158, 255, 0.2));
}

.visual-card {
  position: absolute;
  display: flex;
  gap: 12px;
  align-items: center;
  width: 210px;
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.visual-card :deep(svg) {
  font-size: 24px;
  color: #409eff;
}

.visual-card h4 {
  margin: 0 0 4px;
  font-size: 1rem;
  color: #0f172a;
}

.visual-card p {
  margin: 0;
  font-size: 0.88rem;
  color: #64748b;
}

.visual-card-top {
  top: 28px;
  right: 30px;
}

.visual-card-middle {
  left: 24px;
  top: 154px;
}

.visual-card-bottom {
  right: 18px;
  bottom: 28px;
}

.project-section {
  margin: 0 0 40px;
  scroll-margin-top: 80px;
}

.project-card {
  border-radius: 24px;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.project-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.2rem;
  font-weight: 700;
  color: #1f2937;
}

.project-current {
  color: #409eff;
}

.project-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.project-input {
  max-width: 420px;
}

.project-list {
  display: grid;
  gap: 12px;
}

.project-item {
  border-radius: 18px;
}

.project-item-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.project-item-name {
  margin-bottom: 6px;
  font-size: 1.08rem;
  font-weight: 700;
  color: #0f172a;
}

.project-item-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.9rem;
  color: #64748b;
}

.project-item-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.highlights-section {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin: 0 0 56px;
}

.highlight-item {
  padding: 22px 20px;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.icon-wrapper {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  margin-bottom: 16px;
}

.icon-wrapper :deep(svg) {
  font-size: 24px;
}

.highlight-item h3 {
  margin: 0 0 10px;
  color: #0f172a;
}

.highlight-item p {
  margin: 0;
  line-height: 1.7;
  color: #64748b;
}

.features-section,
.workflow-section {
  margin: 0 0 56px;
}

.section-title {
  margin: 0 0 28px;
  font-size: 2rem;
  color: #111827;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.feature-card {
  padding: 28px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.feature-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  color: #409eff;
}

.feature-header h3 {
  margin: 0;
  color: #0f172a;
}

.feature-description {
  min-height: 72px;
  margin: 0 0 16px;
  line-height: 1.8;
  color: #475569;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.workflow-card {
  padding: 22px;
  border-radius: 22px;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
  border: 1px solid rgba(64, 158, 255, 0.18);
}

.workflow-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: #409eff;
  color: #fff;
  font-weight: 700;
}

.step-icon {
  color: #409eff;
  font-size: 24px;
}

.workflow-card-body h4 {
  margin: 0 0 10px;
  color: #0f172a;
}

.workflow-card-body p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 1100px) {
  .hero-section,
  .features-grid,
  .workflow-grid,
  .highlights-section {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .home-container {
    padding: 18px;
  }

  .hero-section,
  .features-grid,
  .workflow-grid,
  .highlights-section {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    min-height: 340px;
  }

  .visual-card {
    width: calc(100% - 32px);
    left: 16px;
    right: 16px;
  }

  .visual-card-top {
    top: 18px;
  }

  .visual-card-middle {
    top: 122px;
  }

  .visual-card-bottom {
    bottom: 18px;
  }

  .project-item-main {
    align-items: flex-start;
  }

  .project-item-actions {
    width: 100%;
  }
}
</style>
