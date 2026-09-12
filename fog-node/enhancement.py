"""
SentinelGrid — fog-node/enhancement.py
Pre-processes raw frames to improve OCR accuracy on license plates.
"""
import cv2
import numpy as np

def enhance_plate(image):
    # 1. Convert to grayscale to remove color noise
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Apply CLAHE to equalize lighting (fixes headlight glare and shadows)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    equalized = clahe.apply(gray)
    
    # 3. Apply a bilateral filter to smooth noise while keeping the text edges sharp
    filtered = cv2.bilateralFilter(equalized, 11, 17, 17)
    
    # 4. Optional: Adaptive thresholding to make text pop as pure black/white
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return thresh