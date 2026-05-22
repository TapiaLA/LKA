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
```
🚀 2. Despliegue Automatizado (Recomendado)
Para facilitar el arranque del sistema con un solo comando, hemos incluido un script interactivo que inyecta las variables de entorno automáticamente.

Paso 2.1: Otorgar permisos de ejecución
Por única vez, otorga permisos al script lanzador:

```Bash
chmod +x deploy.sh
```
Paso 2.2: Iniciar el clúster
Ejecuta el script y sigue las instrucciones en pantalla para ingresar las credenciales de la cámara y la IP del hardware:

```Bash
./deploy.sh
```
🐳 3. Despliegue Manual (Docker Swarm)
Si prefieres levantar la arquitectura paso a paso sin el script automatizado:

Paso 3.1: Inicialización del Clúster
Para que el servidor actúe como el nodo maestro (Manager), inicializa el enjambre:

```Bash
sudo docker swarm init
```
(Nota: Guarda el token generado si deseas añadir nodos Worker al procesamiento).

Paso 3.2: Construir la imagen de Docker

```Bash
sudo docker build -t lka-vision .
```
Paso 3.3: Arrancar el contenedor
Este comando lanza el sistema, expone el puerto para Flask y crea el túnel de persistencia de datos para el Data Warehouse:

```Bash
sudo docker run -d \
  --name nodo-vision \
  -p 5000:5000 \
  -v $(pwd)/data_warehouse:/app/data_warehouse \
  lka-vision
  ```
📡 4. Monitoreo y Telemetría en Vivo
Una vez que el contenedor esté corriendo (sudo docker ps para confirmar), el sistema comenzará a procesar el video y a registrar la metadata automáticamente.

Para acceder al sistema desde cualquier dispositivo conectado a la misma red Wi-Fi, abre el navegador y dirígete a:

📷 Cámara y Detecciones en Vivo: http://<IP_DEL_SERVIDOR>:5000/video

📊 Data Warehouse (JSON en tiempo real): http://<IP_DEL_SERVIDOR>:5000/telemetria

🛑 5. Detener y Limpiar el Sistema
Si necesitas apagar el nodo o actualizar el código de visión, ejecuta:

```Bash
sudo docker stop nodo-vision
sudo docker rm nodo-vision
```