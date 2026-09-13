"""
SentinelGrid — scripts/generate_sample_data.py
Generates sample license plate images and negative test images (garbage text/noise)
for dataset evaluation, along with the ground-truth manifest.json.
"""

import os
import json
import numpy as np

def create_sample_images():
    import cv2
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_images")
    os.makedirs(output_dir, exist_ok=True)

    samples = [
        {
            "filename": "MH12AB1284.jpg",
            "ground_truth": "MH12AB1284",
            "is_plate": True,
            "text": "MH 12 AB 1284",
            "bg_color": (245, 245, 245),
            "text_color": (20, 20, 20),
            "has_car": True
        },
        {
            "filename": "DL08AF5023.jpg",
            "ground_truth": "DL08AF5023",
            "is_plate": True,
            "text": "DL 08 AF 5023",
            "bg_color": (240, 240, 240),
            "text_color": (15, 15, 15),
            "has_car": True
        },
        {
            "filename": "KA05MN1234.jpg",
            "ground_truth": "KA05MN1234",
            "is_plate": True,
            "text": "KA 05 MN 1234",
            "bg_color": (245, 245, 245),
            "text_color": (25, 25, 25),
            "has_car": True
        },
        {
            "filename": "garbage_billboard.jpg",
            "ground_truth": None,
            "is_plate": False,
            "text": "SUPER SHOPPING MALL SALE",
            "bg_color": (50, 180, 220),
            "text_color": (255, 255, 255),
            "has_car": False
        },
        {
            "filename": "noise_sign.jpg",
            "ground_truth": None,
            "is_plate": False,
            "text": "SPEED LIMIT 50 KM/H",
            "bg_color": (220, 220, 220),
            "text_color": (10, 10, 220),
            "has_car": False
        }
    ]

    manifest = {}

    for s in samples:
        path = os.path.join(output_dir, s["filename"])
        
        if s["has_car"]:
            # Create a 640x480 scene representing a vehicle front with license plate
            img = np.full((480, 640, 3), (70, 70, 75), dtype=np.uint8)
            # Vehicle hood / grill
            cv2.rectangle(img, (80, 100), (560, 420), (35, 45, 55), -1)
            cv2.rectangle(img, (140, 200), (500, 320), (20, 20, 25), -1) # grill
            # Headlights
            cv2.circle(img, (120, 250), 30, (230, 240, 250), -1)
            cv2.circle(img, (520, 250), 30, (230, 240, 250), -1)
            
            # License Plate Area (centered in lower half)
            px1, py1, px2, py2 = 180, 330, 460, 395
            cv2.rectangle(img, (px1-4, py1-4), (px2+4, py2+4), (0, 0, 0), -1) # plate border
            cv2.rectangle(img, (px1, py1), (px2, py2), s["bg_color"], -1) # plate face
            
            # Blue IND strip on the left
            cv2.rectangle(img, (px1, py1), (px1 + 25, py2), (180, 100, 0), -1)
            cv2.putText(img, "IND", (px1 + 2, py1 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            # Registration Number
            cv2.putText(img, s["text"], (px1 + 35, py1 + 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, s["text_color"], 3)
        else:
            # Sign / billboard scene
            img = np.full((360, 600, 3), (80, 80, 80), dtype=np.uint8)
            cv2.rectangle(img, (40, 40), (560, 320), s["bg_color"], -1)
            cv2.putText(img, s["text"], (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.9, s["text_color"], 2)

        cv2.imwrite(path, img)
        print(f"Generated test image: {path}")

        manifest[s["filename"]] = {
            "ground_truth": s["ground_truth"],
            "is_plate": s["is_plate"]
        }

    manifest_file = os.path.join(output_dir, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest created at: {manifest_file}")

if __name__ == "__main__":
    create_sample_images()

