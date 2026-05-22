import cv2
from ultralytics import YOLO

# Cargar tu modelo YOLO entrenado
model = YOLO('best.pt')

# --- LA LÍNEA MÁGICA CORREGIDA ---
model.model.names = {0: 'linea_blanca', 1: 'linea_amarilla', 2: 'cruce_peatonal'}

# --- UMBRAL DE CONFIANZA ---
# Valores entre 0.0 y 1.0. 
# 0.20 significa que detectará todo lo que tenga al menos 20% de seguridad.
# Bájalo si quieres ver más cajas, súbelo si quieres eliminar cajas basura.
NIVEL_CONFIANZA = 0.10 

# 1. Conectar tu cámara IP
cap = cv2.VideoCapture('http://LKA:12345678@192.168.0.142:8080/video')

while True:
    ret, frame = cap.read()
    if not ret:
        print("Buscando señal de la cámara...")
        continue

    # 2. Hacer predicción con YOLO inyectando la variable de confianza
    resultados = model(frame, conf=NIVEL_CONFIANZA, verbose=False)
    
    # 3. Dibujar las cajas y etiquetas en el video
    frame_anotado = resultados[0].plot()

    # 4. Obtener las coordenadas para el Yugo Escocés
    if len(resultados[0].boxes) > 0:
        caja = resultados[0].boxes[0]
        
        # Coordenadas y dimensiones
        centro_x = int(caja.xywh[0][0])
        centro_y = int(caja.xywh[0][1])
        
        print(f"Coordenada para el Yugo Escocés -> X: {centro_x}")
        
        # Dibujamos el punto rojo
        cv2.circle(frame_anotado, (centro_x, centro_y), 15, (0, 0, 255), -1)

    # Mostrar la ventana
    cv2.imshow("Detección con YOLO (Confianza Ajustada)", frame_anotado)

    # Presiona 'q' para salir
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()