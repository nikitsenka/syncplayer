
import socket, json, time
import vlc

FILE_PATH = "song.mp3"
MASTER_IP = "0.0.0.0"
MASTER_PORT = 12345

player = vlc.MediaPlayer(FILE_PATH)

def set_playhead(ms):
    player.set_time(ms)

def handle_message(msg):
    cmd = msg.get("cmd", "")
    if cmd == "PLAY":
        startTime = msg["startTime"]
        startPosMs = msg["startPosMs"]
        nowLocal = int(time.time() * 1000)
        delay = startTime - nowLocal
        if delay < 0:
            delay = 0
        time.sleep(delay / 1000)
        set_playhead(startPosMs)
        player.play()

    elif cmd == "HEARTBEAT":
        masterTime = msg["masterTime"]
        masterPlayhead = msg["playheadMs"]
        localPlayhead = player.get_time()
        diff = localPlayhead - masterPlayhead
        if abs(diff) > 50:
            corrected = localPlayhead - diff
            set_playhead(corrected + 50)

    # Handle PAUSE, RESUME, SEEK similarly...

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((MASTER_IP, MASTER_PORT))
    buffer = ""
    while True:
        data = s.recv(1024)
        if not data:
            break
        buffer += data.decode()
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            msg = json.loads(line)
            handle_message(msg)

if __name__ == "__main__":
    main()