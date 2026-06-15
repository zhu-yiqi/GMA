import socket
import threading

LHOST, LPORT = '0.0.0.0', 5556
THOST, TPORT = '127.0.0.1', 5555

listener = socket.socket()
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind((LHOST, LPORT))
listener.listen(16)


def pipe(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass
        try:
            src.close()
        except Exception:
            pass


def handle(client):
    try:
        target = socket.create_connection((THOST, TPORT))
    except Exception:
        client.close()
        return
    threading.Thread(target=pipe, args=(client, target), daemon=True).start()
    threading.Thread(target=pipe, args=(target, client), daemon=True).start()


while True:
    client, _ = listener.accept()
    threading.Thread(target=handle, args=(client,), daemon=True).start()
