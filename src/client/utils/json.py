class JSON_Manager:
    def get_queue_request(nickname):

        return {
            "action": "queue",
            "player_id": nickname,
        }

    def get_initial_connect(player_id, session_id=None, match_token=None):

        payload = {
            "player_id": player_id,
            "client_version": "0.0.1",
            "is_ready": True,
        }

        if session_id is not None:
            payload["session_id"] = session_id

        if match_token is not None:
            payload["match_token"] = match_token

        return {
            "type": "INITIAL_CONNECT",
            "payload": payload,
        }

    def get_datajoin(nickname):

        return JSON_Manager.get_queue_request(nickname)

    def get_startgame(session_id=None): 

        start = {
            "type": "START_GAME",
            "payload":{
                "start" : False,
            },
        }
        
        if session_id is not None:
            start["payload"]["session_id"] = session_id

        return start

    def get_moveorder(id,x,y):

        command_payload = {
            "type": "MOVE_ORDER",
            "payload": {
                "unit_id": id,
                "target_x": x,
                "target_y": y,
            },
        }

        return command_payload

    def get_unit_recolectors():

        recolector_payload = {
            "type": "BUY_UNIT",
            "payload": {
                "unit_type": "Collector",
                "quantity": 1,
            },
        }

        return recolector_payload

    def get_unit_attacker():

        attacker_payload = {
            "type": "BUY_UNIT",
            "payload": {
                "unit_type": "Attacker",
                "quantity": 1,
            },
        }

        return attacker_payload

    def attack(target_unit_id:int,attacker_unit_id:int):
        
        attack_payload= {
            "type": "ATTACK",
            "payload": {
                "target_id": target_unit_id,
                "attacker_id": attacker_unit_id,
            }
        }
        
        return attack_payload

    @staticmethod
    def get_pause_game(paused: bool):
        return {
            "type": "PAUSE_GAME",
            "payload": {
                "paused": paused
            }
        }

    @staticmethod
    def get_surrender():
        return {
            "type": "SURRENDER",
            "payload": {}
        }
