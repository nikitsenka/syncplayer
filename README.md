# SyncPlayer

SyncPlayer is a multi-device, synchronized MP3 player. It allows you to play the same audio files on multiple devices in
perfect sync.

## Server

The server controls playback and synchronizes all connected clients.

### Running the server

```bash
# Basic usage
python main.py --music-dir /path/to/music

# With interactive TUI (recommended)
python main.py --music-dir /path/to/music --interactive

# Additional options
python main.py --music-dir /path/to/music --host 0.0.0.0 --port 12345 --verbose
```

### Server Interface

The server has two interface modes:

1. **Traditional CLI** (default): Text-based commands
    - `play` - Start playback from beginning of current track
    - `play <number>` - Play the song at specified position in playlist
    - `play <seconds>` - Start playback from specified time position
    - `play_next` - Play next song in the playlist
    - `stop` - Stop playback
    - `list` - List all songs in the playlist
    - `exit` - Quit the program

2. **Interactive TUI** (with `--interactive` flag): Full featured interface
    - Up/Down keys to navigate
    - Enter to select/double-click to play
    - Space to play/pause
    - N for next track
    - Q to quit

## Client

The client connects to the server and plays audio in sync with all other clients.

### Running the client

```bash
# Basic usage
python client.py --ip <server_ip> --music-dir /path/to/music

# With calibration adjustment (if your device needs timing adjustment)
python client.py --ip <server_ip> --music-dir /path/to/music --calibration 50

# Additional options
python client.py --ip <server_ip> --port 12345 --verbose --music-dir /path/to/music
```

## Important Notes

- All devices must have the same audio files available locally
- NTP synchronization is recommended for better timing accuracy
- The `--music-dir` path should contain the audio files to be played