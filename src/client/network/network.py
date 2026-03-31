import socket
import json
import threading

class NetworkManager:
    """Class that manages all the connections"""

    def __init__(self):
        """INITIAL STATES"""
        # -------------------- TCP INTIAL STATES -------------------
        self.client_tcp = None
        self.connected = False
        self.connection_status = "IDLE"
        self.receive_buffer = ""
        self.pending_messages = []

        # ------------------- UDP INITIAL STATES -------------------
        self.client_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_udp.setblocking(False)
        self.udp_port_server = None
        self.server_ip = None

#--------------------------- UDP Methods -------------------------------------
    def init_udp_connection(self, ip, port):
        """It is called when the Lobby Start button is clicked"""
        self.server_ip = ip
        self.udp_port_server = port
        
        welcome_message = b"HELLO_UDP"
        
        try:
            self.client_udp.sendto(welcome_message,(self.server_ip,self.udp_port_server))
            print("UDP Channel open. Waiting for positions")
        except Exception as e:
            print(f"Error at moment of UDP channel openning: {e}")

    def receive_udp(self):
        """Read the last postions packet from the server"""
        try:
            raw_data, origin_directions = self.client_udp.recvfrom(1024)
            
            return raw_data
        
        except BlockingIOError:
            return None
        except Exception as e:
            return None

#------------------------------- TCP methods ------------------------------------------------------
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
        self.client_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.client_tcp.settimeout(3.0)
        try:
            self.client_tcp.connect((ip, port))

            mensaje = json.dumps(datos_iniciales) + "\n"
            self.client_tcp.send(mensaje.encode("utf-8"))

            self.client_tcp.settimeout(None)
            self.client_tcp.setblocking(False)

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
                self.client_tcp.send(message.encode("utf-8"))
            except Exception as e:
                print(f"Error in: {e}")

    def receive_json(self):

        if self.pending_messages:
            return self.pending_messages.pop(0)

        if self.connected:
            try:
                data = self.client_tcp.recv(4096).decode("utf-8")
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
        if self.client_tcp is not None:

            # SERVER DOES NOT RECEIVE this message
            # try:
            #     if self.connected:
            #         message = json.dumps({"type": "LEAVE"}) + "\n"
            #         self.client.send(message.encode("utf-8"))
            # except Exception as e:
            #     print(f"The farewell message could not be sent: {e}")

            # finally:
            try:
                self.client_tcp.close()
            except Exception as e:
                print(f"Error forcing the socket to close: {e}")

            # RESTARTING VARIBLES TO THE INITIAL STATE
            self.client_tcp = None
            self.connected = False
            self.connection_status = "IDLE"

            # CLEAN BUFFER
            self.receive_buffer = ""
            self.pending_messages = []
            print("Disconnection complete and network restarted.")
