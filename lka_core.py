import cv2
import time
import requests
import numpy as np
import json
import os
import threading
from flask import Flask, Response, jsonify
from ultralytics import YOLO

# --- CONFIGURACIÓN DATA WAREHOUSE ---
CARPETA_DW = "data_warehouse/imagenes"
ARCHIVO_JSON = "data_warehouse/registro_datos.jsonl"
os.makedirs(CARPETA_DW, exist_ok=True)

# --- INICIALIZACIÓN ---
app = Flask(__name__)
modelo = YOLO('best.pt')  

# --- LA LÍNEA MÁGICA CORREGIDA ---
modelo.model.names = {0: 'linea_blanca', 1: 'linea_amarilla', 2: 'cruce_peatonal'}

frame_global = None       
datos_telemetria = {}     

def enviar_comando(angulo, velocidad):
    """
    ¡MODO MANUAL ACTIVADO PARA LA EVIDENCIA!
    La IA analiza el video, pero NO mueve el motor. Tú lo controlas con el teclado/celular.
    """
    pass 

def procesar_opencv(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    bajo_amarillo = np.array([20, 100, 100])
    alto_amarillo = np.array([30, 255, 255])
    mascara = cv2.inRange(hsv, bajo_amarillo, alto_amarillo)
    momentos = cv2.moments(mascara)
    if momentos["m00"] > 0:
        return int(momentos["m10"] / momentos["m00"])
    return None

def hilo_vision_autonoma():
    global frame_global
    
    # URL DE TU CÁMARA YA CONFIGURADA
    cap = cv2.VideoCapture(os.getenv("CAMARA_URL", "http://LKA:12345678@192.168.0.110:8080/video"))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # Inferencia de YOLO
        resultados = modelo(frame, conf=0.10, verbose=False)
        
        # DIBUJAR CAJAS PARA EL VIDEO DE EVIDENCIA
        frame_visual = resultados[0].plot()
        
        # DIBUJAR PUNTO VERDE DE OPENCV
        cx = procesar_opencv(frame)
        if cx is not None:
            cv2.circle(frame_visual, (cx, int(frame_visual.shape[0]/2)), 15, (0, 255, 0), -1)

        # Actualizar video para el servidor web
        frame_global = frame_visual.copy()

    cap.release()

# --- RUTAS DEL SERVIDOR WEB ---
def generar_video():
    global frame_global
    while True:
        if frame_global is not None:
            ret, buffer = cv2.imencode('.jpg', frame_global)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05)

@app.route('/')
def index():
    return "<h1>LKA-mini Servidor Activo (Modo Visual)</h1><p>Ve a /video para ver la IA.</p>"

@app.route('/video')
def video_feed():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    hilo_vision = threading.Thread(target=hilo_vision_autonoma)
    hilo_vision.daemon = True
    hilo_vision.start()
    app.run(host='0.0.0.0', port=5000, debug=False)