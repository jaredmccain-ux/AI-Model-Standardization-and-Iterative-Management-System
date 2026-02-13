# VisioFirm 标注工具后端集成指南

本文档详细说明如何在后端系统中集成 VisioFirm 标注工具，以支持前端的 AI 辅助标注功能。

## 一、API 接口需求与实现状态

### 已实现的 API 接口

#### 1. AI 自动标注接口

**请求地址**：`/api/visiofirm/auto_annotate`

**请求方法**：POST

**请求格式**：multipart/form-data

**请求参数**：
- `image`: 待标注的图像文件
- `tool`: 标注类型，可选值：`bbox`（边界框）、`polygon`（多边形）、`keypoint`（关键点）、`obb`（方向框）
- `classes`: JSON 字符串格式的类别列表

**响应格式**：JSON

**成功响应示例**：
```json
{
  "success": true,
  "annotations": [
    {
      "type": "bbox",
      "label": "person",
      "x": 10.5,
      "y": 20.3,
      "width": 15.2,
      "height": 30.8,
      "score": 0.95,
      "id": "annotation_0"
    },
    {
      "type": "bbox", 
      "label": "car",
      "x": 45.1,
      "y": 32.7,
      "width": 22.3,
      "height": 18.5,
      "score": 0.92,
      "id": "annotation_1"
    }
    // 更多标注结果...
  ]
}
```

**失败响应示例**：
```json
{
  "success": false,
  "detail": "标注处理失败的具体原因"
}
```

#### 2. 保存标注结果接口

**请求地址**：`/api/visiofirm/save_annotations`

**请求方法**：POST

**请求格式**：multipart/form-data（注意：实际实现使用了multipart/form-data而非application/json）

**请求参数**：
- `image_id`: 图片唯一标识符（整数）
- `annotations`: JSON 字符串格式的标注数据
- `format`: 标注格式（默认: "json"）

**响应格式**：JSON

#### 3. 获取标注历史接口

**请求地址**：`/api/visiofirm/annotations/{image_id}`

**请求方法**：GET

**响应格式**：JSON

#### 4. 获取标注工具列表接口

**请求地址**：`/api/visiofirm/tools`

**请求方法**：GET

**响应格式**：JSON

**响应示例**：
```json
[
  {"value": "bbox", "label": "边界框"},
  {"value": "polygon", "label": "多边形"},
  {"value": "keypoint", "label": "关键点"},
  {"value": "obb", "label": "方向框"}
]
```

## 二、后端实现指南

### 1. 环境准备

1. **安装 VisioFirm 库**
   
   后端已经在 requirements.txt 中添加了 VisioFirm 库依赖：
   
   ```bash
   # 安装所有依赖
   pip install -r requirements.txt
   ```

2. **配置 SAM2 模型**
   
   目前的实现使用了项目中已有的 YOLOv8 模型进行标注。未来可以扩展支持 SAM2 模型，需要下载相应模型文件并配置模型路径。

### 2. 实际实现的代码结构

已在项目中实现了 VisioFirm 相关的 API 接口，具体文件结构如下：

```
ai-image-recognition-backend/
├── main.py            # 主应用入口，已集成 VisioFirm API 路由
├── visiofirm/
│   ├── __init__.py    # 包初始化文件
│   └── api.py         # VisioFirm API 接口实现
├── ai_models.py       # AI 模型服务实现
└── requirements.txt   # 项目依赖（已添加 visiofirm>=0.1.0）
```

主要实现逻辑：
1. 在 `visiofirm/api.py` 中实现了所有 VisioFirm 相关的 API 接口
2. 通过 `convert_to_visiofirm_format()` 函数将现有模型的输出格式转换为前端期望的格式
3. 在 `main.py` 中注册了 VisioFirm API 路由

### 3. 实现的关键功能

1. **自动标注转换**：利用现有的 AI 模型（YOLOv8）进行目标检测，并将结果转换为 VisioFirm 前端需要的格式
2. **多种标注类型支持**：支持边界框、多边形、关键点和方向框四种标注类型
3. **数据库集成**：将标注结果保存到数据库，支持标注历史查询
4. **灵活的类别配置**：支持前端传递自定义类别列表

### 4. Docker 部署配置

项目可以使用现有 Docker 配置进行部署，已在 requirements.txt 中添加了必要的依赖。

## 三、性能优化建议

1. **模型缓存**
   
   将加载的 SAM2 模型缓存到内存中，避免每次请求都重新加载模型，大幅提高响应速度。

2. **异步处理**
   
   对于大图片或高并发场景，建议将标注任务放入队列，异步处理，并提供任务状态查询接口。

3. **GPU 加速**
   
   确保在生产环境中使用 GPU 运行 SAM2 模型，以获得最佳性能。

4. **请求限流**
   
   实现 API 请求限流机制，防止因大量并发请求导致服务过载。

## 四、安全性考虑

1. **输入验证**
   
   对所有输入参数进行严格验证，特别是文件类型和大小限制。

2. **访问控制**
   
   为 API 接口添加适当的身份验证和授权机制，确保只有授权用户可以使用标注服务。

3. **异常处理**
   
   完善的异常捕获和日志记录机制，便于问题排查和系统监控。

## 五、前端集成说明

前端已完成 VisioFirm 标注工具的集成，具体实现位于 `src/components/VisioFirmAnnotator.vue`。

前端通过 `API_BASE_URL` 配置获取后端 API 地址，在开发环境中默认指向 `http://localhost:8000`。

## 六、测试与验证

1. **本地测试**
   
   启动后端服务后，可以使用 curl 或 Postman 进行接口测试：
   
   ```bash
   curl -X POST "http://localhost:8000/api/visiofirm/auto_annotate" \
        -F "image=@test_image.jpg" \
        -F "tool=bbox" \
        -F "classes=[\"person\",\"car\"]"
   ```

2. **集成测试**
   
   启动前后端服务后，通过前端界面上传图片并尝试 AI 自动标注功能，验证端到端流程是否正常工作。

## 七、常见问题排查

1. **API 连接失败**
   - 检查后端服务是否正常运行
   - 验证网络连接和防火墙设置
   - 确认 `API_BASE_URL` 配置是否正确

2. **标注结果为空或不准确**
   - 检查图像质量和清晰度
   - 确认是否提供了正确的类别列表
   - 验证 VisioFirm 模型是否正确加载

3. **性能问题**
   - 检查是否启用了 GPU 加速
   - 考虑优化图像尺寸和模型参数
   - 对于大批量任务，考虑使用异步处理机制

通过以上指南，您应该能够成功在后端系统中集成 VisioFirm 标注工具，为前端提供 AI 辅助标注功能。如有其他问题或需求，请参考 VisioFirm 官方文档或联系技术支持。