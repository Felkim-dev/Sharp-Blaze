import socket
import json
import threading

class NetworkManager:
    """Class that manages all the connections"""

    def __init__(self):
        """INITIAL STATES"""
        self.client = None
        self.connected = False
        self.connection_status = "IDLE"

        self.receive_buffer = ""
        self.pending_messages = []

    def connect(self, ip, datos_iniciales, port=5555):

        if self.connection_status == "CONNECTING":
            return
        self.connection_status = "CONNECTING"

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
            self.connection_status = "IDLE"

        except socket.timeout:
            print("Timeout.")
            self.connected = False
            self.connection_status = "ERROR"
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            self.connection_status = "ERROR"

    def send_json(self, data_dictionary):
        if self.connected:
            try:
                message = json.dumps(data_dictionary)
                print(message)
                self.client.send(message.encode("utf-8"))
            except Exception as e:
                print(f"Error in: {e}")

    def receive_json(self):

        if self.pending_messages:
            return self.pending_messages.pop(0)

        if self.connected:
            try:
                data = self.client.recv(4096).decode("utf-8")
                print(data)
                if data:
                    self.receive_buffer += data
                    if "\n" in self.receive_buffer:
                        partes = self.receive_buffer.split("\n")
                        self.receive_buffer = partes.pop()

                        # Ahora 'partes' solo tiene paquetes JSON completos y perfectos
                        for json_packet in partes:
                            if json_packet.strip():  # Ignorar líneas en blanco
                                try:
                                    # Convertimos a diccionario y lo formamos en la fila
                                    json_valido = json.loads(json_packet)
                                    self.pending_messages.append(json_valido)
                                except json.JSONDecodeError as e:
                                    print(
                                        f"Error encountered while reading JSON: {json_packet} -> {e}"
                                    )

                        # Si logramos procesar algo, devolvemos el primer mensaje de la fila
                        if self.pending_messages:
                            return self.pending_messages.pop(0)
            except BlockingIOError:
                pass
            except Exception as e:
                print(f"Error to receive: {e}")
                self.connected = False

        return None

    def disconnect(self):
        if self.client is not None:

            # SERVER DOES NOT RECEIVE this message
            # try:
            #     if self.connected:
            #         message = json.dumps({"type": "LEAVE"}) + "\n"
            #         self.client.send(message.encode("utf-8"))
            # except Exception as e:
            #     print(f"The farewell message could not be sent: {e}")

            # finally:
            try:
                self.client.close()
            except Exception as e:
                print(f"Error forcing the socket to close: {e}")

            # RESTARTING VARIBLES TO THE INITIAL STATE
            self.client = None
            self.connected = False
            self.connection_status = "IDLE"

            # CLEAN BUFFER
            self.receive_buffer = ""
            self.pending_messages = []
            print("Disconnection complete and network restarted.")
