from typing import Optional
import cv2
from PIL import Image
import imagehash

def video_phash_first_frame(video_path: str) -> Optional[str]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return None
    # OpenCV is BGR; convert to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    return str(imagehash.phash(img))
