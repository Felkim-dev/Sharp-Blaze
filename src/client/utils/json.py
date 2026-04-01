class JSON_Manager:
    def get_datajoin(nickname):

        datajoin = {
            "type": "INITIAL_CONNECT",
            "payload": {
                "player_id": nickname,
                "client_version": "0.0.1",
                "is_ready": True,
            },
        }
        
        return datajoin
