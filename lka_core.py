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
IP_ESP32 = os.getenv("ESP_URL", "http://192.168.1.X") # Recibe la IP del Bash
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
modelo = YOLO('best.pt')  # Asegúrate de tener tu best.pt en la misma carpeta
frame_global = None       # Variable compartida para el streaming web
datos_telemetria = {}     # Datos en vivo para la web

# Variables de Estado
estado_giro = 0 
tiempo_delay = 0
estado_cruce = 0  # 0: Libre, 1: Detenido, 2: Cooldown (Ignorar cruce recién pasado)
tiempo_cruce = 0

def enviar_comando(angulo, velocidad):
    """Envía la señal HTTP al ESP32"""
    try:
        requests.get(f"{IP_ESP32}/control?steer={angulo}&speed={velocidad}", timeout=0.1)
    except:
        pass 

def guardar_metadata(frame, detectado, conf, angulo, velocidad):
    """Guarda la imagen y registra el JSON en el Data Warehouse"""
    global datos_telemetria
    timestamp = int(time.time() * 1000)
    nombre_img = f"secuencia_{timestamp}.jpg"
    ruta_img = os.path.join(CARPETA_DW, nombre_img)
    
    # Guardar foto
    cv2.imwrite(ruta_img, frame)
    
    # Estructura JSON para la base de datos
    registro = {
        "id_secuencia": timestamp,
        "archivo_imagen": nombre_img,
        "deteccion_yolo": detectado,
        "confianza": round(float(conf), 3),
        "angulo_direccion": angulo,
        "potencia_pwm": velocidad,
        "estado_sistema": "Operativo"
    }
    datos_telemetria = registro
    
    # Guardar en JSONL (Una línea por registro, ideal para Data Warehouses)
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
    
    cap = cv2.VideoCapture(os.getenv("CAMARA_URL", "http://IP_DE_TU_CELULAR:8080/video"))
    secuencia_id = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # 1. Inferencia de YOLO con confianza 0.10
        resultados = modelo(frame, conf=0.10, verbose=False)
        curva_detectada = False
        cruce_detectado = False
        mejor_confianza = 0.0
        objeto_detectado = "Ninguno"
        
        for r in resultados:
            for box in r.boxes:
                conf_actual = float(box.conf[0])
                clase_id = int(box.cls[0])
                nombre_clase = modelo.names[clase_id]
                
                if conf_actual > mejor_confianza:
                    mejor_confianza = conf_actual
                    objeto_detectado = nombre_clase

                if nombre_clase == "curva": # Ajusta al nombre exacto de tu YAML
                    curva_detectada = True
                elif nombre_clase == "cruce_peatonal": # Ajusta al nombre exacto de tu YAML
                    cruce_detectado = True

        angulo_actual = SERVO_CENTRO
        velocidad_actual = VELOCIDAD_CRUCERO

        # 2. Lógica de CRUCE PEATONAL (Prioridad Máxima)
        if cruce_detectado and estado_cruce == 0:
            print("🛑 Cruce Peatonal Detectado: Frenando...")
            angulo_actual = SERVO_CENTRO
            velocidad_actual = 0
            enviar_comando(angulo_actual, velocidad_actual)
            estado_cruce = 1
            tiempo_cruce = time.time()
            
        elif estado_cruce == 1:
            velocidad_actual = 0
            if (time.time() - tiempo_cruce) >= 5.0: # Esperar 5 segundos
                print("🟢 5s cumplidos: Reanudando marcha")
                estado_cruce = 2
                tiempo_cruce = time.time()
                velocidad_actual = VELOCIDAD_CRUCERO
                enviar_comando(SERVO_CENTRO, velocidad_actual)
                
        elif estado_cruce == 2:
            # Cooldown de 3 segundos para no volver a frenar viendo el mismo cruce
            if (time.time() - tiempo_cruce) >= 3.0:
                estado_cruce = 0

        # 3. Lógica de DIRECCIÓN (Si no está frenado por el cruce)
        if estado_cruce == 0 or estado_cruce == 2:
            if not curva_detectada and estado_giro == 0:
                cx = procesar_opencv(frame)
                if cx is not None:
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

        # 4. Registrar en Data Warehouse (Guardar 1 de cada 5 frames para no llenar el disco)
        secuencia_id += 1
        if secuencia_id % 5 == 0:
            guardar_metadata(frame, objeto_detectado, mejor_confianza, angulo_actual, velocidad_actual)

        # Actualizar video para el servidor web
        frame_global = frame.copy()

    cap.release()

# --- RUTAS DEL SERVIDOR WEB (FLASK) ---
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
    return "<h1>LKA-mini Servidor Activo</h1><p>Ve a /video para ver la cámara y a /telemetria para ver el JSON.</p>"

@app.route('/video')
def video_feed():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetria')
def telemetria():
    return jsonify(datos_telemetria)

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == '__main__':
    # Iniciar la visión en un hilo paralelo
    hilo_vision = threading.Thread(target=hilo_vision_autonoma)
    hilo_vision.daemon = True
    hilo_vision.start()
    
    # Iniciar el servidor web en el puerto 5000 (Accesible desde tu teléfono)
    print("Iniciando Servidor Web. Entra a http://IP_DE_UBUNTU:5000/video en tu teléfono.")
    app.run(host='0.0.0.0', port=5000, debug=False)