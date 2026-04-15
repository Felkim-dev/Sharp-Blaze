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

    def get_startgame(): 

        start = {
            "type": "START_GAME",
            "payload":{
                "start" : False,
            },
        }

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
