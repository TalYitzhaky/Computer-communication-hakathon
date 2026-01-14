import socket
import threading
import time

from protocol import Protocol
from game import BlackjackRound

class Server:
    UDP_PORT = 13117
    BROADCAST_INTERVAL = 1

    def __init__(self, server_name: str, tcp_port: int):
        self.server_name = server_name
        self.tcp_port = tcp_port
        self.running = True

    def start_udp_broadcast(self):
        def broadcast_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            print("Server started, sending offers...")

            while self.running:
                offer = Protocol.build_offer_packet(
                    self.tcp_port,
                    self.server_name
                )
                sock.sendto(offer, ('<broadcast>', self.UDP_PORT))
                time.sleep(self.BROADCAST_INTERVAL)

        threading.Thread(target=broadcast_loop, daemon=True).start()

    def start_tcp_server(self):
        ip = socket.gethostbyname(socket.gethostname())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.tcp_port))
        sock.listen()
        sock.settimeout(1)
        print(f"Server started, listening on IP address {ip} and port {self.tcp_port}")

        while self.running:
            try:
                client_sock, addr = sock.accept()
                print(f"Client connected from {addr}")

                threading.Thread(
                    target=self.handle_client,
                    args=(client_sock,),
                    daemon=True
                ).start()
            except socket.timeout:
                continue

    def handle_client(self, sock: socket.socket):
        client_name = "Unknown"
        try:
            sock.settimeout(None)
            data = sock.recv(Protocol.REQUEST_SIZE)
            if not data: return
            
            request = Protocol.parse_request_packet(data)
            num_rounds = request["rounds"]
            client_name = request["client_name"]
            
            print(f"Starting {num_rounds} rounds with {client_name}")

            for _ in range(num_rounds):
                self.play_round(sock)
                time.sleep(0.1)

            print(f"Finished rounds for {client_name}. Cleaning up...")
            time.sleep(1.5) 

        except (ConnectionResetError, BrokenPipeError):
            print(f"Client {client_name} disconnected abruptly.")
        except Exception as e:
            print(f"Error handling {client_name}: {e}")
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            sock.close()
            print(f"Socket for {client_name} closed safely.")

    def play_round(self, sock: socket.socket):
        sock.settimeout(None)
        game = BlackjackRound()
        game.initial_deal()

        for c in [
            game.player_hand.cards[0],
            game.player_hand.cards[1],
            game.dealer_hand.cards[0]
        ]:
            sock.sendall(
                Protocol.build_payload_packet(
                    b"\x00" * 5,
                    Protocol.ROUND_NOT_OVER,
                    c.rank,
                    c.suit
                )
            )

        while not game.finished:
            data = sock.recv(Protocol.PAYLOAD_SIZE)
            if not data:
                return

            payload = Protocol.parse_payload_packet(data)

            if payload["decision"] == Protocol.HIT:
                game.player_hit()
                c = game.player_hand.cards[-1]

                sock.sendall(
                    Protocol.build_payload_packet(
                        b"\x00" * 5,
                        Protocol.ROUND_NOT_OVER,
                        c.rank,
                        c.suit
                    )
                )

                if game.player_hand.total >= 21:
                    break

            else: 
                game.player_stand()
                break

        for i in range(1, len(game.dealer_hand.cards)):
            c = game.dealer_hand.cards[i]
            sock.sendall(
                Protocol.build_payload_packet(
                    b"\x00" * 5,
                    Protocol.ROUND_NOT_OVER,
                    c.rank,
                    c.suit
                )
            )

        result_code = Protocol.result_to_code(game.result())
        sock.sendall(
            Protocol.build_payload_packet(
                b"\x00" * 5,
                result_code,
                0,
                0
            )
        )


    def run(self):
        self.start_udp_broadcast()
        self.start_tcp_server()


if __name__ == "__main__":
    server = Server(server_name="Team Tal", tcp_port=5000)
    try:
        server.run()
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.running = False