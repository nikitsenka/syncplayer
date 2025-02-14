import socket, time, threading, json
import argparse

clients = []
playback_info = {"startTime": None, "positionMs": 0, "playing": False}
server_running = True


def accept_clients(server_socket):
    while server_running:
        try:
            server_socket.settimeout(1)
            client_socket, addr = server_socket.accept()
            clients.append(client_socket)
            print(f"Client connected: {addr}")
        except socket.timeout:
            continue
        except:
            break


def send_to_all(msg_dict):
    msg_str = json.dumps(msg_dict) + "\n"
    disconnected_clients = []
    for c in clients:
        try:
            c.sendall(msg_str.encode())
        except:
            disconnected_clients.append(c)

    # Remove disconnected clients
    for c in disconnected_clients:
        clients.remove(c)


def start_playback(position_sec=0):
    now = int(time.time_ns())
    position_ms = int(position_sec * 1000)  # Convert seconds to milliseconds
    send_to_all({"cmd": "PLAY", "startTime": now, "startPosMs": position_ms})


def stop_playback():
    send_to_all({"cmd": "STOP"})


def cleanup():
    global server_running
    server_running = False
    for c in clients:
        try:
            c.close()
        except:
            pass
    clients.clear()


def parse_args():
    parser = argparse.ArgumentParser(description='Audio playback synchronization server')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=12345,
                        help='Port to listen on (default: 12345)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        print(f"Starting server on {args.host}:{args.port}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((args.host, args.port))
    server_socket.listen(5)
    accept_thread = threading.Thread(target=accept_clients, args=(server_socket,))
    accept_thread.start()

    print("Commands:")
    print("  play           - Start playback from beginning")
    print("  play <seconds> - Start playback from specified position")
    print("  stop           - Stop playback")
    print("  exit           - Quit the program")

    while True:
        cmd = input("> ")
        cmd_parts = cmd.split()

        if not cmd_parts:
            continue

        if cmd_parts[0] == "play":
            if len(cmd_parts) > 1:
                try:
                    start_sec = int(cmd_parts[1])
                    start_playback(start_sec)
                    if args.verbose:
                        print(f"Starting playback at {start_sec} seconds")
                except ValueError:
                    print("Invalid time format. Please use seconds (e.g., 'play 5' or 'play 5.5')")
            else:
                start_playback(0)
                if args.verbose:
                    print("Starting playback from beginning")
        elif cmd == "stop":
            stop_playback()
            if args.verbose:
                print("Stopping playback")
        elif cmd == "exit":
            if args.verbose:
                print("Shutting down server...")
            cleanup()
            break

    server_socket.close()
    accept_thread.join()
    print("Server shutdown complete")


if __name__ == "__main__":
    main()