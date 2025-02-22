// src/server.ts
import fs from 'fs';
import path from 'path';
import net from 'net';
import express from 'express';
import http from 'http';
import { Server as SocketIOServer } from 'socket.io';

////////////////////////////////////////////////////////////////////////////////
// 1. TCP Server Logic
////////////////////////////////////////////////////////////////////////////////

interface PlaybackCommand {
  cmd: 'PLAY' | 'STOP';
  filename?: string;
  startTime?: number;
  startPosMs?: number;
}

let tcpClients: net.Socket[] = [];
let serverRunning = true;

/** Start a TCP server that accepts clients on tcpPort. */
function startTcpServer(tcpPort: number): net.Server {
  const tcpServer = net.createServer((socket) => {
    console.log('TCP client connected:', socket.remoteAddress, socket.remotePort);
    tcpClients.push(socket);

    socket.on('close', () => {
      console.log('TCP client disconnected');
      tcpClients = tcpClients.filter((s) => s !== socket);
    });

    socket.on('error', (err) => {
      console.log('TCP client error:', err);
      tcpClients = tcpClients.filter((s) => s !== socket);
    });
  });

  tcpServer.listen(tcpPort, () => {
    console.log(`TCP server listening on port ${tcpPort}`);
  });
  return tcpServer;
}

/** Broadcast a command (PLAY/STOP) to all connected TCP clients. */
function sendToAllClients(msg: PlaybackCommand) {
  const msgString = JSON.stringify(msg) + '\n';
  const disconnected: net.Socket[] = [];

  tcpClients.forEach((socket) => {
    try {
      socket.write(msgString);
    } catch (err) {
      console.log('Error writing to client:', err);
      disconnected.push(socket);
    }
  });

  // Remove disconnected
  disconnected.forEach((sock) => {
    tcpClients = tcpClients.filter((s) => s !== sock);
  });
}

/** Tell TCP clients to start playback of `filename` at optional `positionSec`. */
function startPlayback(filename: string, positionSec = 0) {
  const now = Date.now() * 1_000_000; // Convert ms to ns
  const positionMs = Math.floor(positionSec * 1000);
  sendToAllClients({
    cmd: 'PLAY',
    filename,
    startTime: now,
    startPosMs: positionMs,
  });
}

/** Tell TCP clients to stop playback. */
function stopPlayback() {
  sendToAllClients({ cmd: 'STOP' });
}

////////////////////////////////////////////////////////////////////////////////
// 2. Playlist Management
////////////////////////////////////////////////////////////////////////////////

function loadPlaylist(folder: string): string[] {
  if (!fs.existsSync(folder) || !fs.lstatSync(folder).isDirectory()) {
    throw new Error(`Folder not found or not a directory: ${folder}`);
  }

  const playlist: string[] = [];

  function readDirRecursively(dir: string) {
    const items = fs.readdirSync(dir);
    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = fs.lstatSync(fullPath);
      if (stat.isDirectory()) {
        readDirRecursively(fullPath);
      } else {
        const relative = path.relative(folder, fullPath);
        playlist.push(relative);
      }
    }
  }

  readDirRecursively(folder);
  return playlist;
}

////////////////////////////////////////////////////////////////////////////////
// 3. Express + Socket.IO for the Web UI
////////////////////////////////////////////////////////////////////////////////

let globalPlaylist: string[] = [];
let currentIndex = 0;
let currentFile: string | null = null;

/**
 * Start an Express + Socket.IO server for front-end UI on httpPort.
 * On "selectFolder", load the new playlist.
 * On "play", either play the selected track (possibly looping).
 * On "playNext", advance or loop.
 * On "stop", stop playback.
 */
function createWebServer(httpPort: number): http.Server {
  const app = express();
  const server = http.createServer(app);
  const io = new SocketIOServer(server);

  // Serve static files (our front-end) from "public"
  app.use(express.static(path.join(__dirname, '..', 'public')));

  // Listen for socket.io connections
  io.on('connection', (socket) => {
    console.log('Web UI client connected');

    // Send current playlist & highlight info
    socket.emit('playlistData', {
      playlist: globalPlaylist,
      currentIndex,
    });

    // 1. User selects a folder -> reload playlist
    socket.on('selectFolder', (folderPath: string) => {
      try {
        globalPlaylist = loadPlaylist(folderPath);
        currentIndex = 0;
        currentFile = null;
        console.log(`Loaded ${globalPlaylist.length} items from folder: ${folderPath}`);

        // Notify all clients about the new playlist
        io.emit('playlistData', {
          playlist: globalPlaylist,
          currentIndex,
        });
      } catch (err) {
        console.error('Error loading folder:', err);
        socket.emit('errorMessage', (err as Error).message);
      }
    });

    // 2. Play a given index, with optional loop
    interface PlayMsg {
      index: number;
      loop: boolean;
    }
    socket.on('play', (data: PlayMsg) => {
      const { index, loop } = data;
      if (!globalPlaylist.length) return;
      if (index < 0 || index >= globalPlaylist.length) return;

      currentIndex = index;
      currentFile = globalPlaylist[currentIndex];
      console.log(`Playing: ${currentFile}, loop=${loop}`);

      startPlayback(currentFile);

      // Update all clients with currentIndex
      io.emit('playlistData', {
        playlist: globalPlaylist,
        currentIndex,
      });

      // If loop is on, we could “auto-play” the same track after it ends,
      // but we have no real "on track end" event from the server side.
      // We'll handle "playNext" logic separately (see below).
    });

    // 3. "Play Next" – either loop the same track or move forward
    socket.on('playNext', (loop: boolean) => {
      if (!globalPlaylist.length) return;
      if (loop && currentFile) {
        // Re-play the same track
        console.log(`Looping track: ${currentFile}`);
        startPlayback(currentFile);
      } else {
        // Advance to next
        currentIndex = (currentIndex + 1) % globalPlaylist.length;
        currentFile = globalPlaylist[currentIndex];
        console.log(`Playing next: ${currentFile}`);
        startPlayback(currentFile);
      }

      io.emit('playlistData', {
        playlist: globalPlaylist,
        currentIndex,
      });
    });

    // 4. "Stop" – broadcast STOP
    socket.on('stop', () => {
      console.log('Stopping playback');
      stopPlayback();
    });

    socket.on('disconnect', () => {
      console.log('Web UI client disconnected');
    });
  });

  server.listen(httpPort, () => {
    console.log(`Web server (UI) listening on http://localhost:${httpPort}`);
  });

  return server;
}

////////////////////////////////////////////////////////////////////////////////
// 4. Main Entry Point
////////////////////////////////////////////////////////////////////////////////

function main() {
  const TCP_PORT = 12345;
  const HTTP_PORT = 3000;

  // Start the TCP server
  const tcpServer = startTcpServer(TCP_PORT);

  // Start the web server
  const webServer = createWebServer(HTTP_PORT);

  // Graceful shutdown
  process.on('SIGINT', () => {
    console.log('Shutting down...');
    serverRunning = false;

    // Close all TCP clients
    tcpClients.forEach((sock) => sock.destroy());
    tcpClients = [];

    // Close servers
    tcpServer.close(() => console.log('TCP server closed.'));
    webServer.close(() => {
      console.log('Web server closed.');
      process.exit(0);
    });
  });
}

main();