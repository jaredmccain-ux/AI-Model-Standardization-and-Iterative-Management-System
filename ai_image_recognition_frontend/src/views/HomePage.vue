<template>
  <div class="home-container">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="title">AI 图像识别标准化迭代系统</h1>
        <p class="subtitle">
          集成 <span class="highlight">YOLOv8</span> 全流程开发、
          <span class="highlight">知识蒸馏</span> 与 
          <span class="highlight">增量学习</span> 的下一代 AI 平台
        </p>
        <p class="description">
          从数据标注到模型评估，只需一个平台。内置 LLM 智能分析助手，让模型优化不再盲目。
        </p>
        <div class="action-buttons">
          <el-button type="primary" size="large" @click="navigateTo('/model-development')" class="cta-btn">
            <el-icon class="el-icon--left"><Monitor /></el-icon>
            开始模型训练
          </el-button>
          <el-button size="large" @click="navigateTo('/image-annotation')" class="secondary-btn">
            <el-icon class="el-icon--left"><Edit /></el-icon>
            数据标注
          </el-button>
        </div>
      </div>
      <div class="hero-image">
        <div class="floating-cards">
          <el-card class="float-card card-1" shadow="hover">
            <div class="card-icon"><el-icon><Cpu /></el-icon></div>
            <div class="card-text">
              <h4>知识蒸馏</h4>
              <p>Teacher → Student</p>
            </div>
          </el-card>
          <el-card class="float-card card-2" shadow="hover">
            <div class="card-icon"><el-icon><TrendCharts /></el-icon></div>
            <div class="card-text">
              <h4>LLM 评估</h4>
              <p>智能生成优化报告</p>
            </div>
          </el-card>
          <el-card class="float-card card-3" shadow="hover">
            <div class="card-icon"><el-icon><Refresh /></el-icon></div>
            <div class="card-text">
              <h4>增量迭代</h4>
              <p>防止灾难性遗忘</p>
            </div>
          </el-card>
          <img src="/vite.svg" alt="AI Core" class="main-logo" />
        </div>
      </div>
    </div>

    <!-- Technical Highlights -->
    <div class="highlights-section">
      <div class="highlight-item">
        <div class="icon-wrapper"><el-icon><Lightning /></el-icon></div>
        <h3>高效训练</h3>
        <p>支持冻结策略与多卡并行，大幅缩短训练周期</p>
      </div>
      <div class="highlight-item">
        <div class="icon-wrapper"><el-icon><Connection /></el-icon></div>
        <h3>模型压缩</h3>
        <p>通过知识蒸馏技术，在保持精度的同时显著降低模型体积</p>
      </div>
      <div class="highlight-item">
        <div class="icon-wrapper"><el-icon><ChatLineRound /></el-icon></div>
        <h3>智能诊断</h3>
        <p>集成大语言模型，自动分析 mAP/Loss 曲线并给出建议</p>
      </div>
      <div class="highlight-item">
        <div class="icon-wrapper"><el-icon><Files /></el-icon></div>
        <h3>数据闭环</h3>
        <p>支持从标注到训练再到评估的完整数据流转</p>
      </div>
    </div>

    <!-- Core Features -->
    <div ref="featuresSection" class="features-section">
      <h2 class="section-title">核心功能模块</h2>
      <div class="features-grid">
        <el-card class="feature-card" shadow="hover" @click="navigateTo('/model-development')">
          <template #header>
            <div class="feature-header">
              <el-icon :size="32" color="#409eff"><Monitor /></el-icon>
              <h3>模型开发</h3>
            </div>
          </template>
          <ul class="feature-list">
            <li>🚀 <strong>多模式训练</strong>：支持常规、增量、冻结及蒸馏训练</li>
            <li>📊 <strong>实时监控</strong>：可视化 Loss 曲线与训练日志</li>
            <li>💾 <strong>版本管理</strong>：自动保存模型权重与配置参数</li>
          </ul>
          <div class="card-footer">
            <span>前往开发</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </el-card>

        <el-card class="feature-card" shadow="hover" @click="navigateTo('/image-annotation')">
          <template #header>
            <div class="feature-header">
              <el-icon :size="32" color="#67c23a"><PictureFilled /></el-icon>
              <h3>图像标注</h3>
            </div>
          </template>
          <ul class="feature-list">
            <li>🤖 <strong>AI 辅助</strong>：集成 YOLO/SAM 模型自动预标注</li>
            <li>✍️ <strong>多工具支持</strong>：矩形框、多边形、关键点标注</li>
            <li>🔄 <strong>格式兼容</strong>：支持 JSON/TXT/XML 导入导出</li>
          </ul>
          <div class="card-footer">
            <span>开始标注</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </el-card>

        <el-card class="feature-card" shadow="hover" @click="navigateTo('/evaluation-optimization')">
          <template #header>
            <div class="feature-header">
              <el-icon :size="32" color="#e6a23c"><DataAnalysis /></el-icon>
              <h3>评估优化</h3>
            </div>
          </template>
          <ul class="feature-list">
            <li>📈 <strong>深度指标</strong>：mAP@0.5:0.95、Precision、Recall</li>
            <li>🧠 <strong>LLM 报告</strong>：AI 生成的自然语言优化建议</li>
            <li>📉 <strong>PR 曲线</strong>：高分辨率可视化图表导出</li>
          </ul>
          <div class="card-footer">
            <span>查看报告</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Workflow Section -->
    <div class="workflow-section">
      <h2 class="section-title">标准化迭代流程</h2>
      <div class="workflow-container">
        <div class="workflow-card" v-for="(step, index) in workflowSteps" :key="index">
          <div class="card-header">
            <span class="step-number">0{{ index + 1 }}</span>
            <div class="step-icon">
              <el-icon><component :is="step.icon" /></el-icon>
            </div>
          </div>
          <div class="card-body">
            <h4>{{ step.title }}</h4>
            <p>{{ step.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { 
  Monitor, 
  PictureFilled, 
  DataAnalysis, 
  Connection, 
  Cpu, 
  ArrowRight,
  Edit,
  TrendCharts,
  Refresh,
  Lightning,
  ChatLineRound,
  Files,
  UploadFilled,
  Right,
  DataLine,
  VideoPlay
} from '@element-plus/icons-vue';

const router = useRouter();
const featuresSection = ref(null);

const workflowSteps = [
  { 
    icon: 'UploadFilled', 
    title: '数据准备', 
    description: '上传原始图片，利用 AI 辅助快速完成数据标注' 
  },
  { 
    icon: 'Cpu', 
    title: '模型训练', 
    description: '选择增量或蒸馏模式，配置超参数启动训练' 
  },
  { 
    icon: 'DataLine', 
    title: '评估分析', 
    description: '生成评估报告，根据 LLM 建议调整策略' 
  },
  { 
    icon: 'VideoPlay', 
    title: '迭代优化', 
    description: '将优化后的模型投入下一轮训练循环' 
  }
];

const navigateTo = (route) => {
  router.push(route);
};

const scrollToFeatures = () => {
  featuresSection.value.scrollIntoView({ behavior: 'smooth' });
};
</script>

<style scoped>
.home-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px 40px;
}

/* Hero Section */
.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 80px 0;
  gap: 60px;
}

