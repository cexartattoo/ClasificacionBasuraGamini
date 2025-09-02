# -*- coding: utf-8 -*-
"""
Module de Cámara y Visión por Computadora (camera.py)

Este es uno de los módulos más importantes del sistema. Se encarga de
gestionar la cámara, procesar el video en tiempo real y determinar
el estado del sistema de detección (presencia y estabilidad de objetos).

Arquitectura:
- Utiliza un hilo (thread) de procesamiento dedicado que se ejecuta en segundo
  plano para analizar continuamente los fotogramas de la cámara. Esto evita
  bloquear el servidor Flask y permite un análisis de video fluido.
- El hilo realiza todas las operaciones de visión por computadora (OpenCV),
  como la sustracción de fondo y la diferencia entre fotogramas.
- Las funciones principales (detect_object_presence, is_object_stable)
  simplemente devuelven el estado calculado por el hilo, lo que las hace
  extremadamente rápidas y eficientes.
- Genera dos flujos de video: uno "limpio" para ser enviado a Gemini y
  otro "anotado" con los contornos de detección para ser mostrado en la
  interfaz web como feedback visual.
"""
import cv2
import time
import threading
from datetime import datetime, timedelta

class Camera:
    """
    Clase que encapsula toda la lógica de la cámara y el procesamiento de video.
    """

    def __init__(self,
                 frame_delta_thresh=30,
                 min_contour_area=2000,
                 stability_pixel_threshold=1000,
                 stability_duration_sec=1.0):
        """
        Inicializa la cámara, los parámetros de detección y el hilo de procesamiento.

        Args:
            frame_delta_thresh (int): Umbral para la diferencia de píxeles en la
                                    detección de presencia (vs. fondo). Un valor
                                    más bajo es más sensible.
            min_contour_area (int): Área mínima en píxeles para que un contorno
                                  sea considerado un objeto válido.
            stability_pixel_threshold (int): Umbral de cambio de píxeles para
                                           considerar que un objeto se está
                                           moviendo. Más bajo = más sensible.
            stability_duration_sec (float): Tiempo en segundos que un objeto
                                          debe permanecer quieto para ser
                                          considerado estable.
        """
        # Intentar abrir la cámara. El índice 1 suele ser una cámara USB externa.
        # Si solo tienes una cámara, prueba con el índice 0.
        self.video = cv2.VideoCapture(1)
        if not self.video.isOpened():
            raise RuntimeError("No se pudo iniciar la cámara. ¿Está conectada y no está en uso?")

        # --- Parámetros de Detección ---
        self.frame_delta_thresh = frame_delta_thresh
        self.min_contour_area = min_contour_area
        self.stability_pixel_threshold = stability_pixel_threshold
        self.stability_duration = timedelta(seconds=stability_duration_sec)

        # --- Variables de Estado (gestionadas por el hilo) ---
        # Estas variables son actualizadas por el hilo de procesamiento y leídas
        # por el hilo principal de Flask de forma segura.
        self.latest_frame = None      # Guarda el último fotograma original (limpio)
        self.annotated_frame = None   # Guarda el último fotograma con dibujos (para streaming)
        self.object_present = False   # True si hay un objeto frente a la cámara
        self.object_stable = False    # True si el objeto está quieto por el tiempo requerido

        # --- Variables Internas del Hilo ---
        self.background = None        # Fotograma de referencia del fondo sin objetos
        self.prev_gray = None         # Fotograma anterior en escala de grises (para detectar movimiento)
        self.stable_since = None      # Timestamp de cuándo el objeto empezó a estar estable

        # --- Hilo de Procesamiento ---
        # Se crea y se inicia el hilo. Se marca como 'daemon' para que
        # se cierre automáticamente cuando el programa principal termine.
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

        print("Cámara iniciada. Capturando fondo inicial en 3 segundos...")
        time.sleep(3)
        self.update_background()

    def __del__(self):
        """Método destructor para asegurar que la cámara se libere al cerrar."""
        if self.video.isOpened():
            self.video.release()

    def _processing_loop(self):
        """
        Bucle principal del hilo de procesamiento. No debe ser llamado directamente.

        Este bucle se ejecuta continuamente en segundo plano y realiza todo el
        trabajo pesado de OpenCV.
        """
        while True:
            success, frame = self.video.read()
            if not success:
                time.sleep(0.1)
                continue

            # Guardar una copia del fotograma original antes de dibujar en él.
            # Este fotograma limpio es el que se enviará a Gemini.
            self.latest_frame = frame.copy()

            # Pre-procesamiento: convertir a escala de grises y aplicar desenfoque
            # para reducir el ruido y mejorar la detección.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # --- 1. Detección de Presencia (Objeto vs. Fondo) ---
            if self.background is not None:
                # Compara el frame actual con el fondo para ver si algo ha cambiado.
                frame_delta = cv2.absdiff(self.background, gray)
                thresh = cv2.threshold(frame_delta, self.frame_delta_thresh, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2) # Rellena huecos
                contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                found = False
                for c in contours:
                    if cv2.contourArea(c) > self.min_contour_area:
                        found = True
                        # Dibuja el contorno en el fotograma anotado (verde para presencia)
                        cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
                self.object_present = found

            # --- 2. Detección de Movimiento y Estabilidad (Frame Actual vs. Anterior) ---
            if self.prev_gray is not None:
                # Compara el frame actual con el anterior para detectar movimiento.
                frame_delta_mov = cv2.absdiff(self.prev_gray, gray)
                thresh_mov = cv2.threshold(frame_delta_mov, 15, 255, cv2.THRESH_BINARY)[1]

                # Dibuja los contornos del movimiento solo si ya hay un objeto presente.
                if self.object_present:
                    contours_mov, _ = cv2.findContours(thresh_mov.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for c in contours_mov:
                        if cv2.contourArea(c) > 50: # Umbral pequeño para cualquier movimiento
                             cv2.drawContours(frame, [c], -1, (0, 0, 255), 2) # Rojo para movimiento

                # Lógica de estabilidad temporal
                pixel_change = cv2.countNonZero(thresh_mov)
                if self.object_present and pixel_change < self.stability_pixel_threshold:
                    # Si el objeto está quieto, iniciar o continuar el contador de tiempo.
                    if self.stable_since is None:
                        self.stable_since = datetime.now()
                    
                    # Si ha estado quieto por suficiente tiempo, marcar como estable.
                    if datetime.now() - self.stable_since >= self.stability_duration:
                        self.object_stable = True
                else:
                    # Si hay movimiento o no hay objeto, reiniciar el contador.
                    self.stable_since = None
                    self.object_stable = False

            # Actualizar el fotograma anterior y el fotograma anotado para el siguiente ciclo
            self.prev_gray = gray
            self.annotated_frame = frame
            time.sleep(1/30) # Limitar a ~30 FPS para no usar 100% de CPU

    def update_background(self):
        """Captura y establece un nuevo fondo de referencia."""
        print("Actualizando fondo de referencia...")
        # Captura varios fotogramas para promediar y obtener un fondo más fiable.
        _, frame = self.video.read()
        if frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.background = cv2.GaussianBlur(gray, (21, 21), 0)
            self.prev_gray = self.background
            print("Fondo actualizado correctamente.")
            return True
        return False

    def get_frame_bytes(self):
        """Obtiene el fotograma ORIGINAL (limpio) codificado como JPEG en bytes."""
        if self.latest_frame is None:
            return None
        ret, jpeg = cv2.imencode('.jpg', self.latest_frame)
        return jpeg.tobytes() if ret else None

    def detect_object_presence(self):
        """Devuelve el estado de presencia de objeto calculado por el hilo."""
        return self.object_present

    def is_object_stable(self):
        """
        Devuelve si el objeto está estable, según el hilo de procesamiento.
        
        Importante: Este estado se auto-resetea a False después de ser leído
        una vez. Esto evita que el sistema clasifique el mismo objeto
        múltiples veces.
        """
        if self.object_stable:
            self.object_stable = False # Resetear para la próxima detección
            self.stable_since = None
            return True
        return False

    def stream_generator(self):
        """
        Generador de Python que produce el flujo de video para la web.
        
        Yields:
            bytes: Un fotograma del stream en formato multipart/x-mixed-replace.
        """
        while True:
            if self.annotated_frame is not None:
                ret, jpeg = cv2.imencode('.jpg', self.annotated_frame)
                if ret:
                    # El formato 'boundary=frame' es el estándar para streaming en navegadores
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(1/30) # Sincronizar con la tasa de FPS del hilo