# Usar una imagen oficial de Python ligera
FROM python:3.10-slim

# Instalar dependencias del sistema necesarias para visión artificial
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear y establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias y ejecutarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto (incluyendo tu best.pt y main.py)
COPY . .

# Exponer el puerto del servidor web Flask
EXPOSE 5000

# Comando de arranque cuando el contenedor despierte
CMD ["python", "main.py"]