.hero-content {
  flex: 1;
}

.title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 24px;
  background: linear-gradient(120deg, #409eff, #36cfc9);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  font-size: 1.5rem;
  color: #303133;
  margin-bottom: 16px;
  font-weight: 500;
}

.highlight {
  color: #409eff;
  font-weight: bold;
}

.description {
  font-size: 1.1rem;
  color: #606266;
  margin-bottom: 40px;
  line-height: 1.6;
  max-width: 600px;
}

.action-buttons {
  display: flex;
  gap: 20px;
}

.cta-btn {
  padding: 12px 30px;
  font-size: 1.1rem;
  font-weight: 600;
}

/* Hero Image & Floating Cards */
.hero-image {
  flex: 1;
  display: flex;
  justify-content: center;
  position: relative;
  height: 400px;
}

.floating-cards {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.main-logo {
  width: 200px;
  height: 200px;
  z-index: 1;
  filter: drop-shadow(0 0 20px rgba(64, 158, 255, 0.3));
}

.float-card {
  position: absolute;
  width: 180px;
  padding: 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  gap: 12px;
  animation: float 4s ease-in-out infinite;
  cursor: default;
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #ecf5ff;
  color: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.card-text h4 {
  margin: 0;
  font-size: 14px;
  color: #303133;
}

.card-text p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}

.card-1 { top: 10%; left: 0%; animation-delay: 0s; }
.card-2 { top: 40%; right: -5%; animation-delay: 1.5s; }
.card-3 { bottom: 10%; left: 10%; animation-delay: 3s; }

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-15px); }
  100% { transform: translateY(0px); }
}

