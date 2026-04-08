import xml.etree.ElementTree as ET

from network.network import NetworkManager

class NetworkManager_XML(NetworkManager):

    def __init__(self):
        super().__init__()

    def receive_XML(xml_string:str):
        try:
            root = ET.fromstring(xml_string)
            msg_type = root.find("Type").text

            if msg_type == "CONNECTION_ACK":
                status = root.find("Status").text
                if status == "rejected":
                    reason = root.find("Reason").text
                    return {"type": msg_type, "status": status, "reason": reason}
                return {"type": msg_type, "status": status}

            elif msg_type == "CONNECTION_ACK":
                status = root.find("Status").text
                return {"type": msg_type, "status": status}

            elif msg_type == "QUEUE_STATUS":
                payload_node = root.find("Payload").text
                if payload_node is None:
                    raise ValueError("Missing <Payload> node in QUEUE_STATUS")

                players_waiting_str = payload_node.find("PlayersWaiting").text
                players_waiting = int(players_waiting_str) 

                you = payload_node.find("You").text

                return {
                    "type": msg_type,
                    "payload": {
                        "players_waiting": players_waiting,
                        "you": you
                    }
                }

            elif msg_type == "MATCH_FOUND":
                payload_node = root.find("Payload").text
                if payload_node is None:
                    raise ValueError("Missing <Payload> node in MATCH_FOUND")

                session_id_string = payload_node.find("SessionID").text
                you = payload_node.find("You").text
                opponent = payload_node.find("Opponent").text

                return {
                    "type": msg_type,
                    "payload": {
                        "session_id": session_id_string,
                        "you": you,
                        "opponnet": opponent
                    }
                }

            elif msg_type == "START_GAME":
                payload_node = root.find("Payload").text
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
                    
                return {
                    "type": msg_type,
                    "payload": {
                        "session_id": session_id_string,
                        "start": start_bool,
                        "structures": structures_dict,
                        "units": {},
                    }
                }

        except ET.ParseError as e:
            print(f"XML Parsing Error: {e}")
            return {}
        except (AttributeError, ValueError) as e:
            print(f"[Data Error] Missing or invalid XML nodes: {e}")
            return {}
