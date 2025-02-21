import socket, json, time
import vlc
import argparse
import os

DELAY_TO_SYNC_SEC = 3
MASTER_PORT = 12345

player = None  # Initialize player as None

def handle_message(msg, calibration, music_dir):
    global player
    cmd = msg.get("cmd", "")
    print(f"Current time: {int(time.time() * 1000)}")
    if cmd == "PLAY":
        filename = msg.get("filename", "")
        target_time_ns = msg["startTime"] + (DELAY_TO_SYNC_SEC * 1000000000)

        if filename:
            filepath = os.path.join(music_dir, filename)
            if not os.path.exists(filepath):
                print(f"File {filepath} does not exist.")
                return
            if player is None:
                player = vlc.MediaPlayer(filepath)
            else:
                media = vlc.Media(filepath)
                player.set_media(media)
            player.play()
            time.sleep(0.01)
            player.stop()
            print(f"Received startTime: {msg['startTime']}")
            print(f"Target time with d: {target_time_ns}")
            print(f"Current time      : {int(time.time_ns())}")
            while True:
                current_time_ns = int(time.time_ns())
                if current_time_ns >= target_time_ns:
                    print(f"Current time {current_time_ns}")
                    break
                time.sleep(0.000001)
            print(f"Current time: {int(time.time() * 1000)}")
            time.sleep(calibration / 1000)
            player.play()
    elif cmd == "STOP":
        if player:
            player.stop()

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
    parser.add_argument('--music-dir', default='.',
                        help='Base directory for music files (default: current directory)')
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
                msg = json.loads(line)
                handle_message(msg, args.calibration, args.music_dir)
                if args.verbose:
                    print(f"Received command: {msg['cmd']}")
    finally:
        # Clean up
        s.close()

if __name__ == "__main__":
    main()
