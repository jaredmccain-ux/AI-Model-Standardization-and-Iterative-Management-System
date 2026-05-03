# AI图像识别标准化迭代系统 - 前端

一个基于 Vue 3 + Vite + Element Plus 构建的AI图像识别标准化迭代系统前端应用，提供完整的AI模型开发、图像标注和评估优化工作流。

## 快速启动

**前提条件**: 请确保已安装 Node.js（推荐 v18+）和 npm。

```bash
# 1. 进入前端目录
cd ai_image_recognition_frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

启动后访问（以控制台输出为准，一般是）:
- http://localhost:5173/

---

## 核心页面与能力

### 核心功能模块
- **模型开发**:
  - 支持常规训练、增量训练、冻结策略训练和知识蒸馏
  - 与项目 project_id 绑定：训练产物统一归档到项目目录
  - 实时监控训练进度、损失值和性能指标
- **图像标注**:
  - 支持批量上传 / 自动标注 / 手动编辑
  - 支持缩略图快速回显项目历史图片（点击加载原图）
  - 支持“一键导入到项目数据集”（自动划分或手动选择 train/val）
- **评估优化**:
  - 自动读取训练产物 `evaluation_data.json` 并一键评估
  - `ground_truths=0` 会阻止评估并提示原因（避免“全 0 假成功”）
  - 支持查看项目历史评估记录与报告

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

## 使用指南（推荐顺序）

1. **首页创建/选择项目**：先选中项目再进入标注/训练/评估
2. **图像标注**：
   - 上传图片并标注（手动或自动）
   - 点击“导入到项目”，把图片+标注落盘为项目的 YOLO 数据集（train/val）
3. **模型开发**：
   - 选择训练类型与参数，启动训练
   - 可取消训练，状态会及时更新
4. **评估优化**：
   - 从项目最新训练产物加载 `evaluation_data.json`
   - 一键评估并查看历史评估记录

## 🛠️ 技术栈

- **Core**: Vue 3, Vite
- **UI**: Element Plus
- **Network**: Axios

## ⚙️ 配置说明

后端地址在 [api.js](file:///Users/baiyu/Desktop/ai/ai_image_recognition_frontend/src/config/api.js) 中配置：

- 开发环境默认请求：`http://localhost:8000`
- 生产环境默认同域：`window.location.origin`（通常由 Nginx 反向代理 `/api`）
- 如需强制切换环境，可修改 `FORCE_ENV`

## 构建与部署

```bash
npm run build
```

构建产物默认在 `dist/`。项目提供了 `Dockerfile` 与 `nginx.conf` 用于容器化部署。
