import socket, json, time
import vlc
import argparse

DELAY_TO_SYNC_SEC = 2

FILE_PATH = "song.mp3"
MASTER_PORT = 12345

player = vlc.MediaPlayer(FILE_PATH)

def set_playhead(ms):
    player.set_time(ms)

def handle_message(msg, calibration):
    cmd = msg.get("cmd", "")
    if cmd == "PLAY":
        target_time_ns = msg["startTime"] + DELAY_TO_SYNC_SEC * 1000000000
        startPosMs = msg["startPosMs"]
        while True:
            current_time_ns = int(time.time_ns())
            if current_time_ns >= target_time_ns:
                print(f"Current time {current_time_ns}")
                break
            time.sleep(0.000001)

        set_playhead(startPosMs + calibration)
        print(f"Current playhead {player.get_time()}")
        player.play()
    elif cmd == "STOP":
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
                handle_message(msg, args.calibration)
                if args.verbose:
                    print(f"Received command: {msg['cmd']}")
    finally:
        # Clean up
        s.close()

if __name__ == "__main__":
    main()