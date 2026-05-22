import cv2
import numpy as np
import requests
from ultralytics import YOLO
from flask import Flask, Response

# 1. Configuración de Flask para el streaming
app = Flask(__name__)

# 2. Configurar YOLO
model = YOLO('best.pt')
model.model.names = {0: 'linea_blanca', 1: 'linea_amarilla', 2: 'cruce_peatonal'}
NIVEL_CONFIANZA = 0.15

# 3. Configurar colores para OpenCV (Ajusta estos valores para tu línea amarilla)
AMARILLO_BAJO = np.array([15, 100, 100])
AMARILLO_ALTO = np.array([30, 255, 255])

# IP de tu ESP32-CAM
ESP32_IP = "192.168.0.142"
URL_VIDEO = f'http://LKA:12345678@{ESP32_IP}:8080/video'

def procesar_vision():
    cap = cv2.VideoCapture(URL_VIDEO)

    while True:
        ret, frame = cap.read()
        if not ret: continue

        # Convertir a HSV para OpenCV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        centro_x = 0

        # Hacer predicción con YOLO
        resultados = model(frame, conf=NIVEL_CONFIANZA, verbose=False)
        frame_anotado = resultados[0].plot()

        # Extraer cajas de líneas amarillas (clase 1)
        cajas_linea = [box for box in resultados[0].boxes if int(box.cls[0]) == 1]

        # LOGICA HÍBRIDA + RESPALDO
        if len(cajas_linea) > 0:
            # MODO 1: YOLO encontró la línea. Usamos el ROI.
            caja = cajas_linea[0]
            x1, y1, x2, y2 = map(int, caja.xyxy[0]) # Coordenadas de las esquinas
            
            # Recortamos la imagen (ROI)
            roi_hsv = hsv[y1:y2, x1:x2]
            mascara = cv2.inRange(roi_hsv, AMARILLO_BAJO, AMARILLO_ALTO)
            
            # Buscamos el centro solo en el recorte
            M = cv2.moments(mascara)
            if M["m00"] != 0:
                centro_x_roi = int(M["m10"] / M["m00"])
                centro_x = x1 + centro_x_roi # Ajustamos a la coordenada de la pantalla completa
                cv2.putText(frame_anotado, "MODO: YOLO+OpenCV", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        else:
            # MODO 2: YOLO falló. OpenCV toma el control total (Respaldo).
            mascara = cv2.inRange(hsv, AMARILLO_BAJO, AMARILLO_ALTO)
            M = cv2.moments(mascara)
            if M["m00"] != 0:
                centro_x = int(M["m10"] / M["m00"])
                cv2.putText(frame_anotado, "MODO: OpenCV FALLBACK!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Si tenemos un centro válido, dibujamos y ENVIAMOS AL ESP32
        if centro_x != 0:
            cv2.circle(frame_anotado, (centro_x, int(frame.shape[0]/2)), 15, (0, 0, 255), -1)
            
            # --- MANDAR INSTRUCCIÓN AL ESP32 ---
            # Descomenta esto cuando el código de tu ESP32 esté listo para recibir peticiones
            # try:
            #     requests.get(f"http://{ESP32_IP}/volante?x={centro_x}", timeout=0.1)
            # except:
            #     pass # Ignorar errores de red para no frenar el video

        # 4. Codificar la imagen en JPEG para transmitirla por la red
        ret, buffer = cv2.imencode('.jpg', frame_anotado)
        frame_bytes = buffer.tobytes()
        
        # Formato mágico para que el navegador lo vea como video
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Ruta web para ver el video
@app.route('/')
def ver_video():
    return Response(procesar_vision(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Arranca el servidor web en el puerto 5000 (Accesible desde cualquier PC en tu red)
    print("Iniciando servidor de visión. Entra a http://<IP_DE_TU_UBUNTU>:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)