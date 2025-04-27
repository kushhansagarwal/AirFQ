@component
export class WebSocketExample extends BaseScriptComponent {
  @input
  remoteServiceModule: RemoteServiceModule;

  private socket!: WebSocket;
  // Method called when the script is awake
  async onAwake() {
    this.socket = this.remoteServiceModule.createWebSocket('wss://s14548.nyc1.piesocket.com/v3/snap?api_key=S3mOqwO98bva0NAXrXIlhAWVh0RKBaWL0HNsvkdS');

    this.socket.binaryType = 'blob';

    // Listen for the open event
    this.socket.onopen = (event: WebSocketEvent) => {
      // Socket has opened, send a message back to the server
      this.socket.send('Message 1');

      // Try sending a binary message
      // (the bytes below spell 'Message 2')
      const message: number[] = [77, 101, 115, 115, 97, 103, 101, 32, 50];
      const bytes = new Uint8Array(message);
      this.socket.send(bytes);
    };

    // Listen for messages
    this.socket.onmessage = async (event: WebSocketMessageEvent) => {
      if (event.data instanceof Blob) {
        // Binary frame, can be retrieved as either Uint8Array or string
        const bytes = await event.data.bytes();
        const text = await event.data.text();

        print('Received binary message, printing as text: ' + text);
      } else {
        // Text frame
        const text: string = event.data;
        print('Received text message: ' + text);
      }
    };
    this.socket.onclose = (event: WebSocketCloseEvent) => {
      if (event.wasClean) {
        print('Socket closed cleanly');
      } else {
        print('Socket closed with error, code: ' + event.code);
      }
    };

    this.socket.onerror = (event: WebSocketErrorEvent) => {
      print('Socket error');
    };
  }
}