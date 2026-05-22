# 🚗 LKA-mini V2: Sistema de Visión Híbrida y Telemetría Autónoma

Este repositorio contiene la arquitectura de software del nodo de percepción visual para el vehículo autónomo LKA-mini. El sistema utiliza una arquitectura híbrida integrando **YOLOv8** (para detección de cruces peatonales y curvas) y **OpenCV** (para seguimiento de carril). 

Además, incorpora un servidor web en **Flask** para transmisión de video en tiempo real y un *Data Warehouse* ligero (JSON Lines) para la recolección de telemetría IoT. Todo el entorno está contenerizado y orquestado mediante **Docker Swarm**.

---

## 📋 1. Requisitos Previos (Para la Líder de Proyecto)

Antes de ejecutar el clúster, el servidor (Ubuntu Server o similar) debe contar con:
* **Docker Engine** instalado.
* **Python 3.10+** (solo si se desean hacer pruebas en local fuera del contenedor).
* Los pesos entrenados de la red neuronal (`best.pt`) colocados en la raíz de este directorio.

Si se realizarán pruebas locales sin Docker, instalar las librerías base ejecutando:
```bash
pip install -r requirements.txt

🐳 2. Inicialización del Clúster (Docker Swarm)
Para que el servidor actúe como el nodo maestro (Manager) de nuestra arquitectura distribuida, inicializar el enjambre de contenedores con el siguiente comando:

Bash
sudo docker swarm init
(Nota: Guardar el token generado por la terminal si en el futuro se desean añadir nodos esclavos al procesamiento).

🚀 3. Despliegue del Nodo de Visión
El despliegue se divide en dos pasos: construir la imagen empaquetando nuestras librerías y ejecutar el contenedor haciendo un puente (volumen) para salvar nuestras fotografías.

Paso 3.1: Construir la imagen de Docker
Ejecutar este comando estando dentro de la carpeta del proyecto:

Bash
sudo docker build -t lka-vision .
Paso 3.2: Arrancar el contenedor
Este comando lanza el sistema, expone el puerto 5000 para Flask y crea el túnel de persistencia de datos para el Data Warehouse:

Bash
sudo docker run -d \
  --name nodo-vision \
  -p 5000:5000 \
  -v $(pwd)/data_warehouse:/app/data_warehouse \
  lka-vision
📡 5. Monitoreo y Telemetría en Vivo
Una vez que el contenedor esté corriendo (sudo docker ps para confirmar), el sistema comenzará a procesar el video y a registrar la metadata automáticamente.

Para acceder al sistema desde cualquier dispositivo (teléfono o PC) conectado a la misma red Wi-Fi, abre el navegador y dirígete a:

📷 Cámara y Detecciones en Vivo: http://<IP_DEL_SERVIDOR>:5000/video

📊 Data Warehouse (JSON en tiempo real): http://<IP_DEL_SERVIDOR>:5000/telemetria

🛑 Detener y Limpiar el Sistema
Si necesitas apagar el nodo o actualizar el código, ejecuta:

Bash
sudo docker stop nodo-vision
sudo docker rm nodo-vision

3. Darle Permisos y Ejecutarlo
Para que Ubuntu te permita correr este archivo interactivo, debes darle permisos de ejecución por única vez. En tu terminal escribe:

Bash
chmod +x deploy.sh
¡Y listo! De ahora en adelante, todo el proyecto se arranca simplemente escribiendo esto en la terminal:

Bash
./deploy.sh