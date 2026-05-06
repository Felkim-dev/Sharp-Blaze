import os

def load_env():
    # Calculate the path to the .env file in the root directory (Sharp-Blaze/.env)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
    env_path = os.path.join(root_dir, ".env")
    
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key, val = line.strip().split('=', 1)
                        os.environ[key.strip()] = val.strip()

load_env()

class Config:
    #------- NETWORK ----------
    
    SERVER_IP = os.environ.get("SERVER_IP", "127.0.0.1")
    TCP_PORT_SERVER = 5555
    UDP_PORT_CLIENT = 0
    BROKER_IP = os.environ.get("SERVER_IP", "127.0.0.1")
    BROKER_PORT = 5000
    GAME_SERVER_UDP_PORT = 5556
    
    # ----- DEVELOPER MODE -------
    
    OFFLINE_DEBUG_MODE = False
    