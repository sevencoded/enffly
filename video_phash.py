from PIL import Image
import imagehash
import io

def phash_from_image_bytes(data: bytes) -> str:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return str(imagehash.phash(img))
