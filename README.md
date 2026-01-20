# ♻️ Sistema de Clasificación de Basura Inteligente

Este proyecto implementa un sistema de clasificación de residuos utilizando una **cámara**, un **servidor Flask**, la **API de Gemini** para el reconocimiento de imágenes y un **Arduino** para el control físico de los contenedores.


## ⚙️ Flujo de Trabajo

1. La interfaz web muestra el video en vivo de la cámara.
2. Al presionar **"Clasificar Objeto"**, se captura un fotograma.
3. La imagen se envía a la **API de Gemini** para su clasificación.
4. Gemini responde con un **JSON** que incluye:
   - Tipo de material
   - Objetos detectados
   - Respuesta hablada
5. El resultado se guarda en la base de datos `historial.db`.
6. El material se envía al **Arduino** mediante puerto serial.
7. El Arduino responde con `"OK"`.
8. La interfaz web se actualiza y reproduce la respuesta hablada.

---

## 🛠️ Tecnologías Utilizadas

- **Python** - Backend y lógica principal
- **Flask** - Servidor web
- **OpenCV** - Procesamiento de cámara
- **Gemini API** - Reconocimiento de imágenes con IA
- **Arduino** - Control de hardware
- **SQLite** - Base de datos local

---


---

## 📂 Estructura del Proyecto
```
basura_inteligente/
│
├── app.py                  # Servidor Flask principal
├── camera.py               # Lógica para manejar la cámara con OpenCV
├── gemini_client.py        # Cliente para la API de Gemini
├── arduino_serial.py       # Comunicación Serial con Arduino
├── database.py             # Conexión y funciones para la base de datos SQLite
│
├── static/
│   └── style.css           # Estilos para la interfaz web
│
├── templates/
│   └── index.html          # Interfaz web principal
│
├── requirements.txt        # Dependencias de Python
└── README.md               # Esta documentación
```

---

## 🚀 Instalación

### 1. Clonar o descargar el proyecto
Copia todos los archivos en una carpeta llamada `basura_inteligente`.

```bash
git clone https://github.com/cexartattoo/ClasificacionBasuraGamini.git basura_inteligente
```

### 2. Crear un entorno virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate      # En Linux/Mac
venv\Scripts\activate         # En Windows
```

### 3. Instalar dependencias
Asegúrate de tener el archivo `requirements.txt` y ejecuta:
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
- **API Key de Gemini**: Reemplaza el placeholder `"TU_API_KEY_AQUI"` en `gemini_client.py` con tu clave real.
- **Puerto Serial del Arduino**: Configura el puerto en `arduino_serial.py` (ejemplo: `COM3` en Windows o `/dev/ttyUSB0` en Linux).

---

## 🏃‍♂️ Cómo ejecutar el sistema

### 1. Cargar el código en Arduino
Sube un sketch simple que lea los comandos seriales (`PLASTICO`, `ORGANICO`, `METAL`) y responda con `"OK\n"` después de procesarlos.

### 2. Iniciar el servidor Flask
Desde la carpeta raíz del proyecto:
```bash
python app.py
```

### 3. Acceder a la interfaz web
Abre tu navegador en [http://127.0.0.1:5000](http://127.0.0.1:5000)

Allí verás la transmisión en vivo de la cámara y el historial de clasificación.

---

## 📝 Notas

- Asegúrate de tener permisos de acceso a la cámara
- Verifica que el puerto serial del Arduino esté correctamente configurado
- La API de Gemini requiere conexión a internet

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 👨‍💻 Autor

César Ramírez H.
@cexartatto (Ig)
Cez Art (Fb)
