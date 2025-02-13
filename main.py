
import socket, time, threading, json

clients = []
playback_info = {"startTime": None, "positionMs": 0, "playing": False}

def accept_clients(server_socket):
    while True:
        client_socket, addr = server_socket.accept()
        clients.append(client_socket)
        print(f"Client connected: {addr}")

def send_to_all(msg_dict):
    msg_str = json.dumps(msg_dict) + "\n"
    for c in clients:
        c.sendall(msg_str.encode())

def start_playback():
    now = int(time.time() * 1000)
    future = now + 2000  # 2s lead time
    playback_info["startTime"] = future
    playback_info["positionMs"] = 0
    playback_info["playing"] = True
    # Broadcast command
    send_to_all({"cmd": "PLAY", "startTime": future, "startPosMs": 0})

def heartbeat_loop():
    while True:
        if playback_info["playing"]:
            now = int(time.time() * 1000)
            playhead = now - playback_info["startTime"] + playback_info["positionMs"]
            playhead = max(playhead, 0)
            send_to_all({
                "cmd": "HEARTBEAT",
                "masterTime": now,
                "playheadMs": playhead
            })
        time.sleep(10)

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 12345))
    server_socket.listen(5)
    threading.Thread(target=accept_clients, args=(server_socket,)).start()
    threading.Thread(target=heartbeat_loop).start()

    # Wait for user input to start playback
    while True:
        cmd = input("Type 'play' to start playback: ")
        if cmd == "play":
            start_playback()

if __name__ == "__main__":
    main()