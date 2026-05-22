#!/bin/bash

echo "=============================================="
echo "🚀 Lanzador LKA-mini V2 - Arquitectura Híbrida"
echo "=============================================="

# 1. Solicitar credenciales e IPs al usuario
read -p "📡 Ingresa la IP del ESP32 (ej. 192.168.1.15): " INPUT_ESP32_IP
read -p "📱 Ingresa la IP y puerto del teléfono (ej. 192.168.1.20:8080): " INPUT_CAM_IP
read -p "👤 Ingresa el usuario de la cámara (deja vacío si no tiene): " INPUT_USER
read -s -p "🔑 Ingresa la contraseña de la cámara (deja vacío si no tiene): " INPUT_PASS
echo ""
echo ""

# 2. Construir la URL del video de forma dinámica
if [ -z "$INPUT_USER" ]; then
    URL_CAMARA="http://${INPUT_CAM_IP}/video"
else
    URL_CAMARA="http://${INPUT_USER}:${INPUT_PASS}@${INPUT_CAM_IP}/video"
fi

URL_ESP32="http://${INPUT_ESP32_IP}"

# 3. Detectar automáticamente la IP del servidor Ubuntu
IP_SERVIDOR=$(hostname -I | awk '{print $1}')

echo "⚙️  Construyendo y Desplegando el Clúster Docker..."
echo "=============================================="

# Detener y limpiar la versión anterior (silenciando errores si es la primera vez)
sudo docker stop nodo-vision > /dev/null 2>&1
sudo docker rm nodo-vision > /dev/null 2>&1

# Construir la imagen del contenedor
sudo docker build -t lka-vision .

# Arrancar el contenedor inyectando las variables del usuario
sudo docker run -d \
  --name nodo-vision \
  -p 5000:5000 \
  -v $(pwd)/data_warehouse:/app/data_warehouse \
  -e ESP_URL="${URL_ESP32}" \
  -e CAMARA_URL="${URL_CAMARA}" \
  lka-vision

echo "=============================================="
echo "✅ DESPLIEGUE EXITOSO"
echo "=============================================="
echo "🌐 Video en vivo y Detecciones : http://${IP_SERVIDOR}:5000/video"
echo "📊 Telemetría y JSON (DW)      : http://${IP_SERVIDOR}:5000/telemetria"
echo "=============================================="
echo "🔍 Mostrando logs de red neuronal y clúster en tiempo real..."
echo "(Presiona Ctrl + C para salir de los logs, el servidor seguirá corriendo)"
echo "----------------------------------------------"

# Mostrar logs en tiempo real
sudo docker logs -f nodo-vision