# AI 模型标准化迭代管理系统

一个围绕“项目（Project）”组织数据与产物的视觉类 AI 迭代平台，覆盖从数据标注到训练、评估与优化建议的完整闭环。

## 目录

- 前端：`ai_image_recognition_frontend/`（Vue 3 + Vite + Element Plus）
- 后端：`ai-image-recognition-backend/`（FastAPI + Ultralytics YOLO）

## 运行方式（本地开发）

### 1) 启动后端（端口 8000）

```bash
cd ai-image-recognition-backend
pip3 install -r requirements.txt
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：
- http://localhost:8000/docs

### 2) 启动前端（Vite，端口以控制台输出为准）

```bash
cd ai_image_recognition_frontend
npm install
npm run dev
```

前端默认请求后端：`http://localhost:8000`（可在 `src/config/api.js` 调整）。

## 标准工作流（推荐顺序）

1. **首页创建/选择项目**
2. **图像标注**
   - 上传图片 → 自动标注/手动标注 → 保存标注
   - 点击“导入到项目”：把图片+标注落盘为项目数据集（YOLO 目录结构，train/val）
3. **模型开发**
   - 选择训练类型（常规/增量/冻结/蒸馏）与训练参数，启动训练
   - 训练产物归档到项目目录，生成评估所需 `evaluation_data.json`
4. **评估优化**
   - 从最新训练产物加载 `evaluation_data.json`，一键评估
   - 评估结果写入项目 `evaluation/eval_*`，支持历史查看与报告

## 项目化数据结构

项目默认落在后端的 `PROJECTS_ROOT`（不设置时为 `ai-image-recognition-backend/projects/`）：

```
projects/<project_id>/
├── meta.json
├── dataset.yaml
├── data/
│   ├── images/{train,val}/
│   └── labels/{train,val}/
├── training/<run>/...
└── evaluation/eval_<evaluation_id>/...
```

## 常见问题

### 1) 新项目“串出”其他项目的图片

前端图像标注页使用 keep-alive 缓存组件，项目切换时需要同步刷新项目上下文。项目已做兼容处理：当 project_id 变化会清空会话并重新拉取当前项目数据集。

### 2) 评估全为 0 / `ground_truths` 为 0

通常原因：
- 验证集划分到未标注图片，或 `labels/val` 下 txt 为空
- 历史产物 `evaluation_data.json` 的 `image_id` 不匹配真实文件名

处理方式：
- 回到“图像标注 → 导入到项目”，确保验证集图片确实有标注
- 对历史训练产物执行重建：`POST /api/projects/{project_id}/artifacts/evaluation-data/regenerate`

## 进一步说明

- 后端详细说明见：`ai-image-recognition-backend/README.md`
- 前端详细说明见：`ai_image_recognition_frontend/README.md`
