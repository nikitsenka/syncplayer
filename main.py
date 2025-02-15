import socket
import time
import threading
import json
import argparse
import base64
import os

clients = []
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

def send_file(file_path):
    """Send the specified audio file to all connected clients (base64-encoded)."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
        encoded_data = base64.b64encode(file_data).decode("utf-8")
        send_to_all({
            "cmd": "FILE",
            "filename": os.path.basename(file_path),
            "data": encoded_data
        })
        print(f"File '{file_path}' sent to all clients.")
    except Exception as e:
        print(f"Failed to send file: {e}")

def start_playback(position_sec=0):
    now = int(time.time_ns())
    position_ms = int(position_sec * 1000)  # Convert seconds to milliseconds
    send_to_all({"cmd": "PLAY", "startTime": now, "startPosMs": position_ms})

def stop_playback():
    send_to_all({"cmd": "STOP"})

def cleanup(server_socket, accept_thread):
    global server_running
    server_running = False
    for c in clients:
        try:
            c.close()
        except:
            pass
    clients.clear()
    server_socket.close()
    accept_thread.join()
    print("Server shutdown complete")

def parse_args():
    parser = argparse.ArgumentParser(description='Audio playback synchronization server')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=12345,
                        help='Port to listen on (default: 12345)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--audio-file', type=str, default=None,
                        help='Path to the audio file to synchronize across clients')
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
    print("  send_file      - Send the audio file (if specified via --audio-file) to all clients")
    print("  exit           - Quit the program")

    while True:
        cmd = input("> ")
        if not cmd.strip():
            continue

        cmd_parts = cmd.split()

        if cmd_parts[0] == "play":
            if len(cmd_parts) > 1:
                try:
                    start_sec = float(cmd_parts[1])
                    start_playback(start_sec)
                    if args.verbose:
                        print(f"Starting playback at {start_sec} seconds")
                except ValueError:
                    print("Invalid time format. Please use seconds (e.g., 'play 5' or 'play 5.5')")
            else:
                start_playback(0)
                if args.verbose:
                    print("Starting playback from beginning")
        elif cmd_parts[0] == "stop":
            stop_playback()
            if args.verbose:
                print("Stopping playback")
        elif cmd_parts[0] == "send_file":
            if args.audio_file:
                send_file(args.audio_file)
            else:
                print("No audio file specified. Use --audio-file to set a file path.")
        elif cmd_parts[0] == "exit":
            if args.verbose:
                print("Shutting down server...")
            cleanup(server_socket, accept_thread)
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()