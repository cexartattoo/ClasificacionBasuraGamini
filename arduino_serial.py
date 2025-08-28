import serial
import time

# --- CONFIGURACIÓN ---
# IMPORTANTE: Cambia 'COM3' al puerto serial correcto de tu Arduino.
# En Linux/Mac, podría ser algo como '/dev/ttyUSB0' o '/dev/tty.usbmodem1411'.
# Puedes encontrar el puerto en el IDE de Arduino > Herramientas > Puerto.
ARDUINO_PORT = 'COM3'
BAUD_RATE = 9600
TIMEOUT = 2  # Tiempo máximo de espera para la respuesta del Arduino en segundos

# Variable global para mantener la conexión
ser = None


def init_serial():
    """
    Inicializa la conexión serial con el Arduino.
    """
    global ser
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=TIMEOUT)
        time.sleep(2)  # Esperar a que la conexión se establezca
        print(f"Conexión serial establecida en el puerto {ARDUINO_PORT}.")
        return True
    except serial.SerialException as e:
        print(f"Error: No se pudo conectar al Arduino en el puerto {ARDUINO_PORT}.")
        print(f"Detalle del error: {e}")
        ser = None
        return False


def send_command(command):
    """
    Envía un comando al Arduino y espera una confirmación "OK".

    Args:
        command (str): El comando a enviar (ej. "PLASTICO").

    Returns:
        bool: True si el comando se envió y se recibió "OK", False en caso contrario.
    """
    global ser
    if ser is None or not ser.is_open:
        print("Error: La conexión serial no está disponible.")
        # Intenta reconectar
        if not init_serial():
            return False

    try:
        # Limpiar el buffer de entrada para descartar datos viejos
        ser.reset_input_buffer()

        # Añadir un salto de línea, que es un delimitador común para Arduino
        full_command = (command.upper() + '\n').encode('utf-8')

        print(f"Enviando comando a Arduino: {full_command.decode().strip()}")
        ser.write(full_command)

        # Esperar la respuesta del Arduino
        response = ser.readline().decode('utf-8').strip()

        print(f"Respuesta de Arduino: '{response}'")

        if response == "OK":
            print("Confirmación 'OK' recibida del Arduino.")
            return True
        else:
            print("Error: No se recibió la confirmación 'OK' del Arduino.")
            return False

    except serial.SerialException as e:
        print(f"Error durante la comunicación serial: {e}")
        # Cierra la conexión si hay un error para intentar reconectar la próxima vez
        close_serial()
        return False
    except Exception as e:
        print(f"Un error inesperado ocurrió: {e}")
        return False


def close_serial():
    """
    Cierra la conexión serial si está abierta.
    """
    global ser
    if ser and ser.is_open:
        ser.close()
        print("Conexión serial cerrada.")
        ser = None


# Ejemplo de uso (para pruebas)
if __name__ == '__main__':
    if init_serial():
        # Prueba enviando los tres comandos posibles
        send_command("PLASTICO")
        time.sleep(1)
        send_command("ORGANICO")
        time.sleep(1)
        send_command("METAL")

        close_serial()

