import base64
import io

import numpy as np
import requests
import torch
from PIL import Image


class CameraCapture:
    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT")
    RETURN_NAMES = ("image", "width", "height", "rotation_degrees")
    FUNCTION = "capture"
    CATEGORY = "camera"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "port": ("INT", {"default": 8080, "min": 1024, "max": 49151}),
                "timeout": ("FLOAT", {"default": 5.0, "min": 1.0, "max": 30.0, "step": 0.5}),
            }
        }

    @classmethod
    def IS_CHANGED(cls):
        return True

    def capture(self, port, timeout):
        url = f"http://127.0.0.1:{port}/frame"

        try:
            with requests.Session() as session:
                session.timeout = timeout

                response = session.get(url)

                if response.status_code == 200:
                    data = response.json()

                    if data.get("status") == "success":
                        image_bytes = base64.b64decode(data["image_bytes"])

                        width = data["width"]

                        height = data["height"]

                        rotation_degrees = data["rotation_degrees"]

                        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

                        arr = np.asarray(img).astype(np.float32) / 255.0

                        tensor = torch.from_numpy(arr).unsqueeze(0)

                        return tensor, width, height, rotation_degrees
                    else:
                        error = data["error"]

                        print(f"Server error: {error}")
                else:
                    print(f"HTTP error: {response.status_code}")

        except requests.exceptions.Timeout:
            print("Server connection timeout")
        except requests.exceptions.ConnectionError:
            print("Server connection error")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        return torch.zeros((1, 512, 512, 3), dtype=torch.float32), 512, 512, 0


NODE_CLASS_MAPPINGS = {"CameraCapture": CameraCapture}
NODE_DISPLAY_NAME_MAPPINGS = {"CameraCapture": "Camera Capture"}
