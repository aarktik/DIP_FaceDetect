import os
import sys

# Patch for Windows terminal emoji encoding issues from DeepFace
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import urllib.request
import uuid

# Optional tf-keras setup to prevent warning spam
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    from retinaface import RetinaFace
    from deepface import DeepFace
except ImportError:
    pass # Managed by the app execution flow after install

FONT_PATH = "Sarabun-Regular.ttf"

def prepare_font():
    if not os.path.exists(FONT_PATH):
        print("Downloading Thai font (Sarabun)...")
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf",
            FONT_PATH
        )

def draw_thai_text(img_bgr, text, position, font_path, font_size, color_bgr, bg_color_bgr=None):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()

    x, y = position
    bbox = draw.textbbox((x, y), text, font=font)

    if bg_color_bgr:
        bg_color_rgb = bg_color_bgr[::-1]
        draw.rectangle(bbox, fill=bg_color_rgb)

    text_color_rgb = color_bgr[::-1]
    draw.text((x, y), text, font=font, fill=text_color_rgb)

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def process_image(filepath, output_dir):
    """
    Process image using RetinaFace and DeepFace.
    Returns: output_filepath, count, male_count, female_count
    """
    prepare_font()
    # Use imdecode to support Unicode (Thai) file paths
    img = cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not read image file")

    faces = RetinaFace.detect_faces(img)

    count = 0
    male_count = 0
    female_count = 0

    if isinstance(faces, dict):
        for key in faces:
            face = faces[key]["facial_area"]
            x1, y1, x2, y2 = face

            h, w = img.shape[:2]
            pad = 20
            x1p = max(0, x1 - pad)
            y1p = max(0, y1 - pad)
            x2p = min(w, x2 + pad)
            y2p = min(h, y2 + pad)

            face_crop = img[y1p:y2p, x1p:x2p]

            gender_th = "ไม่ทราบ"
            confidence = 0
            try:
                analysis = DeepFace.analyze(
                    face_crop,
                    actions=["gender"],
                    enforce_detection=False,
                    detector_backend="skip",
                    silent=True
                )
                result = analysis[0]["gender"]
                man_score = result.get("Man", 0)
                woman_score = result.get("Woman", 0)

                if woman_score >= 40:
                    gender_th = "หญิง"
                    confidence = woman_score
                    female_count += 1
                else:
                    gender_th = "ชาย"
                    confidence = man_score
                    male_count += 1

            except Exception as e:
                print("DeepFace analysis error:", e)
                gender_th = "ไม่ทราบ"

            # Colors in BGR
            color = (147, 20, 255) if gender_th == "หญิง" else (0, 140, 255)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            label = f"{gender_th} {confidence:.0f}%"
            font_size = max(16, (y2 - y1) // 4)

            img = draw_thai_text(
                img, label,
                position=(x1, max(0, y1 - font_size - 6)),
                font_path=FONT_PATH,
                font_size=font_size,
                color_bgr=(255, 255, 255),
                bg_color_bgr=color
            )

            count += 1

    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    out_filename = f"{name}_processed_{uuid.uuid4().hex[:6]}.jpg"
    out_filepath = os.path.join(output_dir, out_filename)
    
    # Use imencode to support Unicode (Thai) file paths
    success, encoded = cv2.imencode('.jpg', img)
    if success:
        encoded.tofile(out_filepath)

    return out_filename, count, male_count, female_count
