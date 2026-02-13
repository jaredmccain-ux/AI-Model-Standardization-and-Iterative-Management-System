# AI图像识别标准化迭代系统 - 前端

一个基于 Vue 3 + Vite + Element Plus 构建的AI图像识别标准化迭代系统前端应用，提供完整的AI模型开发、图像标注和评估优化工作流。

## 🚀 快速启动

**前提条件**: 请确保已安装 Node.js (推荐 v16.0.0+) 和 npm/yarn。

```bash
# 1. 进入前端目录
cd ai_image_recognition_frontend

# 2. 安装依赖
npm install
# 或 yarn install

# 3. 启动开发服务器
npm run dev
# 或 yarn dev
```

启动后访问: [http://localhost:3000](以控制台输出地址为准)

---

## 🚀 项目特性

### 核心功能模块
- **🔧 模型开发**: 
  - 支持常规训练、增量训练、冻结策略训练和知识蒸馏
  - 支持本地数据集路径直接选择，解决路径映射问题
  - 实时监控训练进度、损失值和性能指标
- **🖼️ 图像标注**: 
  - 集成 YOLOv8 自动标注
  - 支持边界框 (BBox)、多边形 (Polygon)、关键点 (Keypoint)
  - 实时 Canvas 绘制与编辑
- **📊 评估优化**: 
  - 模型性能评估报告
  - 针对性优化建议

## 📦 项目结构

```
src/
├── api/               # 后端接口封装
├── components/        # 公共组件
├── views/             # 页面视图
│   ├── ImageAnnotation.vue      # 图像标注
│   ├── ModelDevelopment.vue     # 模型开发 (含训练配置)
│   └── EvaluationOptimization.vue # 评估优化
├── config/            # 全局配置
└── ...
```

## 🎯 使用指南

### 模型开发工作流
1. **配置训练**: 在“模型开发”页面选择训练类型（常规/增量/冻结/蒸馏）。
2. **选择数据**: 点击输入框旁的“选择本地文件”按钮，直接选取本地的 YAML 数据集配置文件。
3. **参数设置**: 调整 Epochs、Batch Size、模型大小等参数。
4. **启动训练**: 点击开始，并在右侧面板实时查看训练日志和指标。

### 图像标注工作流
1. **上传图片**: 支持批量上传图片。
2. **AI 辅助**: 使用“AI自动标注”快速生成初步结果。
3. **人工修正**: 使用工具栏调整标注框或分割点。
4. **导出数据**: 将标注结果导出为标准格式。

## 🛠️ 技术栈

- **Core**: Vue 3, Vite
- **UI**: Element Plus
- **Network**: Axios
- **Visualization**: ECharts (用于训练图表)

## ⚙️ 配置说明

在 `src/config/api.js` 中配置后端地址：
```javascript
export const API_BASE_URL = 'http://localhost:8000'; // 根据实际后端地址修改
```
