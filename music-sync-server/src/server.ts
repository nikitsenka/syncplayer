// src/server.ts

import fs from 'fs';
import path from 'path';
import net from 'net';
import express from 'express';
import http from 'http';
import { Server as SocketIOServer } from 'socket.io';

////////////////////////////////////////////////////////////////////////////////
// 1. TCP Server Logic (similar to the Python code)
////////////////////////////////////////////////////////////////////////////////

interface PlaybackCommand {
  cmd: string;
  filename?: string;
  startTime?: number;
  startPosMs?: number;
}

let tcpClients: net.Socket[] = [];
let serverRunning = true;

/**
 * Accept incoming TCP clients and store them in `tcpClients`.
 */
function startTcpServer(tcpPort: number) {
  const tcpServer = net.createServer((socket) => {
    console.log('TCP client connected:', socket.remoteAddress, socket.remotePort);
    tcpClients.push(socket);

    socket.on('close', () => {
      console.log('TCP client disconnected');
      tcpClients = tcpClients.filter((s) => s !== socket);
    });

    socket.on('error', () => {
      console.log('TCP client error');
      tcpClients = tcpClients.filter((s) => s !== socket);
    });
  });

  tcpServer.listen(tcpPort, () => {
    console.log(`TCP server listening on port ${tcpPort}`);
  });

  return tcpServer;
}

/**
 * Send a command (PLAY or STOP) to all connected TCP clients.
 */
function sendToAllClients(msg: PlaybackCommand) {
  const msgString = JSON.stringify(msg) + '\n';
  const disconnected: net.Socket[] = [];

  tcpClients.forEach((socket) => {
    try {
      socket.write(msgString);
    } catch (err) {
      console.log('Error sending to client:', err);
      disconnected.push(socket);
    }
  });

  // Remove disconnected clients
  disconnected.forEach((sock) => {
    tcpClients = tcpClients.filter((s) => s !== sock);
  });
}

/**
 * Instruct clients to start playback of `filename` at `positionSec`.
 */
function startPlayback(filename: string, positionSec: number = 0) {
  const now = Date.now() * 1_000_000; // Convert ms to ns
  const positionMs = Math.floor(positionSec * 1000);
  sendToAllClients({
    cmd: 'PLAY',
    filename,
    startTime: now,
    startPosMs: positionMs,
  });
}

/**
 * Instruct clients to stop playback.
 */
function stopPlayback() {
  sendToAllClients({ cmd: 'STOP' });
}

////////////////////////////////////////////////////////////////////////////////
// 2. Playlist Management
////////////////////////////////////////////////////////////////////////////////

/**
 * Recursively load all files from the provided `folder`.
 */
function loadPlaylist(folder: string): string[] {
  if (!fs.existsSync(folder) || !fs.lstatSync(folder).isDirectory()) {
    throw new Error(`Folder not found: ${folder}`);
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
        // Store relative path
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

function createWebServer(httpPort: number, musicDir: string) {
  // 1. Create an Express app + HTTP server
  const app = express();
  const server = http.createServer(app);
  const io = new SocketIOServer(server);

  // Serve static files from "public" (where our UI will live)
  app.use(express.static(path.join(__dirname, '..', 'public')));

  // 2. Basic socket.io events
  io.on('connection', (socket) => {
    console.log('Web UI client connected via Socket.IO');

    // Send the playlist upon connection
    socket.emit('playlist', globalPlaylist);

    socket.on('play', (index: number) => {
      if (index < 0 || index >= globalPlaylist.length) return;
      currentIndex = index;
      const filename = globalPlaylist[currentIndex];
      console.log(`Playing: ${filename}`);
      startPlayback(filename, 0);
    });

    socket.on('stop', () => {
      console.log('Stopping playback');
      stopPlayback();
    });

    socket.on('disconnect', () => {
      console.log('Web UI client disconnected');
    });
  });

  // 3. Start the server
  server.listen(httpPort, () => {
    console.log(`Web server listening on http://localhost:${httpPort}`);
  });

  // 4. Load the playlist
  globalPlaylist = loadPlaylist(musicDir);
  console.log(`Playlist loaded. ${globalPlaylist.length} items found.`);

  return server;
}

////////////////////////////////////////////////////////////////////////////////
// 4. Main Entry Point
////////////////////////////////////////////////////////////////////////////////

function main() {
  const TCP_PORT = 12345;
  const HTTP_PORT = 3000;
  const MUSIC_DIR = '/Users/ivan/Music/From movies/Anime'; // or pass from process.env or command-line

  // Start the TCP server (for external media clients)
  const tcpServer = startTcpServer(TCP_PORT);

  // Start the Web/UI server
  const webServer = createWebServer(HTTP_PORT, MUSIC_DIR);

  // In a real app, you might capture shutdown signals:
  process.on('SIGINT', () => {
    console.log('Shutting down servers...');
    serverRunning = false;

    // Close all TCP client sockets
    tcpClients.forEach((sock) => sock.destroy());
    tcpClients = [];

    tcpServer.close(() => console.log('TCP server closed.'));
    webServer.close(() => {
      console.log('Web server closed.');
      process.exit(0);
    });
  });
}

main();