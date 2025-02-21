import socket, time, threading, json
import argparse
import os

clients = []
playback_info = {"startTime": None, "positionMs": 0, "playing": False}
server_running = True
playlist = []
current_index = 0


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


def start_playback(filename, position_sec=0):
    now = int(time.time_ns())
    position_ms = int(position_sec * 1000)  # Convert seconds to milliseconds
    send_to_all({"cmd": "PLAY", "filename": filename, "startTime": now, "startPosMs": position_ms})


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


def load_playlist(folder):
    if not os.path.isdir(folder):
        raise ValueError(f"Folder {folder} does not exist.")

    # Get absolute path of folder
    base_folder = os.path.abspath(folder)
    # Load playlist
    loaded_playlist = []
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            # Append relative path to playlist
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, base_folder)
            loaded_playlist.append(relpath)
    return loaded_playlist


def parse_args():
    parser = argparse.ArgumentParser(description='Audio playback synchronization server')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=12345,
                        help='Port to listen on (default: 12345)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--music-dir', required=True,
                        help='Directory containing music files')
    return parser.parse_args()


def main():
    global playlist, current_index

    args = parse_args()

    # Load playlist at startup
    try:
        playlist = load_playlist(args.music_dir)
        print(f"Loaded {len(playlist)} files into playlist.")
    except ValueError as e:
        print(f"Error: {e}")
        return

    if args.verbose:
        print(f"Starting server on {args.host}:{args.port}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((args.host, args.port))
    server_socket.listen(5)
    accept_thread = threading.Thread(target=accept_clients, args=(server_socket,))
    accept_thread.start()

    print("Commands:")
    print("  play            - Start playback from beginning of the playlist")
    print("  play <seconds>  - Start playback from specified position")
    print("  play_next       - Play next song in the playlist")
    print("  stop            - Stop playback")
    print("  exit            - Quit the program")

    while True:
        cmd = input("> ")
        cmd_parts = cmd.strip().split()

        if not cmd_parts:
            continue

        if cmd_parts[0] == "play":
            if not playlist:
                print("Playlist is empty.")
                continue
            if len(cmd_parts) > 1:
                try:
                    start_sec = int(cmd_parts[1])
                    filename = playlist[current_index]
                    start_playback(filename, start_sec)
                    if args.verbose:
                        print(f"Starting playback at {start_sec} seconds of {filename}")
                except ValueError:
                    print("Invalid time format. Please use seconds (e.g., 'play 5' or 'play 5.5')")
            else:
                filename = playlist[current_index]
                start_playback(filename)
                if args.verbose:
                    print(f"Starting playback {filename} from beginning")
        elif cmd_parts[0] == "play_next":
            if not playlist:
                print("Playlist is empty.")
                continue
            current_index += 1
            if current_index >= len(playlist):
                print("Reached end of playlist.")
                current_index = 0
            filename = playlist[current_index]
            start_playback(filename)
            if args.verbose:
                print(f"Playing next song: {filename}")
        elif cmd_parts[0] == "stop":
            stop_playback()
            if args.verbose:
                print("Stopping playback")
        elif cmd_parts[0] == "exit":
            if args.verbose:
                print("Shutting down server...")
            cleanup()
            break
        else:
            print("Unknown command")

    server_socket.close()
    accept_thread.join()
    print("Server shutdown complete")


if __name__ == "__main__":
    main()