import cv2
import time
import requests
import numpy as np
import json
import os
import threading
from flask import Flask, Response, jsonify
from ultralytics import YOLO

# --- CONFIGURACIÓN DE RED Y CINEMÁTICA ---
IP_ESP32 = os.getenv("ESP_URL", "http://192.168.1.100") # Ya no se usará
SERVO_CENTRO = 90
SERVO_CURVA_IZQ = 145      
SERVO_PRE_CURVA = 75       
VELOCIDAD_CRUCERO = 180    
VELOCIDAD_LENTA = 100
TIEMPO_5CM = 0.4           

# --- CONFIGURACIÓN DATA WAREHOUSE ---
CARPETA_DW = "data_warehouse/imagenes"
ARCHIVO_JSON = "data_warehouse/registro_datos.jsonl"
os.makedirs(CARPETA_DW, exist_ok=True)

# --- INICIALIZACIÓN ---
app = Flask(__name__)
modelo = YOLO('best.pt')  

# --- LA LÍNEA MÁGICA CORREGIDA ---
# Forzamos los nombres correctos para arreglar el cruce de etiquetas del entrenamiento
modelo.model.names = {0: 'linea_blanca', 1: 'linea_amarilla', 2: 'cruce_peatonal'}

frame_global = None       
datos_telemetria = {}     

# Variables de Estado
estado_giro = 0 
tiempo_delay = 0
estado_cruce = 0  # 0: Libre, 1: Detenido, 2: Cooldown
tiempo_cruce = 0

def enviar_comando(angulo, velocidad):
    """
    ¡MODO MANUAL ACTIVADO! 
    Esta función está vacía (pass) para que NO envíe señales al ESP32.
    Tú controlarás el hardware, la IA solo hará la parte visual.
    """
    pass 

def guardar_metadata(frame, detectado, conf, angulo, velocidad):
    global datos_telemetria
    timestamp = int(time.time() * 1000)
    nombre_img = f"secuencia_{timestamp}.jpg"
    ruta_img = os.path.join(CARPETA_DW, nombre_img)
    
    cv2.imwrite(ruta_img, frame)
    
    registro = {
        "id_secuencia": timestamp,
        "archivo_imagen": nombre_img,
        "deteccion_yolo": detectado,
        "confianza": round(float(conf), 3),
        "angulo_direccion_calculado": angulo,
        "estado_sistema": "Modo Visual Manual"
    }
    datos_telemetria = registro
    
    with open(ARCHIVO_JSON, "a") as f:
        f.write(json.dumps(registro) + "\n")

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
    global frame_global, estado_giro, tiempo_delay, estado_cruce, tiempo_cruce
    
    # URL con credenciales directas
    cap = cv2.VideoCapture(os.getenv("CAMARA_URL", "http://LKA:12345678@192.168.0.110:8080/video"))
    secuencia_id = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # 1. Inferencia de YOLO
        resultados = modelo(frame, conf=0.10, verbose=False)
        
        # 1.5 DIBUJAR CAJAS EN EL FRAME (Para la evidencia visual)
        frame_visual = resultados[0].plot()

        curva_detectada = False
        cruce_detectado = False
        mejor_confianza = 0.0
        objeto_detectado = "Ninguno"
        
        for r in resultados:
            for box in r.boxes:
                conf_actual = float(box.conf[0])
                clase_id = int(box.cls[0])
                nombre_clase = modelo.model.names[clase_id] # Usamos la línea mágica
                
                if conf_actual > mejor_confianza:
                    mejor_confianza = conf_actual
                    objeto_detectado = nombre_clase

                # --- SECCIÓN ACTUALIZADA CON LOS NUEVOS NOMBRES ---
                if nombre_clase == "linea_amarilla": 
                    curva_detectada = True
                elif nombre_clase == "linea_blanca": # El modelo lo llama línea blanca pero es el cruce
                    cruce_detectado = True

        angulo_actual = SERVO_CENTRO
        velocidad_actual = VELOCIDAD_CRUCERO

        # 2. Lógica Visual de CRUCE PEATONAL
        if cruce_detectado and estado_cruce == 0:
            angulo_actual = SERVO_CENTRO
            velocidad_actual = 0
            enviar_comando(angulo_actual, velocidad_actual)
            estado_cruce = 1
            tiempo_cruce = time.time()
            
        elif estado_cruce == 1:
            velocidad_actual = 0
            if (time.time() - tiempo_cruce) >= 5.0:
                estado_cruce = 2
                tiempo_cruce = time.time()
                velocidad_actual = VELOCIDAD_CRUCERO
                enviar_comando(SERVO_CENTRO, velocidad_actual)
                
        elif estado_cruce == 2:
            if (time.time() - tiempo_cruce) >= 3.0:
                estado_cruce = 0

        # 3. Lógica Visual de DIRECCIÓN (OpenCV)
        if estado_cruce == 0 or estado_cruce == 2:
            if not curva_detectada and estado_giro == 0:
                cx = procesar_opencv(frame)
                if cx is not None:
                    # DIBUJAR EL PUNTO DE OPENCV EN VERDE
                    cv2.circle(frame_visual, (cx, int(frame_visual.shape[0]/2)), 15, (0, 255, 0), -1)
                    angulo_actual = int(90 + ((cx - 320) / 10))
                    enviar_comando(angulo_actual, velocidad_actual)
                    
            elif curva_detectada and estado_giro == 0:
                angulo_actual = SERVO_PRE_CURVA
                enviar_comando(angulo_actual, velocidad_actual)
                estado_giro = 1
                
            elif estado_giro == 1:
                tiempo_delay = time.time()
                estado_giro = 2
                
            elif estado_giro == 2:
                if (time.time() - tiempo_delay) >= TIEMPO_5CM:
                    angulo_actual = SERVO_CURVA_IZQ
                    enviar_comando(angulo_actual, velocidad_actual)
                    estado_giro = 3
                    
            elif not curva_detectada and estado_giro == 3:
                angulo_actual = SERVO_CENTRO
                enviar_comando(angulo_actual, velocidad_actual)
                estado_giro = 0

        # 4. Registrar Data Warehouse
        secuencia_id += 1
        if secuencia_id % 5 == 0:
            guardar_metadata(frame_visual, objeto_detectado, mejor_confianza, angulo_actual, velocidad_actual)

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
    return "<h1>LKA-mini Servidor Activo (Modo Visual)</h1><p>Ve a /video para ver la cámara con IA.</p>"

@app.route('/video')
def video_feed():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetria')
def telemetria():
    return jsonify(datos_telemetria)

if __name__ == '__main__':
    hilo_vision = threading.Thread(target=hilo_vision_autonoma)
    hilo_vision.daemon = True
    hilo_vision.start()
    
    print("Iniciando Servidor Web. Entra a http://localhost:5000/video para ver la IA operando.")
    app.run(host='0.0.0.0', port=5000, debug=False)