/* Highlights Section */
.highlights-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 30px;
  margin-bottom: 80px;
  padding: 40px;
  background: #fcfcfc;
  border-radius: 16px;
}

.highlight-item {
  text-align: center;
}

.icon-wrapper {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #409eff;
  margin: 0 auto 20px;
}

.highlight-item h3 {
  margin: 0 0 10px;
  font-size: 18px;
  color: #303133;
}

.highlight-item p {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

/* Features Section */
.section-title {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 50px;
  color: #303133;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 30px;
  margin-bottom: 80px;
}

.feature-card {
  border-radius: 12px;
  border: none;
  transition: all 0.3s;
  cursor: pointer;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}

.feature-header {
  display: flex;
  align-items: center;
  gap: 15px;
}

.feature-header h3 {
  margin: 0;
  font-size: 20px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-list li {
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.card-footer {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  color: #409eff;
  font-weight: 500;
  gap: 5px;
}

/* Workflow Section */
.workflow-section {
  padding: 80px 0;
  background-color: #f8f9fa;
  border-radius: 16px;
  margin-bottom: 40px;
}

.workflow-container {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 30px;
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}

/* 连接线背景层 */
.workflow-container::before {
  content: '';
  position: absolute;
  top: 40px;
  left: 10%;
  right: 10%;
  height: 2px;
  background: linear-gradient(90deg, #e4e7ed 0%, #409eff 50%, #e4e7ed 100%);
  z-index: 0;
}

.workflow-card {
  background: #fff;
  border-radius: 16px;
  padding: 30px 20px;
  text-align: center;
  position: relative;
  z-index: 1;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  border: 1px solid #ebeef5;
}

.workflow-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 12px 30px rgba(64, 158, 255, 0.15);
  border-color: #c6e2ff;
}

.card-header {
  position: relative;
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.step-number {
  position: absolute;
  top: -15px;
  right: 20px;
  font-size: 40px;
  font-weight: 900;
  color: #f0f2f5;
  z-index: -1;
  font-family: Arial, sans-serif;
  transition: color 0.3s;
}

.workflow-card:hover .step-number {
  color: #ecf5ff;
}

.step-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: linear-gradient(135deg, #ffffff, #f0f9eb);
  border: 1px solid #e1f3d8;
  color: #67c23a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  box-shadow: 0 8px 16px rgba(103, 194, 58, 0.1);
  transition: all 0.3s;
}

/* 为每个步骤设置不同的主题色 */
.workflow-card:nth-child(1) .step-icon {
  background: linear-gradient(135deg, #ffffff, #ecf5ff);
  border-color: #d9ecff;
  color: #409eff;
  box-shadow: 0 8px 16px rgba(64, 158, 255, 0.1);
}

.workflow-card:nth-child(2) .step-icon {
  background: linear-gradient(135deg, #ffffff, #fdf6ec);
  border-color: #faecd8;
  color: #e6a23c;
  box-shadow: 0 8px 16px rgba(230, 162, 60, 0.1);
}

.workflow-card:nth-child(3) .step-icon {
  background: linear-gradient(135deg, #ffffff, #fef0f0);
  border-color: #fde2e2;
  color: #f56c6c;
  box-shadow: 0 8px 16px rgba(245, 108, 108, 0.1);
}

.workflow-card:nth-child(4) .step-icon {
  background: linear-gradient(135deg, #ffffff, #f4f4f5);
  border-color: #e9e9eb;
  color: #909399;
  box-shadow: 0 8px 16px rgba(144, 147, 153, 0.1);
}

.workflow-card:hover .step-icon {
  transform: scale(1.1) rotate(5deg);
}

.card-body h4 {
  margin: 15px 0 10px;
  font-size: 18px;
  color: #303133;
  font-weight: 600;
}

.card-body p {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .workflow-container {
    grid-template-columns: 1fr;
    gap: 40px;
  }
  
  .workflow-container::before {
    display: none; /* 移动端隐藏连接线 */
  }
}
</style>