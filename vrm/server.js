const http = require("http");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");

const PORT = 3000;
const WS_PORT = 8080;

const mimeTypes = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".vrm": "model/gltf-binary",
  ".vrma": "model/gltf-binary",
  ".glb": "model/gltf-binary",
  ".gltf": "model/gltf+json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".wasm": "application/wasm",
};

const server = http.createServer((req, res) => {
  let filePath = path.join(__dirname, req.url);
  if (req.url === "/") {
    filePath = path.join(__dirname, "index.html");
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      return res.end("Not Found");
    }

    const ext = path.extname(filePath);
    const type = mimeTypes[ext] || "application/octet-stream";

    res.writeHead(200, {
      "Content-Type": type,
    });

    res.end(data);
  });
});

server.listen(PORT, () => console.log(`Server is running at PORT ${PORT}`));

const wss = new WebSocket.Server({
  port: WS_PORT,
});

let pythonClient = null;
let browsers = [];

wss.on("connection", (ws) => {
  console.log("WebSocket client connected");

  ws.on("message", (data, isBinary) => {
    // Text messages identify clients
    if (!isBinary) {
      const type = data.toString();

      if (type === "python") {
        pythonClient = ws;
        console.log("Python audio source connected");
      }

      if (type === "browser") {
        browsers.push(ws);
        console.log("Browser audio client connected");
      }

      return;
    }

    // Binary data = audio

    if (ws === pythonClient) {
      console.log("Audio chunk:", data.length, "bytes");

      for (const browser of browsers) {
        if (browser.readyState === WebSocket.OPEN) {
          browser.send(data);
        }
      }
    }
  });

  ws.on("close", () => {
    console.log("WebSocket disconnected");

    browsers = browsers.filter((client) => client !== ws);

    if (ws === pythonClient) {
      pythonClient = null;
    }
  });
});
