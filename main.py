import socket
import threading
import json
import struct
import base64
import logging
import os
import sys
import yaml

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")

DEFAULT_CONFIG_TEXT = """ip: 0.0.0.0
port: 25565
motd: |
  §aFake Minecraft Server
  §7Welcome!
version_text: FakeMinecraftServer
kick_message: |
  You cannot join this server.
  Please contact admin.
server_icon: ''
max_players: 10
online_players: 0
"""

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_TEXT)
    print(f"{CONFIG_FILE} not found! Generated default config. Edit it and run again.")
    sys.exit(0)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

class PacketUtils:
    @staticmethod
    def read_varint(sock):
        num_read = 0
        result = 0
        while True:
            byte = sock.recv(1)
            if not byte:
                break
            value = byte[0]
            result |= (value & 0x7F) << (7 * num_read)
            num_read += 1
            if not value & 0x80:
                break
            if num_read > 5:
                raise Exception("VarInt too big")
        return result

    @staticmethod
    def write_varint(value):
        buf = b""
        while True:
            temp = value & 0x7F
            value >>= 7
            if value != 0:
                temp |= 0x80
            buf += struct.pack("B", temp)
            if value == 0:
                break
        return buf

    @staticmethod
    def read_utf(sock):
        length = PacketUtils.read_varint(sock)
        return sock.recv(length).decode("utf-8")

    @staticmethod
    def write_utf(string):
        data = string.encode("utf-8")
        return PacketUtils.write_varint(len(data)) + data

class ClientThread(threading.Thread):
    def __init__(self, conn, addr, config):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.config = config

    def send_packet(self, packet_id, data_bytes):
        packet = PacketUtils.write_varint(packet_id) + data_bytes
        length = PacketUtils.write_varint(len(packet))
        self.conn.sendall(length + packet)

    def run(self):
        try:
            length = PacketUtils.read_varint(self.conn)
            packet_id = PacketUtils.read_varint(self.conn)
            if packet_id == 0:
                protocol_version = PacketUtils.read_varint(self.conn)
                server_address = PacketUtils.read_utf(self.conn)
                server_port = struct.unpack(">H", self.conn.recv(2))[0]
                next_state = PacketUtils.read_varint(self.conn)
                username = "Unknown"
                try:
                    username_length = PacketUtils.read_varint(self.conn)
                    username = self.conn.recv(username_length).decode("utf-8")
                except:
                    pass
                username_display = username if username else self.addr[0]
                logging.info(f"\033[1;32m[{self.addr[0]}:{self.addr[1]}]\033[0m -> \033[1;34m{username_display}\033[0m connected, next_state={next_state}")
                if next_state == 1:
                    status = {
                        "version": {"name": self.config.get("version_text"), "protocol": -1},
                        "players": {"max": self.config.get("max_players"), "online": self.config.get("online_players")},
                        "description": {"text": self.config.get("motd")}
                    }
                    icon_path = self.config.get("server_icon")
                    if icon_path and os.path.exists(icon_path):
                        with open(icon_path, "rb") as f:
                            icon_b64 = base64.b64encode(f.read()).decode("utf-8")
                        status["favicon"] = f"data:image/png;base64,{icon_b64}"
                    self.send_packet(0, PacketUtils.write_utf(json.dumps(status)))
                    ping_payload = self.conn.recv(8)
                    logging.info(f"\033[1;36mPing received from {username_display}@{self.addr[0]}:{self.addr[1]}, replying pong\033[0m")
                    self.send_packet(1, ping_payload)
                elif next_state == 2:
                    kick_msg_text = self.config.get("kick_message")
                    kick_json = json.dumps({"text": kick_msg_text})
                    self.send_packet(0, PacketUtils.write_utf(kick_json))
                    logging.info(f"\033[1;31mKicked {username_display}@{self.addr[0]}:{self.addr[1]}: {kick_msg_text.splitlines()[0]}\033[0m")
        except Exception as e:
            logging.error(f"[{self.addr}] Error: {e}")
        finally:
            self.conn.close()

class MCServer:
    def __init__(self, config):
        self.config = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        ip = self.config.get("ip", "0.0.0.0")
        port = self.config.get("port", 25565)
        try:
            self.sock.bind((ip, port))
            self.sock.listen()
            print(f"\033[1;33mFake Minecraft Server listening on {ip}:{port}\033[0m")
        except OSError as e:
            logging.error(f"Cannot bind to {ip}:{port}: {e}")
            sys.exit(1)
        try:
            while True:
                conn, addr = self.sock.accept()
                ClientThread(conn, addr, self.config).start()
        except KeyboardInterrupt:
            print("\033[1;33mServer shutting down...\033[0m")
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            self.sock.close()

if __name__ == "__main__":
    server = MCServer(config)
    server.start()
