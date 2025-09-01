import cv2
import time
import threading
from datetime import datetime, timedelta

class Camera:
    """
    Clase para manejar la cámara, con detección de presencia de objetos,
    análisis de estabilidad y un hilo de procesamiento dedicado.
    """

    def __init__(self,
                 frame_delta_thresh=30,
                 min_contour_area=2000,
                 stability_pixel_threshold=1000,
                 stability_duration_sec=1.0):
        """
        Inicializa la cámara y los parámetros de detección.

        Args:
            frame_delta_thresh (int): Umbral para la diferencia de píxeles en la detección de presencia.
            min_contour_area (int): Área mínima para que un cambio sea considerado un objeto.
            stability_pixel_threshold (int): Umbral de píxeles para considerar que un objeto se está moviendo.
            stability_duration_sec (float): Segundos que un objeto debe estar quieto para ser estable.
        """
        self.video = cv2.VideoCapture(1)
        if not self.video.isOpened():
            raise RuntimeError("No se pudo iniciar la cámara.")

        # Parámetros de sensibilidad
        self.frame_delta_thresh = frame_delta_thresh
        self.min_contour_area = min_contour_area
        self.stability_pixel_threshold = stability_pixel_threshold
        self.stability_duration = timedelta(seconds=stability_duration_sec)

        # Variables de estado (manejadas por el hilo de procesamiento)
        self.latest_frame = None
        self.annotated_frame = None
        self.object_present = False
        self.object_stable = False

        # Variables internas del hilo
        self.background = None
        self.prev_gray = None
        self.stable_since = None
        self.last_presence_check = datetime.now()

        # Iniciar el hilo de procesamiento
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()

        print("Cámara iniciada. Esperando 3 segundos para capturar el fondo inicial...")
        time.sleep(3)
        self.update_background()

    def __del__(self):
        if self.video.isOpened():
            self.video.release()

    def _processing_loop(self):
        """
        Hilo principal que procesa continuamente los fotogramas de la cámara.
        """
        while True:
            success, frame = self.video.read()
            if not success:
                time.sleep(0.1)
                continue

            # Guardar el fotograma original para enviarlo a Gemini
            self.latest_frame = frame.copy()

            # Pre-procesamiento
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # --- Detección de Presencia (Contornos Verdes) ---
            if self.background is not None:
                frame_delta_presence = cv2.absdiff(self.background, gray)
                thresh_presence = cv2.threshold(frame_delta_presence, self.frame_delta_thresh, 255, cv2.THRESH_BINARY)[1]
                thresh_presence = cv2.dilate(thresh_presence, None, iterations=2)
                contours_presence, _ = cv2.findContours(thresh_presence.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                found_object = False
                for c in contours_presence:
                    if cv2.contourArea(c) > self.min_contour_area:
                        found_object = True
                        cv2.drawContours(frame, [c], -1, (0, 255, 0), 2) # Verde
                self.object_present = found_object

            # --- Detección de Movimiento y Estabilidad (Contornos Rojos) ---
            if self.prev_gray is not None:
                frame_delta_movement = cv2.absdiff(self.prev_gray, gray)
                thresh_movement = cv2.threshold(frame_delta_movement, self.frame_delta_thresh, 255, cv2.THRESH_BINARY)[1]
                
                # Dibujar contornos de movimiento si hay un objeto presente
                if self.object_present:
                    contours_movement, _ = cv2.findContours(thresh_movement.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for c in contours_movement:
                        if cv2.contourArea(c) > 50: # Umbral pequeño para movimiento
                             cv2.drawContours(frame, [c], -1, (0, 0, 255), 2) # Rojo

                # Lógica de estabilidad
                pixel_change_count = cv2.countNonZero(thresh_movement)
                if self.object_present and pixel_change_count < self.stability_pixel_threshold:
                    if self.stable_since is None:
                        self.stable_since = datetime.now()
                    
                    if datetime.now() - self.stable_since >= self.stability_duration:
                        self.object_stable = True
                else:
                    # Si hay movimiento o no hay objeto, se resetea la estabilidad
                    self.stable_since = None
                    self.object_stable = False

            self.prev_gray = gray
            self.annotated_frame = frame
            time.sleep(1/30) # Limitar a ~30 FPS

    def update_background(self):
        """Captura el fotograma actual y lo establece como el nuevo fondo de referencia."""
        print("Actualizando fondo de referencia...")
        # Capturamos un par de fotogramas para asegurar que el fondo es estable
        for _ in range(5):
            success, frame = self.video.read()
            if success:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                self.background = cv2.GaussianBlur(gray, (21, 21), 0)
            time.sleep(0.1)
        self.prev_gray = self.background
        print("Fondo actualizado.")
        return True

    def get_frame_bytes(self):
        """Obtiene el fotograma ORIGINAL (sin anotaciones) codificado como JPEG."""
        if self.latest_frame is None:
            return None
        ret, jpeg = cv2.imencode('.jpg', self.latest_frame)
        return jpeg.tobytes() if ret else None

    def detect_object_presence(self):
        """FASE 1: Devuelve si el hilo de procesamiento ha detectado un objeto."""
        return self.object_present

    def is_object_stable(self):
        """FASE 2: Devuelve si el hilo de procesamiento considera el objeto estable."""
        if self.object_stable:
            # Resetear después de confirmar para evitar reclasificaciones múltiples
            self.object_stable = False
            self.stable_since = None
            return True
        return False

    def stream_generator(self):
        """Generador para el streaming de video con anotaciones."""
        while True:
            if self.annotated_frame is not None:
                ret, jpeg = cv2.imencode('.jpg', self.annotated_frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(1/30) # Coincidir con la tasa del hilo de procesamiento
