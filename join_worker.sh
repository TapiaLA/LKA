#!/bin/bash

echo "=============================================="
echo "🤖 LKA-mini V2 - Conectar Nodo Worker al Clúster"
echo "=============================================="
echo "Asegúrate de tener Docker instalado antes de continuar."
echo ""

# Solicitar los datos de conexión al usuario
read -p "🖥️ Ingresa la IP del Nodo Manager (Tu Servidor Ubuntu): " MANAGER_IP
read -p "🔑 Ingresa el Token de Worker (proporcionado por el Manager): " SWARM_TOKEN
echo ""

echo "⚙️ Conectando al enjambre de Docker Swarm..."
echo "----------------------------------------------"

# Ejecutar el comando de unión al clúster
sudo docker swarm join --token "${SWARM_TOKEN}" "${MANAGER_IP}:2377"

echo "----------------------------------------------"
echo "✅ Secuencia finalizada. Verifica con el Manager si la conexión fue exitosa."
echo "=============================================="