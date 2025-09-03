import {WebSocket, WebSocketServer} from "ws";
import bonjour from "bonjour";

const HOST = "0.0.0.0";

const PORT = 8080;

const wss = new WebSocketServer({host: HOST, port: PORT});

const clients = new Set<WebSocket>();

let latestMessage: [WebSocket, string] | null = null;

wss.on("connection", (ws: WebSocket) => {
    clients.add(ws);

    if (latestMessage != null) {
        clients.forEach(client => {
            const [sender, message] = latestMessage!

            if (sender != client) {
                client.send(message)
            }
        })
    }

    ws.on("message", (msg: WebSocket.Data) => {
        if (typeof msg === "string") {
            latestMessage = [ws, msg];
        }
    });

    ws.on("close", () => {
        clients.delete(ws);

        if (latestMessage != null && latestMessage[0] === ws) {
            latestMessage = null;
        }
    });
});

const bonjourService = bonjour();

bonjourService.publish({
    name: "comfyui-camera-capture-node",
    type: "_ws._tcp",
    port: PORT
});