import cv2


def enhance_crop(image_bgr, low_quality: bool = False):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    upscale = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_LANCZOS4)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(upscale)
    if low_quality:
        return cv2.fastNlMeansDenoising(clahe, None, 10, 7, 21)
    return clahe
