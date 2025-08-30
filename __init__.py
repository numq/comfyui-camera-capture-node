import asyncio
import io
import logging
import threading
import time

import numpy as np
import torch
import torch.nn.functional as F
import websockets
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080


class WebSocketImageReceiver:
    def __init__(self, port=DEFAULT_PORT):
        self.address = DEFAULT_HOST
        self.port = port
        self.current_frame = None
        self.lock = threading.Lock()
        self.running = False
        self._loop = None
        self._server = None
        self._thread = None

    def _decode_jpeg_to_ndarray(self, jpeg_bytes):
        try:
            im = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
            return np.ascontiguousarray(np.asarray(im))
        except Exception as e:
            return None

    async def _ws_server(self):
        async def handler(websocket, path=None):
            try:
                async for message in websocket:
                    arr = self._decode_jpeg_to_ndarray(message)
                    if arr is not None:
                        with self.lock:
                            self.current_frame = arr
            except Exception:
                pass

        try:
            self._server = await websockets.serve(handler, self.address, self.port)
            await self._server.wait_closed()
        except Exception:
            pass

    def start(self):
        if self.running:
            return
        self.running = True

        def run_server():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._ws_server())

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=1.0)

    def get_latest_frame(self):
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None


class CameraCapture:
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "capture"
    CATEGORY = "camera"
    OUTPUT_NODE = False

    def __init__(self):
        self.receiver = None
        self._current_port = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "port": ("INT", {"default": 8080, "min": 1024, "max": 49151}),
                "width": ("INT", {"default": 512, "min": 64, "max": 4096}),
                "height": ("INT", {"default": 512, "min": 64, "max": 4096}),
            }
        }

    def capture(self, port=8080, width=512, height=512):
        if self.receiver is None or port != self._current_port:
            self._restart_receiver(port)
            time.sleep(0.5)

        frame = self.receiver.get_latest_frame()

        if frame is None:
            return (torch.zeros((1, height, width, 3), dtype=torch.float32),)

        img_f = frame.astype(np.float32) / 255.0
        tensor = torch.from_numpy(img_f).unsqueeze(0)

        _, h, w, _ = tensor.shape
        if h != height or w != width:
            tensor = tensor.permute(0, 3, 1, 2)
            tensor = F.interpolate(tensor, size=(height, width), mode='bilinear', align_corners=False)
            tensor = tensor.permute(0, 2, 3, 1)

        return (tensor,)

    def _restart_receiver(self, port):
        if self.receiver:
            self.receiver.stop()
        self.receiver = WebSocketImageReceiver(port)
        self.receiver.start()
        self._current_port = port

    def __del__(self):
        if self.receiver:
            self.receiver.stop()


NODE_CLASS_MAPPINGS = {"CameraCapture": CameraCapture}
NODE_DISPLAY_NAME_MAPPINGS = {"CameraCapture": "Camera Capture"}
