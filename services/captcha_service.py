"""Captcha AI service using ONNX model for digit recognition."""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional

from utils.logging import get_logger

logger = get_logger(__name__)

# Try to import dependencies
try:
    import onnxruntime as ort
    from PIL import Image
    import aiohttp
    import io

    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Captcha service dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


class CaptchaAI:
    """AI-powered captcha solver using ONNX model.

    Uses an ONNX object detection model to recognize digits in captcha images.
    """

    # Image size expected by the model
    IMG_SIZE = 160
    # Maximum number of digits in captcha
    MAX_LABEL_SIZE = 4

    def __init__(self, model_path: str | Path) -> None:
        """Initialize the CaptchaAI with an ONNX model.

        Args:
            model_path: Path to the ONNX model file.

        Raises:
            FileNotFoundError: If the model file doesn't exist.
            RuntimeError: If ONNX runtime fails to load the model.
        """
        if not DEPENDENCIES_AVAILABLE:
            raise RuntimeError(
                "Required dependencies not available. "
                "Install: pip install onnxruntime Pillow aiohttp"
            )

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            self._session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
            )
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info(f"Captcha AI model loaded: {model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ONNX model: {e}")

    async def predict(self, img_url: str) -> str:
        """Predict the captcha digits from an image URL.

        Args:
            img_url: URL of the captcha image.

        Returns:
            String of predicted digits (empty string on failure).
        """
        try:
            # Download and preprocess image
            img = await self._get_image(img_url)
            input_tensor = self._image_to_tensor(img)

            # Run inference
            output = self._run_inference(input_tensor)

            # Post-process with NMS
            _, labels, boxes = self._nms(output)

            # Order labels by x-position (left to right)
            indices = list(range(len(labels)))
            indices.sort(key=lambda i: boxes[i * 4])

            # Build result string
            result = ""
            for i in indices[: self.MAX_LABEL_SIZE]:
                result += str(labels[i])

            logger.debug(f"Captcha prediction: {result}")
            return result

        except Exception as e:
            logger.error(f"Captcha prediction failed: {e}")
            return ""

    async def _get_image(self, img_url: str) -> Image.Image:
        """Download and preprocess an image from URL.

        Args:
            img_url: URL of the image.

        Returns:
            Preprocessed PIL Image.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(img_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to download image: HTTP {response.status}")
                data = await response.read()

        # Open image
        img = Image.open(io.BytesIO(data)).convert("RGB")

        # Resize maintaining aspect ratio
        width, height = img.size
        if width > height:
            new_width = self.IMG_SIZE
            new_height = int(height * self.IMG_SIZE / width)
        else:
            new_height = self.IMG_SIZE
            new_width = int(width * self.IMG_SIZE / height)

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create black background and paste image
        bg = Image.new("RGB", (self.IMG_SIZE, self.IMG_SIZE), (0, 0, 0))
        bg.paste(img, (0, 0))

        return bg

    def _image_to_tensor(self, img: Image.Image) -> np.ndarray:
        """Convert PIL Image to ONNX input tensor.

        Args:
            img: PIL Image (RGB).

        Returns:
            Numpy array with shape [1, 3, H, W] in float32.
        """
        # Convert to numpy array [H, W, 3]
        img_array = np.array(img, dtype=np.float32)

        # Normalize to [0, 1]
        img_array /= 255.0

        # Transpose to [3, H, W]
        img_array = img_array.transpose(2, 0, 1)

        # Add batch dimension [1, 3, H, W]
        img_array = np.expand_dims(img_array, axis=0)

        return img_array

    def _run_inference(self, input_tensor: np.ndarray) -> np.ndarray:
        """Run ONNX inference.

        Args:
            input_tensor: Input tensor with shape [1, 3, H, W].

        Returns:
            Model output tensor.
        """
        outputs = self._session.run(
            [self._output_name],
            {self._input_name: input_tensor},
        )
        return outputs[0]

    def _nms(
        self,
        output: np.ndarray,
        iou_threshold: float = 0.5,
        conf_threshold: float = 0.25,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply Non-Maximum Suppression to filter detections.

        Args:
            output: Model output tensor.
            iou_threshold: IoU threshold for suppression.
            conf_threshold: Confidence threshold for filtering.

        Returns:
            Tuple of (confidences, labels, boxes) arrays.
        """
        # Output shape: [1, num_classes+4, num_boxes]
        # Transpose to [num_boxes, num_classes+4]
        dims = output.shape
        rows = dims[2]
        cls_num = dims[1] - 4

        # Transform data
        data = []
        for i in range(rows):
            arr = np.zeros(cls_num + 4, dtype=np.float32)
            for j in range(cls_num + 4):
                arr[j] = output[0, j, i]

            # Convert center format to corner format
            center_x, center_y = arr[0], arr[1]
            half_w, half_h = arr[2] / 2, arr[3] / 2
            arr[0] = center_x - half_w  # x1
            arr[1] = center_y - half_h  # y1
            arr[2] = center_x + half_w  # x2
            arr[3] = center_y + half_h  # y2
            data.append(arr)

        # Find max confidence and label for each box
        conf_arr = np.zeros(rows, dtype=np.float32)
        label_arr = np.zeros(rows, dtype=np.uint8)
        candidates = set()

        for i in range(rows):
            scores = data[i][4 : 4 + cls_num]
            conf = np.max(scores)
            label = np.argmax(scores)

            if conf > conf_threshold:
                candidates.add(i)

            conf_arr[i] = conf
            label_arr[i] = label

        # NMS loop
        selected = []
        while candidates:
            # Find box with max confidence
            max_conf = -1
            max_idx = 0
            for idx in candidates:
                if conf_arr[idx] > max_conf:
                    max_conf = conf_arr[idx]
                    max_idx = idx

            selected.append(max_idx)

            # Calculate IoU with all remaining boxes
            box_a = data[max_idx][:4]
            area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])

            new_candidates = set()
            for idx in candidates:
                if idx == max_idx:
                    continue

                box_b = data[idx][:4]
                area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

                # Calculate intersection
                x1 = max(box_a[0], box_b[0])
                y1 = max(box_a[1], box_b[1])
                x2 = min(box_a[2], box_b[2])
                y2 = min(box_a[3], box_b[3])

                intersection = max(0, x2 - x1) * max(0, y2 - y1)
                union = area_a + area_b - intersection
                iou = intersection / union if union > 0 else 0

                if iou < iou_threshold:
                    new_candidates.add(idx)

            candidates = new_candidates

        # Extract final results
        n = len(selected)
        confidences = np.zeros(n, dtype=np.float32)
        labels = np.zeros(n, dtype=np.uint8)
        boxes = np.zeros(n * 4, dtype=np.float32)

        for i, idx in enumerate(selected):
            confidences[i] = conf_arr[idx]
            labels[i] = label_arr[idx]
            boxes[i * 4 : i * 4 + 4] = data[idx][:4]

        return confidences, labels, boxes

    @classmethod
    async def create(cls, model_path: str | Path) -> "CaptchaAI":
        """Async factory method for creating CaptchaAI instance.

        Args:
            model_path: Path to the ONNX model file.

        Returns:
            Initialized CaptchaAI instance.
        """
        return cls(model_path)
