import xml.etree.ElementTree as ET

from network.network import NetworkManager

class NetworkManager_XML(NetworkManager):

    def __init__(self):
        super().__init__()

    def send_XML(self, data):
        if self.connected:
            try:
                message = data
                self.client_tcp.send(message.encode("utf-8"))
                print(f"Mensaje de salida TCP: {message}")
            except Exception as e:
                print(f"Error in: {e}")

    def receive_XML(self):

        if self.pending_messages:
            return self.pending_messages.pop(0)

        if self.connected:
            try:
                data = self.client_tcp.recv(4096).decode("utf-8")
                print(f"Mensaje de entrada TCP: {data}")
                if data:
                    self.receive_buffer += data
                    if "\n" in self.receive_buffer:
                        partes = self.receive_buffer.split("\n")
                        self.receive_buffer = partes.pop()

                        # Ahora 'partes' solo tiene paquetes JSON completos y perfectos
                        for XML_packet in partes:
                            if XML_packet.strip():  # Ignorar líneas en blanco
                                try:
                                    root = ET.fromstring(XML_packet)
                                    msg_type = root.find("Type").text

                                    if msg_type == "CONNECTION_ACK":
                                        status = root.find("Status").text
                                        if status == "rejected":
                                            reason = root.find("Reason").text
                                            parsed_message = {"type": msg_type, "status": status, "reason": reason}
                                        else:
                                            parsed_message = {"type": msg_type, "status": status}

                                    elif msg_type == "QUEUE_STATUS":
                                        payload_node = root.find("Payload")
                                        if payload_node is None:
                                            raise ValueError("Missing <Payload> node in QUEUE_STATUS")

                                        players_waiting_str = payload_node.find("PlayersWaiting").text
                                        players_waiting = int(players_waiting_str) 

                                        you = payload_node.find("You").text

                                        parsed_message = {
                                            "type": msg_type,
                                            "payload": {
                                                "players_waiting": players_waiting,
                                                "you": you,
                                            },
                                        }
                           
                                    elif msg_type == "MATCH_FOUND":
                                        payload_node = root.find("Payload")
                                        if payload_node is None:
                                            raise ValueError("Missing <Payload> node in MATCH_FOUND")

                                        session_id_string = payload_node.find("SessionId").text
                                        you = payload_node.find("You").text
                                        opponent = payload_node.find("Opponent").text

                                        parsed_message = {
                                            "type": msg_type,
                                            "payload": {
                                                "session_id": session_id_string,
                                                "you": you,
                                                "opponent": opponent,
                                            },
                                        }

                                    elif msg_type == "START_GAME":
                                        payload_node = root.find("Payload")
                                        if payload_node is None:
                                            raise ValueError("Missing <Payload> node in START_GAME")

                                        session_id_string = payload_node.find("SessionID").text

                                        start_str = payload_node.find("Start").text
                                        start_bool = start_str.lower() == "true" # Casteo a bool

                                        structures_dict = {}
                                        structures_node = payload_node.find("Structures")

                                        if structures_node is not None:
                                            for entry in structures_node.findall("Entry"):
                                                struct_key = entry.get("key") 

                                                x = int(entry.find("X").text)
                                                y = int(entry.find("Y").text)

                                                structures_dict[struct_key] = (x,y)

                                        units_dict = {}
                                        units_node = payload_node.find("Units")

                                        if units_node is not None:
                                            for entry in units_node.findall("Entry"):
                                                unit_id = int(entry.get("key"))

                                                x = int(entry.find("X").text)
                                                y = int(entry.find("Y").text)

                                                units_dict[unit_id] = (x, y)

                                            parsed_message = {
                                                "type": msg_type,
                                                "payload": {
                                                    "session_id": session_id_string,
                                                    "start": start_bool,
                                                    "structures": structures_dict,
                                                    "units": units_dict,
                                                },
                                            }

                                    if parsed_message:
                                        self.pending_messages.append(parsed_message)

                                except ET.ParseError as e:
                                    print(f"XML Parsing Error: {e}")
                                    return {}
                                except (AttributeError, ValueError) as e:
                                    print(f"[Data Error] Missing or invalid XML nodes: {e}")
                                    return {}
            except BlockingIOError:
                pass
            except Exception as e:
                print(f"Error to receive: {e}")
                self.connected = False

        if self.pending_messages:
            return self.pending_messages.pop(0)

        return None
