import cv2


class Camera:
    """
    Clase para manejar la captura de video desde la cámara web.
    """

    def __init__(self):
        # Inicia la captura de video. El argumento 0 indica la cámara por defecto.
        # Si tienes varias cámaras, puedes probar con 1, 2, etc.
        self.video = cv2.VideoCapture(0)
        if not self.video.isOpened():
            raise RuntimeError("No se pudo iniciar la cámara. ¿Está conectada y no está en uso por otro programa?")
        print("Cámara iniciada correctamente.")

    def __del__(self):
        # Libera el recurso de la cámara cuando el objeto es destruido.
        if self.video.isOpened():
            self.video.release()
        print("Cámara liberada.")

    def get_frame(self):
        """
        Captura un solo fotograma de la cámara.

        Returns:
            bytes: El fotograma codificado como JPEG, o None si falla la captura.
        """
        success, frame = self.video.read()
        if not success:
            print("Error: No se pudo capturar un fotograma de la cámara.")
            return None

        # Codificar el fotograma en formato JPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            print("Error: No se pudo codificar el fotograma a JPEG.")
            return None

        return jpeg.tobytes()

    def stream_generator(self):
        """
        Generador que produce continuamente fotogramas para el streaming de video.
        """
        while True:
            frame_bytes = self.get_frame()
            if frame_bytes is None:
                # Si falla la captura, se puede detener o intentar de nuevo.
                # Aquí continuamos para no interrumpir el stream por un fotograma fallido.
                continue

            # Formatear la salida para un stream de respuesta HTTP multipart
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

