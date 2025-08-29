# Fake Minecraft Server

A Python server that mimics a Minecraft server. It responds to ping requests and shows MOTD, version, and player info. Players cannot join.

## Requirements

- Python 3.8+
- PyYAML

Install dependencies:

```bash
pip install pyyaml
```

## Configuration

Edit `config.yml`. If missing, a default is created:

```yaml
ip: 0.0.0.0
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
```

## Usage

```bash
python3 main.py
```

- Minecraft clients can ping to see MOTD and version.
- Server logs connections, pings, and kicks.
- Stop with Ctrl+C.
