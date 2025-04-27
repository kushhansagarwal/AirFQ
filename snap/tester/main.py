import asyncio
import websockets
import time

async def send_hi_periodically():
    # Connect to the WebSocket server
    uri = "wss://s14548.nyc1.piesocket.com/v3/snap?api_key=S3mOqwO98bva0NAXrXIlhAWVh0RKBaWL0HNsvkdS"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send "hi" message every 2 seconds
            while True:
                await websocket.send("hi")
                print("Sent 'hi' message")
                await asyncio.sleep(2)
    except Exception as e:
        print(f"Error: {e}")

# Main async function to run the program
async def main():
    # Start the WebSocket communication task
    task = asyncio.create_task(send_hi_periodically())
    
    # Keep the main coroutine running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        task.cancel()
        print("Program terminated")

# Run the async program
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Program terminated by user")
