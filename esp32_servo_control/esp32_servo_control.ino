/*
 * Control de Servo para Clasificador de Basura Inteligente
 *
 * Este sketch está diseñado para una placa ESP32 y funciona en conjunto
 * con el sistema principal de Python.
 *
 * Funcionalidad:
 * 1. Escucha comandos ("PLASTICO", "ORGANICO", "METAL") a través del puerto serial.
 * 2. Mueve un servo motor (MG90) a una posición angular predefinida para cada comando.
 * 3. Regresa el servo a una posición de reposo (home) después de un tiempo.
 * 4. Envía una confirmación ("OK\n") de vuelta a Python después de recibir un comando.
 *
 * Conexiones (Ejemplo):
 * - Servo MG90 Naranja (Señal) -> Pin 13 del ESP32
 * - Servo MG90 Rojo (VCC)      -> Pin 5V del ESP32
 * - Servo MG90 Marrón (GND)    -> Pin GND del ESP32
 *
 * Librerías Necesarias:
 * - ESP32Servo: Búscala e instálala desde el Gestor de Librerías del IDE de Arduino.
 */

#include <ESP32Servo.h>

// --- CONFIGURACIÓN ---
// Puedes ajustar estos valores según tu montaje físico.

// Pin GPIO donde está conectado el cable de señal del servo.
const int SERVO_PIN =27;

// Ángulos para cada posición del servo (0° a 180°).
const int POS_HOME     = 0;    // Posición de reposo o inicial.
const int POS_PLASTICO = 60;   // Posición para los plásticos.
const int POS_ORGANICO = 120;  // Posición para los orgánicos.
const int POS_METAL    = 180;  // Posición para los metales.

// Tiempo en milisegundos que el servo permanecerá en una posición
// antes de regresar a la posición de reposo (home).
const unsigned long RETURN_DELAY = 3000; // 3 segundos.

// --- VARIABLES GLOBALES ---
Servo servoMotor; // Objeto para controlar el servo.
String inputString = ""; // String para almacenar los datos que llegan del puerto serial.
bool stringComplete = false; // Bandera para saber si se ha recibido un comando completo.
unsigned long lastMoveTime = 0; // Para controlar el tiempo de regreso a home.
bool needsReturn = false; // Para saber si el servo debe regresar a home.


void setup() {
  // Iniciar la comunicación serial a la misma velocidad que el script de Python.
  Serial.begin(9600);
  inputString.reserve(20); // Reservar memoria para el string de entrada.

  // Configurar el servo motor.
  servoMotor.attach(SERVO_PIN);

  // Mover el servo a su posición inicial al arrancar.
  Serial.println("Sistema de servo iniciado. Moviendo a la posición HOME.");
  servoMotor.write(POS_HOME);
  delay(500); // Pequeña pausa.
}


void loop() {
  // Tarea 1: Procesar comandos seriales si hay alguno completo.
  if (stringComplete) {
    inputString.trim(); // Limpiar espacios en blanco o caracteres invisibles.
    //Serial.print("Comando recibido: ");
    //Serial.println(inputString);

    

    // Mover el servo según el comando recibido.
    if (inputString == "PLASTICO") {
      servoMotor.write(POS_PLASTICO);
    } else if (inputString == "ORGANICO") {
      servoMotor.write(POS_ORGANICO);
    } else if (inputString == "METAL") {
      servoMotor.write(POS_METAL);
    }
    // Responder "OK" inmediatamente para que Python no espere.
    Serial.println("OK");

    // Preparar el regreso a la posición HOME.
    lastMoveTime = millis();
    needsReturn = true;

    // Limpiar el string para el siguiente comando.
    inputString = "";
    stringComplete = false;
  }

  // Tarea 2: Regresar el servo a la posición HOME si ha pasado el tiempo.
  if (needsReturn && (millis() - lastMoveTime > RETURN_DELAY)) {
    Serial.println("Regresando a la posición HOME.");
    servoMotor.write(POS_HOME);
    needsReturn = false; // Desactivar hasta el próximo comando.
  }
}


/*
 * Evento de Interrupción Serial
 *
 * Esta función se ejecuta automáticamente cada vez que llega un dato
 * al buffer del puerto serial. Es más eficiente que leer en el loop.
 */
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      // Si se recibe un salto de línea, el comando está completo.
      stringComplete = true;
    } else {
      // Si no, se añade el carácter al string.
      inputString += inChar;
    }
  }
}
