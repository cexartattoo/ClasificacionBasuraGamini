# -*- coding: utf-8 -*-
"""
Module de Communication Sérial avec Arduino (arduino_serial.py)

Ce module s'occupe de la communication de bas niveau entre le script
de Python et le microcontrôleur Arduino.

Fonctionnalités:
- Établir une connexion sérielle sur un port et une vitesse spécifiques.
- Envoyer des commandes texte (ex. "PLASTICO") à l'Arduino.
- Attendre et valider une réponse de confirmation ("OK") de l'Arduino.
- Fermer la connexion en toute sécurité.
- Essayer de reconnecter si la connexion est perdue.
"""
import serial
import time

# --- Configuration de la Connexion Sérielle ---
# IMPORTANT: Changez 'COM3' au port sériel correct où votre Arduino est connecté.
# - Sous Windows, c'est généralement 'COMx' (ex. 'COM3', 'COM4').
# - Sous Linux, c'est généralement '/dev/ttyUSBx' ou '/dev/ttyACMx'.
# - Sous macOS, c'est généralement '/dev/tty.usbmodemxxxx'.
# Vous pouvez trouver le port correct dans l'IDE Arduino > Outils > Port.
ARDUINO_PORT = 'COM4'
BAUD_RATE = 9600
# Temps maximum en secondes que le script attendra une réponse de l'Arduino.
SERIAL_TIMEOUT = 2

# Variable globale pour conserver l'objet de la connexion sérielle.
# Utilisée globalement pour que la connexion persiste entre les appels de fonction.
ser = None


def init_serial():
    """
    Initialise et ouvre la connexion sérielle avec l'Arduino.

    Tente de se connecter au port configuré. Si ça échoue, affiche une erreur
    détaillée.

    Returns:
        bool: True si la connexion a réussi, False sinon.
    """
    global ser
    # Si une connexion existe déjà, ne rien faire.
    if ser and ser.is_open:
        return True
    try:
        print(f"Tentative de connexion avec l'Arduino sur le port {ARDUINO_PORT}...")
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        # On attend quelques secondes pour que la connexion sérielle se stabilise.
        # C'est une pratique courante lors du travail avec Arduino.
        time.sleep(2)
        print(f"Connexion sérielle avec l'Arduino établie correctement.")
        return True
    except serial.SerialException as e:
        print(f"--- ERREUR DE CONNEXION SÉRIELLE ---")
        print(f"Impossible de se connecter à l'Arduino sur le port '{ARDUINO_PORT}'.")
        print("Veuillez vérifier les points suivants:")
        print("1. L'Arduino est-il connecté à l'ordinateur ?")
        print("2. Le port dans ce script est-il le bon ? (Voir l'IDE Arduino)")
        print("3. Aucun autre programme (comme le Moniteur Sériel de l'IDE) n'utilise le port ?")
        print(f"Détail de l'erreur: {e}")
        ser = None
        return False

def send_command(command):
    """
    Envoie une commande texte à l'Arduino et attend une confirmation.

    Le protocole de communication est simple:
    1. Python envoie une commande en majuscules suivie d'un saut de ligne (ex. "PLASTICO\n").
    2. Arduino traite la commande (ex. déplace un servo).
    3. Arduino répond avec "OK\n" pour confirmer qu'il a reçu et traité la commande.

    Args:
        command (str): La commande à envoyer (ex. "PLASTICO", "ORGANICO", "METAL").

    Returns:
        bool: True si la commande a été envoyée et la confirmation "OK" a été reçue.
              False en cas d'erreur ou si la confirmation n'a pas été reçue.
    """
    global ser
    # Si la connexion n'est pas active, tenter de l'initialiser à nouveau.
    if ser is None or not ser.is_open:
        print("Avertissement: La connexion sérielle n'était pas disponible. Tentative de reconnexion...")
        if not init_serial():
            print("Erreur: Impossible de se reconnecter à l'Arduino. Commande non envoyée.")
            return False

    try:
        # Nettoyer toute donnée résiduelle dans le buffer d'entrée avant d'envoyer.
        ser.reset_input_buffer()

        # Formater la commande: convertir en majuscules et ajouter un saut de ligne.
        # Le '.encode('utf-8')' est nécessaire pour convertir la chaène Python en octets.
        full_command = (command.upper() + '\n').encode('utf-8')

        print(f"Envoi de la commande à l'Arduino: {full_command.decode().strip()}")
        ser.write(full_command)

        # Attendre la réponse de l'Arduino. readline() lira jusqu'à trouver un '\n'.
        response = ser.readline().decode('utf-8').strip()

        print(f"Réponse reçue de l'Arduino: '{response}'")

        # Vérifier si la réponse est celle attendue.
        if response == "OK":
            print("Confirmation 'OK' reçue. La commande a réussi.")
            return True
        else:
            print(f"Erreur: Une réponse inattendue a été reçue de l'Arduino: '{response}'. 'OK' était attendu.")
            return False

    except serial.SerialException as e:
        print(f"Erreur critique lors de la communication sérielle: {e}")
        # En cas d'erreur grave, fermer la connexion pour forcer une réinitialisation complète la prochaine fois.
        close_serial()
        return False
    except Exception as e:
        print(f"Une erreur inattendue s'est produite lors de l'envoi de la commande: {e}")
        return False

def close_serial():
    """
    Ferme la connexion sérielle si elle est ouverte.

    Il est important d'appeler cette fonction à la fin du programme pour libérer le port sériel.
    """
    global ser
    if ser and ser.is_open:
        ser.close()
        print("Connexion sérielle fermée en toute sécurité.")
        ser = None


# --- Bloc d'Exécution pour Tests ---
# Si vous exécutez ce fichier directement (python arduino_serial.py),
# il tentera de se connecter et d'envoyer les trois commandes de test.
if __name__ == '__main__':
    print("--- Exécution du test du module de communication avec Arduino ---")
    if init_serial():
        print("\nTest de la commande 'PLASTICO'...")
        send_command("PLASTICO")
        time.sleep(2) # Pause entre les commandes

        print("\nTest de la commande 'ORGANICO'...")
        send_command("ORGANICO")
        time.sleep(2)

        print("\nTest de la commande 'METAL'...")
        send_command("METAL")

        close_serial()
    else:
        print("\nImpossible de démarrer la communication. Le test a échoué.")