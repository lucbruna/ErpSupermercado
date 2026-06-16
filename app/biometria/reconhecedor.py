import cv2
import os
import pickle
import numpy as np
import urllib.request

CASCADE_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'cascade', 'haarcascade_frontalface_default.xml')
SFACE_MODEL_URL = 'https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition/sface/face_recognition_sface_2021dec.onnx'
SFACE_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'cascade', 'face_recognition_sface_2021dec.onnx')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'biometria')
EMBEDDINGS_PATH = os.path.join(DATA_DIR, 'embeddings.pkl')
os.makedirs(DATA_DIR, exist_ok=True)

COSINE_THRESHOLD = 0.35

_recognizer = None

def _baixar(url, path):
    if not os.path.exists(path):
        try:
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            raise RuntimeError(f'Falha ao baixar {url}: {e}')

def _carregar_cascade():
    if not os.path.exists(CASCADE_PATH):
        _baixar('https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml', CASCADE_PATH)
    return cv2.CascadeClassifier(CASCADE_PATH)

def _carregar_recognizer():
    global _recognizer
    if _recognizer is None:
        if not os.path.exists(SFACE_MODEL_PATH):
            _baixar(SFACE_MODEL_URL, SFACE_MODEL_PATH)
        _recognizer = cv2.FaceRecognizerSF_create(SFACE_MODEL_PATH, '')
    return _recognizer

def capturar_rosto(frame):
    cascade = _carregar_cascade()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
    if len(faces) == 0:
        return None, None, None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    rosto_gray = gray[y:y+h, x:x+w]
    rosto_gray = cv2.resize(rosto_gray, (200, 200))
    rosto_color = frame[y:y+h, x:x+w]
    rosto_color = cv2.resize(rosto_color, (112, 112))
    return rosto_gray, rosto_color, (x, y, w, h)

def _extrair_embedding(rosto_color):
    rec = _carregar_recognizer()
    return rec.feature(rosto_color)

def treinar(usuario_id, rosto_color):
    embedding = _extrair_embedding(rosto_color)
    embeddings = _carregar_embeddings()
    usuario_id = int(usuario_id)
    embeddings[usuario_id] = embedding
    _salvar_embeddings(embeddings)
    return True

def reconhecer(rosto_color, confidence_threshold=COSINE_THRESHOLD):
    embeddings = _carregar_embeddings()
    if not embeddings:
        return None, None
    emb_atual = _extrair_embedding(rosto_color)
    melhor_id = None
    melhor_dist = float('inf')
    for uid, emb in embeddings.items():
        dist = _cosine_distance(emb_atual, emb)
        if dist < melhor_dist:
            melhor_dist = dist
            melhor_id = uid
    if melhor_dist > confidence_threshold:
        return None, None
    return melhor_id, float(melhor_dist)

def _cosine_distance(a, b):
    a = a.flatten()
    b = b.flatten()
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1 - dot / (norm_a * norm_b)

def _carregar_embeddings():
    if not os.path.exists(EMBEDDINGS_PATH):
        return {}
    with open(EMBEDDINGS_PATH, 'rb') as f:
        return pickle.load(f)

def _salvar_embeddings(embeddings):
    with open(EMBEDDINGS_PATH, 'wb') as f:
        pickle.dump(embeddings, f)

def fotos_cadastradas():
    return [str(k) for k in _carregar_embeddings().keys()]
