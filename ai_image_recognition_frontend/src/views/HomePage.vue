<template>
  <div class="home-container">
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="title">AI图像识别标准化迭代系统</h1>
        <p class="subtitle">一站式AI模型开发、图像标注与评估优化平台</p>
        <div class="action-buttons">
          <el-button type="primary" size="large" @click="navigateTo('/model-development')">开始使用</el-button>
          <el-button size="large" @click="scrollToFeatures">了解更多</el-button>
        </div>
      </div>
      <div class="hero-image">
        <img src="/vite.svg" alt="AI图像识别" />
      </div>
    </div>

    <div ref="featuresSection" class="features-section">
      <h2 class="section-title">核心功能</h2>
      <div class="features-grid">
        <div class="feature-card" v-for="(feature, index) in features" :key="index">
          <el-icon :size="50" class="feature-icon">
            <component :is="feature.icon"></component>
          </el-icon>
          <h3 class="feature-title">{{ feature.title }}</h3>
          <p class="feature-description">{{ feature.description }}</p>
          <el-button type="primary" text @click="navigateTo(feature.route)">
            立即体验
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <div class="workflow-section">
      <h2 class="section-title">使用流程</h2>
      <el-steps :active="1" finish-status="success" simple>
        <el-step v-for="(step, index) in workflowSteps" :key="index" :title="step.title" :description="step.description" />
      </el-steps>
      
      <div class="workflow-details">
        <div class="workflow-item" v-for="(workflow, index) in workflows" :key="index">
          <div class="workflow-header">
            <h3 class="workflow-title">{{ workflow.title }}</h3>
            <el-tag>{{ workflow.tag }}</el-tag>
          </div>
          <div class="workflow-steps">
            <div class="step" v-for="(step, stepIndex) in workflow.steps" :key="stepIndex">
              <div class="step-number">{{ stepIndex + 1 }}</div>
              <div class="step-content">
                <h4 class="step-title">{{ step.title }}</h4>
                <p class="step-description">{{ step.description }}</p>
              </div>
            </div>
          </div>
          <el-button type="primary" @click="navigateTo(workflow.route)">前往{{ workflow.title }}</el-button>
        </div>
      </div>
    </div>

    <div class="cta-section">
      <h2 class="section-title">开始您的AI之旅</h2>
      <p class="cta-description">立即体验我们的AI图像识别标准化迭代系统，提升您的AI模型开发效率</p>
      <el-button type="primary" size="large" @click="navigateTo('/model-development')">开始使用</el-button>
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
  ArrowRight 
} from '@element-plus/icons-vue';

const router = useRouter();
const featuresSection = ref(null);

const features = [
  {
    icon: 'Monitor',
    title: '模型开发',
    description: '创建、训练和迭代管理AI模型，支持多种训练策略和参数配置',
    route: '/model-development'
  },
  {
    icon: 'PictureFilled',
    title: '图像标注',
    description: '支持边界框、多边形分割和关键点检测等多种标注工具，提供AI辅助标注功能',
    route: '/image-annotation'
  },
  {
    icon: 'DataAnalysis',
    title: '评估优化',
    description: '全面评估模型性能，提供可视化分析和优化建议，提升模型准确率',
    route: '/evaluation-optimization'
  }
];

const workflowSteps = [
  { title: '创建模型', description: '配置模型参数' },
  { title: '标注数据', description: '准备训练数据' },
  { title: '训练模型', description: '开始模型训练' },
  { title: '评估优化', description: '分析并优化' },
  { title: '部署应用', description: '投入实际使用' }
];

const workflows = [
  {
    title: '模型开发流程',
    tag: '核心功能',
    route: '/model-development',
    steps: [
      { title: '创建模型', description: '设置模型名称、类型和参数' },
      { title: '选择数据集', description: '上传或选择已有的标注数据集' },
      { title: '配置训练参数', description: '设置批次大小、学习率等参数' },
      { title: '启动训练', description: '开始模型训练过程' },
      { title: '监控训练', description: '实时查看训练进度和指标' }
    ]
  },
  {
    title: '图像标注流程',
    tag: '数据准备',
    route: '/image-annotation',
    steps: [
      { title: '上传图片', description: '点击上传图片按钮，支持批量上传' },
      { title: '选择工具', description: '从下拉菜单选择标注工具类型' },
      { title: 'AI标注', description: '点击AI自动标注进行智能标注' },
      { title: '手动调整', description: '在标注界面中手动调整标注结果' },
      { title: '保存导出', description: '保存标注结果并导出数据' }
    ]
  },
  {
    title: '评估优化流程',
    tag: '性能提升',
    route: '/evaluation-optimization',
    steps: [
      { title: '选择模型', description: '从已训练模型列表中选择' },
      { title: '上传测试集', description: '上传用于评估的图像数据' },
      { title: '运行评估', description: '获取模型性能指标' },
      { title: '查看结果', description: '分析准确率、召回率等指标' },
      { title: '应用优化', description: '根据建议优化模型参数' }
    ]
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.hero-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 40px 0 60px;
  min-height: 400px;
}

.hero-content {
  flex: 1;
  padding-right: 40px;
}

.hero-image {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.hero-image img {
  max-width: 100%;
  height: auto;
  animation: float 3s ease-in-out infinite;
  pointer-events: none;
  user-select: none;
  -webkit-user-drag: none;
}

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-20px); }
  100% { transform: translateY(0px); }
}

.title {
  font-size: 2.5rem;
  margin-bottom: 16px;
  background: linear-gradient(90deg, #409EFF, #67C23A);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;
}

.subtitle {
  font-size: 1.2rem;
  color: #606266;
  margin-bottom: 32px;
}

.action-buttons {
  display: flex;
  gap: 16px;
}

.section-title {
  text-align: center;
  margin-bottom: 40px;
  font-size: 2rem;
  color: #303133;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 4px;
  background: #409EFF;
  border-radius: 2px;
}

.features-section {
  margin: 80px 0;
  scroll-margin-top: 80px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.feature-card {
  background: #fff;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s, box-shadow 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  color: #409EFF;
  margin-bottom: 20px;
}

.feature-title {
  font-size: 1.4rem;
  margin-bottom: 16px;
  color: #303133;
}

.feature-description {
  color: #606266;
  margin-bottom: 20px;
  flex-grow: 1;
}

.workflow-section {
  margin: 80px 0;
}

.workflow-details {
  margin-top: 60px;
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.workflow-item {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 30px;
}

.workflow-header {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.workflow-title {
  font-size: 1.4rem;
  margin-right: 12px;
  color: #303133;
}

.workflow-steps {
  margin-bottom: 24px;
}

.step {
  display: flex;
  margin-bottom: 16px;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 1.1rem;
  margin-bottom: 4px;
  color: #303133;
}

.step-description {
  color: #606266;
}

.cta-section {
  margin: 80px 0;
  text-align: center;
  background: linear-gradient(135deg, #f0f5ff, #e6f7ff);
  padding: 60px;
  border-radius: 8px;
}

.cta-description {
  max-width: 600px;
  margin: 0 auto 32px;
  color: #606266;
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
  }
  
  .hero-content {
    padding-right: 0;
    margin-bottom: 40px;
  }
  
  .action-buttons {
    justify-content: center;
  }
}
</style>