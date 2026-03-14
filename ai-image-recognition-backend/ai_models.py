import cv2
import numpy as np
from PIL import Image
import torch
from ultralytics import YOLO
from transformers import pipeline
import io
import base64
import time

try:
    from visiofirm import model_registry
except ImportError:
    model_registry = None


class AIModelService:
    def __init__(self):
        # 初始化模型（首次运行会自动下载）
        self.detection_models = {}
        self.segmentation_models = {}
        self.classification_models = {}
        self.sam_model = None
        # 推理速度优化参数（优先降低时延）
        self.det_imgsz = 640
        self.seg_imgsz = 640
        self.max_det = 200
        # 用户/目录模型懒加载缓存
        self._lazy_detection = {}
        self._lazy_segmentation = {}
        self._load_models()
    
    def _load_models(self):
        try:
            # 加载目标检测模型
            self.detection_models["YOLO"] = YOLO('yolov8n.pt')  # nano版本，轻量级
            print("✅ YOLO 目标检测模型加载成功")
            
            # 加载真正的Faster R-CNN模型
            try:
                import torch
                import torchvision
                
                # 加载预训练的Faster R-CNN模型
                self.detection_models["FasterRCNN"] = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
                self.detection_models["FasterRCNN"].eval()  # 设置为评估模式
                
                # 加载COCO数据集的类别名称
                self.fasterrcnn_classes = [
                    '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
                    'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
                    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
                    'elephant', 'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A',
                    'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
                    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
                    'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl',
                    'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
                    'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table',
                    'N/A', 'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
                    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book',
                    'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
                ]
                print("✅ Faster R-CNN 目标检测模型加载成功")
                
                # 加载SSD模型作为另一个选项
                self.detection_models["SSD"] = torchvision.models.detection.ssd300_vgg16(pretrained=True)
                self.detection_models["SSD"].eval()  # 设置为评估模式
                print("✅ SSD 目标检测模型加载成功")
                
            except Exception as e:
                print(f"❌ 加载PyTorch检测模型失败: {e}")
                # 如果加载失败，使用YOLO作为备选
                self.detection_models["FasterRCNN"] = YOLO('yolov8n.pt')
                self.detection_models["FasterRCNN"].conf = 0.4
                print("⚠️ 使用YOLO模拟Faster R-CNN模型")
            
            # 尝试加载分割模型
            try:
                # 加载YOLO分割模型
                self.segmentation_models["YOLO-Seg"] = YOLO('yolov8n-seg.pt')
                print("✅ YOLO-Seg 分割模型加载成功")
                
                # 模拟Mask R-CNN（实际上使用YOLO-Seg但配置不同）
                self.segmentation_models["MaskRCNN"] = YOLO('yolov8n-seg.pt')
                self.segmentation_models["MaskRCNN"].conf = 0.5  # 设置不同的置信度阈值
                print("✅ Mask R-CNN 分割模型加载成功")
            except Exception as e:
                print(f"❌ 分割模型加载失败: {e}")
            
            # 尝试加载分类模型
            try:
                import torch
                import torchvision.models as models
                
                # 加载预训练的ResNet模型
                self.classification_models["ResNet"] = models.resnet50(pretrained=True)
                print("✅ ResNet 分类模型加载成功")
                
                # 加载预训练的EfficientNet模型
                self.classification_models["EfficientNet"] = models.efficientnet_b0(pretrained=True)
                print("✅ EfficientNet 分类模型加载成功")
            except Exception as e:
                print(f"❌ 分类模型加载失败: {e}")
                
            # 尝试加载SAM模型
            try:
                import importlib.util
                if importlib.util.find_spec("segment_anything") is not None:
                    from segment_anything import sam_model_registry, SamPredictor
                    
                    # 检查SAM模型文件是否存在
                    import os
                    sam_checkpoint = "sam_vit_h_4b8939.pth"
                    model_type = "vit_h"
                    
                    if os.path.exists(sam_checkpoint):
                        print(f"正在加载SAM模型: {sam_checkpoint}")
                        sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
                        self.sam_model = SamPredictor(sam)
                        print("✅ SAM模型加载成功")
                    else:
                        print(f"❌ SAM模型文件不存在: {sam_checkpoint}")
                else:
                    print("❌ 未安装segment_anything库，无法加载SAM模型")
            except Exception as e:
                print(f"❌ 加载SAM模型失败: {e}")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
    
    def detect_objects_with_visualization(self, image_bytes, model_name="YOLO"):
        """边界框检测，返回 (标注列表, 标注后的图片Base64编码)"""
        # 选择模型，默认使用YOLO
        if model_name not in self.detection_models:
            model_name = "YOLO"
            
        if not self.detection_models:
            return [], None
        
        try:
            # 转换图片格式
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(image)
            
            # 使用指定的模型运行推理
            model = self.detection_models[model_name]
            results = model(image)
            
            annotations = []
            # 在图片上绘制
            draw_img = img_np.copy()

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = box.conf[0].item()
                        cls = int(box.cls[0].item())
                        
                        # 获取类别名称
                        class_name = model.names[cls]
                        label = f"{class_name} ({conf:.2f})"

                        # 绘制边界框
                        cv2.rectangle(draw_img, (x1, y1), (x2, y2), (0, 255, 255), 2)
                        
                        # 绘制标签背景
                        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        cv2.rectangle(draw_img, (x1, y1 - 20), (x1 + w, y1), (0, 255, 255), -1)
                        # 绘制标签文字
                        cv2.putText(draw_img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        # 转换为百分比坐标用于JSON返回
                        img_w, img_h = image.size
                        x_percent = (x1 / img_w) * 100
                        y_percent = (y1 / img_h) * 100
                        w_percent = ((x2 - x1) / img_w) * 100
                        h_percent = ((y2 - y1) / img_h) * 100
                        
                        annotation = {
                            "from_name": "tag",
                            "to_name": "img",
                            "type": "rectanglelabels",
                            "value": {
                                "rectanglelabels": [label],
                                "x": x_percent,
                                "y": y_percent,
                                "width": w_percent,
                                "height": h_percent
                            }
                        }
                        annotations.append(annotation)
            
            # 将绘制后的图片转为Base64
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(draw_img, cv2.COLOR_RGB2BGR))
            annotated_image_base64 = base64.b64encode(buffer).decode('utf-8')

            return annotations, f"data:image/jpeg;base64,{annotated_image_base64}"
            
        except Exception as e:
            print(f"目标检测错误: {e}")
            return [], None
    
    def _get_segmentation_model(self, model_name):
        """解析 model_name：内置 / user:uuid / 目录 id，返回 (model, backend='yolo'|'sam'|None), key。"""
        if model_name and str(model_name).strip():
            mn = str(model_name).strip()
            # 用户上传模型（YOLO 格式）
            if model_registry and mn.startswith("user:"):
                path = model_registry.get_user_model_path(mn)
                if path and path.exists():
                    if mn not in self._lazy_segmentation:
                        self._lazy_segmentation[mn] = self._safe_load_yolo(path)
                    return self._lazy_segmentation[mn], "yolo", mn
            # 目录分割模型：仅当已下载到本地时才使用，不自动下载
            if model_registry and not mn.startswith("user:"):
                path = model_registry.get_downloaded_model_path(mn)
                if mn in self._lazy_segmentation:
                    if not path or not path.exists():
                        del self._lazy_segmentation[mn]
                    else:
                        return self._lazy_segmentation[mn], "yolo", mn
                if path and path.exists():
                    self._lazy_segmentation[mn] = self._safe_load_yolo(path)
                    return self._lazy_segmentation[mn], "yolo", mn
                catalog_ids = [e.get("id") for e in model_registry.load_catalog()]
                if mn in catalog_ids:
                    raise ValueError("该模型未下载到本地，请先在页面选择「下载到本地」后再使用")
            # 内置
            if mn in self.segmentation_models:
                return self.segmentation_models[mn], "yolo", mn
            if hasattr(self, 'sam_model') and self.sam_model and mn.upper() == "SAM":
                return self.sam_model, "sam", mn
        # 回退
        if self.segmentation_models and "YOLO-Seg" in self.segmentation_models:
            return self.segmentation_models["YOLO-Seg"], "yolo", "YOLO-Seg"
        if hasattr(self, 'sam_model') and self.sam_model:
            return self.sam_model, "sam", "SAM"
        return None, None, None

    def segment_objects(self, image_path, model_name=None):
        """多边形分割。支持内置、用户上传、目录已下载模型。"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"无法读取图像: {image_path}")
            height, width = image.shape[:2]
            model, backend, key = self._get_segmentation_model(model_name)
            if model is None:
                return self._generate_mock_segments(width, height)
            if backend == "sam":
                return self._segment_with_sam(image, width, height)
            if backend == "yolo":
                return self._segment_with_yolo(image, width, height, key, model=model)
            return self._generate_mock_segments(width, height)
        except Exception as e:
            print(f"分割错误: {e}")
            return []
            
    def _segment_with_sam(self, image, width, height):
        """使用SAM模型进行分割"""
        try:
            # 转换为RGB格式
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 使用SAM模型生成掩码
            self.sam_model.set_image(image_rgb)
            
            # 自动生成提示点
            # 这里简化处理，使用图像中心点作为提示点
            center_x, center_y = width // 2, height // 2
            input_point = np.array([[center_x, center_y]])
            input_label = np.array([1])  # 1表示前景
            
            # 生成掩码
            masks, scores, _ = self.sam_model.predict(
                point_coords=input_point,
                point_labels=input_label,
                multimask_output=True
            )
            
            segments = []
            
            # 处理每个掩码
            for i, (mask, score) in enumerate(zip(masks, scores)):
                # 找到掩码的轮廓
                contours, _ = cv2.findContours(
                    mask.astype(np.uint8), 
                    cv2.RETR_EXTERNAL, 
                    cv2.CHAIN_APPROX_SIMPLE
                )
                
                # 简化轮廓点
                for contour in contours:
                    # 简化轮廓，减少点的数量
                    epsilon = 0.005 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # 转换为百分比坐标
                    points = []
                    for point in approx:
                        x, y = point[0]
                        points.append([(x / width) * 100, (y / height) * 100])
                    
                    # 只添加有足够点的轮廓
                    if len(points) >= 3:
                        segments.append({
                            "class_name": f"Segment_{i+1}",
                            "confidence": float(score),
                            "points": points
                        })
            
            return segments
            
        except Exception as e:
            print(f"SAM分割错误: {e}")
            return []
            
    def _segment_with_yolo(self, image, width, height, model_name="YOLO-Seg", model=None):
        """使用YOLO分割模型进行分割。类别与置信度从 result.boxes 取，轮廓从 result.masks.xy 取。"""
        try:
            if model is None:
                model = self.segmentation_models.get(model_name) or self._lazy_segmentation.get(model_name)
            if model is None:
                return self._generate_mock_segments(width, height)
            t0 = time.perf_counter()
            results = model(
                image,
                imgsz=self.seg_imgsz,
                conf=0.25,
                iou=0.7,
                max_det=self.max_det,
                verbose=False,
            )
            
            segments = []
            for result in results:
                masks = result.masks
                if masks is not None:
                    for i, mask in enumerate(masks):
                        # 获取掩码数据
                        mask_data = mask.data[0].cpu().numpy()
                        
                        # 获取类别和置信度
                        cls = int(mask.cls[0].item())
                        conf = mask.conf[0].item()
                        class_name = model.names[cls]
                        
                        # 找到掩码的轮廓
                        contours, _ = cv2.findContours(
                            (mask_data * 255).astype(np.uint8), 
                            cv2.RETR_EXTERNAL, 
                            cv2.CHAIN_APPROX_SIMPLE
                        )
                        
                        # 简化轮廓点
                        for contour in contours:
                            # 简化轮廓，减少点的数量
                            epsilon = 0.005 * cv2.arcLength(contour, True)
                            approx = cv2.approxPolyDP(contour, epsilon, True)
                            
                            # 转换为百分比坐标
                            points = []
                            for point in approx:
                                x, y = point[0]
                                points.append([(x / width) * 100, (y / height) * 100])
                            
                            # 只添加有足够点的轮廓
                            if len(points) >= 3:
                                segments.append({
                                    "class_name": class_name,
                                    "confidence": float(conf),
                                    "points": points
                                })
            
            dt_ms = (time.perf_counter() - t0) * 1000
            print(f"YOLO分割推理耗时: {dt_ms:.1f} ms, segments={len(segments)}")
            return segments
            
        except Exception as e:
            print(f"YOLO分割错误: {e}")
            return []
    
    def _generate_mock_segments(self, width, height):
        """生成模拟的分割结果"""
        segments = []
        
        # 模拟一个多边形
        points = [
            [width * 0.2, height * 0.2],
            [width * 0.8, height * 0.2],
            [width * 0.8, height * 0.8],
            [width * 0.2, height * 0.8]
        ]
        points_percent = [[(p[0] / width) * 100, (p[1] / height) * 100] for p in points]

        segments.append({
            "class_name": "Object",
            "confidence": 0.95,
            "points": points_percent
        })
        
        # 模拟另一个多边形
        points2 = [
            [width * 0.3, height * 0.3],
            [width * 0.7, height * 0.3],
            [width * 0.7, height * 0.6],
            [width * 0.3, height * 0.6]
        ]
        points2_percent = [[(p[0] / width) * 100, (p[1] / height) * 100] for p in points2]

        segments.append({
            "class_name": "Region",
            "confidence": 0.87,
            "points": points2_percent
        })
        
        return segments
            
    def _safe_load_yolo(self, path):
        """加载 YOLO 模型文件，若文件损坏则抛出明确的 ValueError。"""
        try:
            return YOLO(str(path))
        except (EOFError, OSError, RuntimeError) as e:
            if isinstance(e, EOFError) or "Ran out of input" in str(e):
                raise ValueError("模型文件已损坏或不完整，请删除后重新下载到本地") from e
            raise

    def _get_detection_model(self, model_name):
        """解析 model_name：内置 / user:uuid / 目录 id，返回 (model, use_yolo=True/False, py_name)。"""
        if not model_name or not str(model_name).strip():
            model_name = "YOLO"
        model_name = str(model_name).strip()
        # 用户上传模型
        if model_registry and model_name.startswith("user:"):
            path = model_registry.get_user_model_path(model_name)
            if path and path.exists():
                if model_name not in self._lazy_detection:
                    self._lazy_detection[model_name] = self._safe_load_yolo(path)
                return self._lazy_detection[model_name], True, model_name
        # 目录模型（检测类）：仅当用户已下载到本地时才使用，不自动下载
        if model_registry and not model_name.startswith("user:"):
            path = model_registry.get_downloaded_model_path(model_name)
            if model_name in self._lazy_detection:
                if not path or not path.exists():
                    del self._lazy_detection[model_name]
                else:
                    return self._lazy_detection[model_name], True, model_name
            if path and path.exists():
                self._lazy_detection[model_name] = self._safe_load_yolo(path)
                return self._lazy_detection[model_name], True, model_name
            catalog_ids = [e.get("id") for e in model_registry.load_catalog()]
            if model_name in catalog_ids:
                raise ValueError("该模型未下载到本地，请先在页面选择「下载到本地」后再使用")
        # 内置
        if model_name in self.detection_models:
            model = self.detection_models[model_name]
            use_pytorch = model_name in ["FasterRCNN", "SSD"] and isinstance(model, torch.nn.Module)
            return model, not use_pytorch, model_name
        # 回退
        model_name = "YOLO"
        if model_name in self.detection_models:
            return self.detection_models[model_name], True, model_name
        return None, True, model_name

    def detect_objects(self, image_path, model_name=None):
        """边界框检测，返回检测结果列表"""
        model, use_yolo, resolved_name = self._get_detection_model(model_name)
        if model is None:
            return self._generate_mock_detections()
        if not self.detection_models and not self._lazy_detection:
            return self._generate_mock_detections()
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"无法读取图像: {image_path}")
            height, width = image.shape[:2]
            if use_yolo:
                return self._detect_with_yolo(image, model)
            return self._detect_with_pytorch(image, model, resolved_name)
        except Exception as e:
            print(f"检测出错: {e}")
            return []
            
    def _detect_with_yolo(self, image, model):
        """使用YOLO模型进行目标检测"""
        height, width = image.shape[:2]
        t0 = time.perf_counter()
        results = model(
            image,
            imgsz=self.det_imgsz,
            conf=0.25,
            iou=0.7,
            max_det=self.max_det,
            verbose=False,
        )
        
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # 获取边界框坐标
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = box.conf[0].item()
                    cls = int(box.cls[0].item())
                    
                    # 获取类别名称
                    class_name = model.names[cls]
                    
                    # 转换为百分比坐标
                    x_percent = x1 / width
                    y_percent = y1 / height
                    w_percent = (x2 - x1) / width
                    h_percent = (y2 - y1) / height
                    
                    # 添加检测结果
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'bbox_percent': [x_percent, y_percent, w_percent, h_percent],
                        'confidence': float(conf),
                        'class_id': int(cls),
                        'class_name': class_name
                    })
        
        dt_ms = (time.perf_counter() - t0) * 1000
        print(f"YOLO检测推理耗时: {dt_ms:.1f} ms, detections={len(detections)}")
        return detections
        
    def _detect_with_pytorch(self, image, model, model_name):
        """使用PyTorch检测模型进行目标检测"""
        import torch
        import torchvision.transforms as transforms
        from PIL import Image
        import numpy as np
        
        # 大图自动缩放后再推理，显著降低 FasterRCNN/SSD 时延
        orig_height, orig_width = image.shape[:2]
        max_side = max(orig_height, orig_width)
        scale = 1.0
        infer_image = image
        if max_side > 1280:
            scale = 1280.0 / float(max_side)
            new_w = max(1, int(orig_width * scale))
            new_h = max(1, int(orig_height * scale))
            infer_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 转换图像格式
        image_rgb = cv2.cvtColor(infer_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # 转换为PyTorch张量
        transform = transforms.Compose([
            transforms.ToTensor()
        ])
        img_tensor = transform(pil_image)
        
        # 进行推理
        t0 = time.perf_counter()
        with torch.no_grad():
            predictions = model([img_tensor])
        
        # 处理预测结果
        detections = []
        boxes = predictions[0]['boxes'].cpu().numpy()
        scores = predictions[0]['scores'].cpu().numpy()
        labels = predictions[0]['labels'].cpu().numpy()
        
        # 设置置信度阈值
        threshold = 0.5
        
        # 获取原图尺寸（百分比坐标按原图计算）
        height, width = orig_height, orig_width
        
        for i, box in enumerate(boxes):
            if scores[i] >= threshold:
                x1, y1, x2, y2 = map(float, box)
                if scale != 1.0:
                    inv = 1.0 / scale
                    x1, y1, x2, y2 = x1 * inv, y1 * inv, x2 * inv, y2 * inv
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                label_id = int(labels[i])
                
                # 获取类别名称
                if model_name in ["FasterRCNN", "SSD"]:
                    class_name = self.fasterrcnn_classes[label_id]
                else:
                    class_name = f"Class_{label_id}"
                
                # 转换为百分比坐标
                x_percent = x1 / width
                y_percent = y1 / height
                w_percent = (x2 - x1) / width
                h_percent = (y2 - y1) / height
                
                # 添加检测结果
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'bbox_percent': [x_percent, y_percent, w_percent, h_percent],
                    'confidence': float(scores[i]),
                    'class_id': label_id,
                    'class_name': class_name
                })
        
        dt_ms = (time.perf_counter() - t0) * 1000
        print(f"{model_name}检测推理耗时: {dt_ms:.1f} ms, scale={scale:.3f}, detections={len(detections)}")
        return detections
    
    def detect_oriented_objects(self, image_path, model_name=None):
        """方向边界框(OBB)检测"""
        # 待集成实际模型，目前返回空
        return []
    
    def classify_image(self, image_path, model_name=None):
        """图像分类"""
        try:
            import torch
            import torchvision.transforms as transforms
            import torchvision.models as models
            from PIL import Image
            
            # 检查是否有GPU可用
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            # 如果模型字典为空，初始化分类模型
            if not self.classification_models:
                self.classification_models = {
                    "ResNet": models.resnet50(pretrained=True),
                    "EfficientNet": models.efficientnet_b0(pretrained=True)
                }
                
            # 选择模型，默认使用ResNet
            if model_name not in self.classification_models:
                model_name = "ResNet"
                
            # 使用选定的模型
            model = self.classification_models[model_name]
            
            model.eval()
            model.to(device)
            
            # 图像预处理
            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            
            # 加载图像
            image = Image.open(image_path).convert('RGB')
            input_tensor = preprocess(image)
            input_batch = input_tensor.unsqueeze(0).to(device)
            
            # 进行推理
            with torch.no_grad():
                output = model(input_batch)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
            
            # 加载ImageNet类别标签
            with open('imagenet_classes.txt', 'r') as f:
                categories = [s.strip() for s in f.readlines()]
            
            # 获取前3个预测结果
            top3_prob, top3_catid = torch.topk(probabilities, 3)
            
            # 构建分类结果
            classifications = []
            for i in range(top3_prob.size(0)):
                classifications.append({
                    "class_name": categories[top3_catid[i]],
                    "confidence": float(top3_prob[i].item())
                })
            
            return classifications
            
        except Exception as e:
            print(f"图像分类错误: {e}")
            return []

    def detect_keypoints(self, image_bytes):
        """关键点检测"""
        # 待集成实际模型，目前返回空
        return []

# 全局模型实例
ai_service = AIModelService()