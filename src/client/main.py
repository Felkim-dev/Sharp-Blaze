# main.py
import pygame
import sys
import socket
import json
import threading

# IMPORT OF SCREENS
from ui.main_screen import MainScreen
from ui.host_screen import HostScreen
from ui.join_screen import JoinScreen
from ui.lobby_screen import LobbyScreen
from ui.conecting_screen import ConnectingScreen


class GAME:

    def __init__(self):

        WIDTH = 1280
        HEIGHT = 720

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sharp Blaze")
        self.clock = pygame.time.Clock()

        self.network = NetworkManager()

        self.screens = {
            "MAIN": MainScreen(self, self.screen),
            "HOST": HostScreen(self, self.screen),
            "JOIN": JoinScreen(self, self.screen),
            "LOBBY": LobbyScreen(self, self.screen),
            "CONNECTING": ConnectingScreen(self, self.screen)
        }

        self.current_screen = self.screens["MAIN"]

    def change_screen(self, screen_name):
        if screen_name in self.screens:
            self.current_screen = self.screens[screen_name]
        else:
            # Borrar
            print("ERROR: Screen Does not Exists")

    def run(self):
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.network.desconectar()
                    pygame.quit()
                    sys.exit()

            keys = pygame.key.get_pressed()

            self.current_screen.handle_events(events, keys)
            self.current_screen.draw()
            self.current_screen.update()

            pygame.display.flip()
            self.clock.tick(60)

class NetworkManager:
    def __init__(self):
        self.client = None
        self.connected = False
        self.estado_conexion = "IDLE"

        self.buffer_recepcion = ""
        self.mensajes_pendientes = []

    def connect(self, ip, datos_iniciales, port=5555):

        if self.estado_conexion == "CONECTANDO":
            return
        self.estado_conexion = "CONECTANDO"

        thread = threading.Thread(
            target=self.connection_thread, args=(ip, port, datos_iniciales)
        )
        thread.daemon = True
        thread.start()

    def connection_thread(self, ip, port, datos_iniciales):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.client.settimeout(3.0)
        try:
            self.client.connect((ip, port))

            mensaje = json.dumps(datos_iniciales) + "\n"
            self.client.send(mensaje.encode("utf-8"))

            self.client.settimeout(None)
            self.client.setblocking(False)

            self.connected = True
            self.estado_conexion = "IDLE"

        except socket.timeout:
            print("Tiempo de espera agotado.")
            self.connected = False
            self.estado_conexion = "ERROR"
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            self.estado_conexion = "ERROR"

    def send_json(self, data_dictionary):
        if self.connected:
            try:
                message = json.dumps(data_dictionary)
                print(message)
                self.client.send(message.encode("utf-8"))
            except Exception as e:
                print(f"Error in: {e}")

    def receive_json(self):

        if self.mensajes_pendientes:
            return self.mensajes_pendientes.pop(0)

        if self.connected:
            try:
                data = self.client.recv(4096).decode("utf-8")
                print(data)
                if data:
                    self.buffer_recepcion += data
                    if '\n' in self.buffer_recepcion:
                        partes = self.buffer_recepcion.split("\n")
                        self.buffer_recepcion = partes.pop()

                        # Ahora 'partes' solo tiene paquetes JSON completos y perfectos
                        for paquete_texto in partes:
                            if paquete_texto.strip():  # Ignorar líneas en blanco
                                try:
                                    # Convertimos a diccionario y lo formamos en la fila
                                    json_valido = json.loads(paquete_texto)
                                    self.mensajes_pendientes.append(json_valido)
                                except json.JSONDecodeError as e:
                                    print(
                                        f"Error descartado al leer JSON: {paquete_texto} -> {e}"
                                    )

                        # Si logramos procesar algo, devolvemos el primer mensaje de la fila
                        if self.mensajes_pendientes:
                            return self.mensajes_pendientes.pop(0)
            except BlockingIOError:
                pass
            except Exception as e:
                print(f"Error to receive: {e}")
                self.connected = False

        return None

    def desconectar(self):
        # 1. Verificamos que el socket realmente exista
        if self.client is not None:
            try:
                # Intentamos ser educados y avisar que nos vamos
                if self.connected:
                    mensaje = json.dumps({"accion": "LEAVE"}) + "\n"
                    self.client.send(mensaje.encode("utf-8"))
            except Exception as e:
                # Si falla el envío, no importa, igual vamos a cerrar
                print(f"No se pudo enviar el mensaje de despedida: {e}")

            finally:
                # AQUÍ ESTÁ LA MAGIA: Esto se ejecuta SÍ O SÍ, falle o no el envío
                try:
                    self.client.close()
                except Exception as e:
                    print(f"Error forzando el cierre del socket: {e}")

                # Reseteamos todas las variables de la red para que quede como nueva
                self.client = None
                self.connected = False
                self.estado_conexion = "IDLE"

                # ¡Súper importante! Limpiamos el balde de mensajes viejos
                self.buffer_recepcion = ""
                self.mensajes_pendientes = []
                print("Desconexión completada y red reiniciada.")


if __name__ == "__main__":
    game = GAME()
    game.run()
