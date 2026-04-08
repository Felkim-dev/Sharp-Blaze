import xml.etree.ElementTree as ET

def create_initial_connect_xml(nickname: str, client_version: str, is_ready: bool) -> str:
    
    root = ET.Element("Message")
    ET.SubElement(root, "Type").text = "INITIAL_CONNECT"

    payload = ET.SubElement(root, "Payload")
    ET.SubElement(payload, "PlayerId").text = nickname
    ET.SubElement(payload, "ClientVersion").text = client_version
    # Convertir booleano a string en minúscula para estándar XML
    ET.SubElement(payload, "IsReady").text = str(is_ready).lower()

    # Generar string en una sola línea y añadir el delimitador \n
    xml_string = ET.tostring(root, encoding="unicode", method="xml")
    return xml_string + "\n"

def create_start_game_xml(start: bool) -> str:

    root = ET.Element("Message")
    ET.SubElement(root, "Type").text = "START_GAME"

    payload = ET.SubElement(root, "Payload")
    ET.SubElement(payload, "Start").text = str(start).lower()

    # Generar string en una sola línea y añadir el delimitador \n
    xml_string = ET.tostring(root, encoding="unicode", method="xml")
    return xml_string + "\n"
