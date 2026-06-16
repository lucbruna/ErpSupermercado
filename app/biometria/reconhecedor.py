import cv2
import os
import pickle
import numpy as np
from datetime import datetime

CASCADE_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'cascade', 'haarcascade_frontalface_default.xml')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'biometria')
MODEL_PATH = os.path.join(DATA_DIR, 'modelo.yml')
LABELS_PATH = os.path.join(DATA_DIR, 'labels.pkl')
os.makedirs(DATA_DIR, exist_ok=True)

_recognizer = None
_label_map = {}

def _carregar_cascade():
    path = CASCADE_PATH
    if not os.path.exists(path):
        _baixar_cascade(path)
    return cv2.CascadeClassifier(path)

def _baixar_cascade(path):
    import urllib.request
    url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'
    try:
        urllib.request.urlretrieve(url, path)
    except Exception:
        cv2.data.haarcascades  # fallback
        alt = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        if os.path.exists(alt):
            import shutil
            shutil.copy(alt, path)

def capturar_rosto(frame):
    cascade = _carregar_cascade()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
    if len(faces) == 0:
        return None, None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    rosto = gray[y:y+h, x:x+w]
    rosto = cv2.resize(rosto, (200, 200))
    return rosto, (x, y, w, h)

def treinar(usuario_id, rosto_gray):
    label = int(usuario_id)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    labels_path = os.path.join(DATA_DIR, f'user_{label}.jpg')
    cv2.imwrite(labels_path, rosto_gray)
    rostos = []
    labels = []
    for f in os.listdir(DATA_DIR):
        if f.startswith('user_') and f.endswith('.jpg'):
            img = cv2.imread(os.path.join(DATA_DIR, f), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                rostos.append(img)
                labels.append(int(f.replace('user_', '').replace('.jpg', '')))
    if len(rostos) < 1:
        return False
    recognizer.train(rostos, np.array(labels))
    recognizer.write(MODEL_PATH)
    return True

def reconhecer(rosto_gray, confidence_threshold=70):
    path = MODEL_PATH
    if not os.path.exists(path):
        return None, None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(path)
    label, confidence = recognizer.predict(rosto_gray)
    if confidence > confidence_threshold:
        return None, None
    return label, confidence

def fotos_cadastradas():
    return [f for f in os.listdir(DATA_DIR) if f.startswith('user_') and f.endswith('.jpg')]
