import socket
import json
import time
import vlc
import argparse
import base64
import os

DELAY_TO_SYNC_SEC = 2
MASTER_PORT = 12345

# We will set the player later once we know the actual filename.
player = None

def set_playhead(ms):
    if player is not None:
        player.set_time(ms)

def handle_message(msg, calibration):
    global player

    cmd = msg.get("cmd", "")

    if cmd == "FILE":
        # Receive file if it doesn't already exist
        filename = msg.get("filename", "song.mp3")
        encoded_data = msg.get("data", "")

        if not os.path.exists(filename):
            with open(filename, "wb") as f:
                f.write(base64.b64decode(encoded_data))
            print(f"Received and saved new file: {filename}")
        else:
            print(f"File '{filename}' already exists. Skipping download.")

        # Reinitialize the player to use this file for future playback
        player = vlc.MediaPlayer(filename)

    elif cmd == "PLAY":
        if player is None:
            print("No audio file available for playback. Please ensure file is sent first.")
            return

        target_time_ns = msg["startTime"] + DELAY_TO_SYNC_SEC * 1000000000
        startPosMs = msg["startPosMs"]
        while True:
            current_time_ns = int(time.time_ns())
            if current_time_ns >= target_time_ns:
                break
            time.sleep(0.000001)

        set_playhead(startPosMs + calibration)
        player.play()
        print(f"Playing from {player.get_time()}ms (calibration: {calibration}ms)")

    elif cmd == "STOP":
        if player is not None:
            player.stop()
            print("Playback stopped.")

def parse_args():
    parser = argparse.ArgumentParser(description='Audio playback synchronization client')
    parser.add_argument('--ip', required=True,
                        help='IP address of the master server')
    parser.add_argument('--port', type=int, default=MASTER_PORT,
                        help=f'Port to connect to (default: {MASTER_PORT})')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--calibration', type=int, required=False, default=0,
                        help='ms to adjust (default: 0)')
    return parser.parse_args()

def main():
    args = parse_args()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if args.verbose:
        print(f"Connecting to {args.ip}:{args.port}")

    try:
        s.connect((args.ip, args.port))
        buffer = ""

        while True:
            data = s.recv(1024)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip() == "":
                    continue
                msg = json.loads(line)
                handle_message(msg, args.calibration)
                if args.verbose and "cmd" in msg:
                    print(f"Received command: {msg['cmd']}")
    finally:
        s.close()

if __name__ == "__main__":
    main()