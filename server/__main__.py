from .server import Server

if __name__ == "__main__":
    print("[STARTING] server starting", flush=True)
    server = Server()
    server.start()
