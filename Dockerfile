# Usa una imagen base de Python
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de requisitos
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY . .

# Expone el puerto en el que la aplicación escuchará (ajusta si es necesario)
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD ["python", "bot.py"]  # Cambia 'bot.py' por el nombre de tu archivo principal si es diferente