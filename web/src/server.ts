import {WebSocket, WebSocketServer} from "ws";

const HOST = "0.0.0.0";

const PORT = 8080;

const wss = new WebSocketServer({host: HOST, port: PORT});

const clients = new Set<WebSocket>();

let latestFrame: Buffer | null = null;

wss.on("connection", (ws: WebSocket) => {
    clients.add(ws);

    console.log(`Client connected, total: ${clients.size}`);

    ws.on("message", (msg: WebSocket.Data) => {
        console.log(`Received message: ${msg}`);

        try {
            if (Buffer.isBuffer(msg)) {
                latestFrame = msg;

                clients.forEach(client => {
                    if (client.readyState === WebSocket.OPEN && client !== ws && latestFrame != null) {
                        client.send(latestFrame);
                    }
                });
            }
        } catch (err) {
            console.error("Bad message", err);
        }
    });

    ws.on("close", () => {
        clients.delete(ws);

        console.log(`Client disconnected, remaining: ${clients.size}`);
    });

    ws.send(JSON.stringify({info: "Connected"}));
});

console.log(`Server running on ws://${HOST}:${PORT}`);