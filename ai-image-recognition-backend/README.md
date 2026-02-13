# AI 图像识别标准化迭代系统 - 后端服务

基于 FastAPI 和 YOLOv8 构建的高性能 AI 后端服务，支持目标检测、图像分割和分类任务的训练、推理与评估。

## 🚀 快速启动

**前提条件**: 请确保已安装 Python 3.9+ 和 CUDA (如需 GPU 训练)。

```bash
# 1. 进入后端目录
cd ai-image-recognition-backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 API 文档:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🚀 核心功能

- **多模式训练系统**:
  - **常规训练**: 标准 YOLOv8 训练流程
  - **增量训练**: 基于现有模型进行新类别或新数据的增量学习 (支持旧样本回放)
  - **知识蒸馏**: 支持教师-学生模型蒸馏，包含分类/回归/特征损失及一致性训练
  - **冻结策略**: 分阶段解冻训练，优化微调效果
- **智能辅助标注**: 提供自动化的 BBox、Polygon 和 Keypoint 标注接口
- **任务管理**: 异步训练任务调度，支持任务状态查询、日志实时获取和取消任务
- **本地文件集成**: 支持服务端直接访问本地文件系统 (适用于本地部署)

## 📡 主要 API 接口

### 模型训练 (Training)
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/training/regular` | 启动常规训练 |
| POST | `/api/training/incremental` | 启动增量训练 (支持新类别) |
| POST | `/api/training/distillation` | 启动知识蒸馏训练 |
| POST | `/api/training/freeze-strategy` | 启动冻结策略训练 |
| GET | `/api/training/tasks` | 获取所有训练任务列表 |
| GET | `/api/training/tasks/{id}/logs` | 获取实时训练日志 |
| GET | `/api/training/select-local-file` | 打开本地文件选择器 |

### 图像标注 (Annotation)
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/auto_annotate` | 上传图片并获取 AI 标注结果 |

## 📂 项目结构

```
ai-image-recognition-backend/
├── main.py                 # FastAPI 入口
├── training/               # 训练核心模块
│   ├── api.py              # 训练相关 API 路由
│   ├── training_service.py # 任务调度服务
│   ├── incremental_newtrain.py # 增量训练逻辑
│   ├── distillation_trainer.py # 知识蒸馏逻辑
│   └── enhanced_training.py    # 常规/冻结训练逻辑
├── ai_models.py            # YOLO 模型推理封装
├── database.py             # SQLite 数据库连接
└── uploads/                # 临时文件存储
```

## 🛠️ 技术栈

- **Web Framework**: FastAPI
- **Deep Learning**: PyTorch, Ultralytics YOLOv8
- **Database**: SQLite, SQLAlchemy
- **Task Queue**: Python `threading` & `asyncio` (用于异步训练任务)

## 🔧 配置说明

- **端口配置**: 默认运行在 `8000` 端口。
- **数据存储**: 默认使用 SQLite 数据库 `sql_app.db` 存储任务记录。
- **模型路径**: 预训练模型默认下载到项目根目录。
