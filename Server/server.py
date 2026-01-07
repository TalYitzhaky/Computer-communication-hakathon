import socket
import threading
import time

from protocol import Protocol
from game import BlackjackRound

class Server:
    UDP_PORT = 13117
    BROADCAST_INTERVAL = 1  # seconds

    def __init__(self, server_name: str, tcp_port: int):
        self.server_name = server_name
        self.tcp_port = tcp_port
        self.running = True

    # UDP broadcast thread
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

    # TCP server
    def start_tcp_server(self):
        ip = socket.gethostbyname(socket.gethostname())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.tcp_port))
        sock.listen()
        sock.settimeout(1)  # to allow periodic checks for self.running
        print(f"Server started, listening on IP address {ip} and port {self.tcp_port}")

        while self.running:
            try:
                client_sock, addr = sock.accept()  # will timeout every 1 second
                print(f"Client connected from {addr}")

                threading.Thread(
                    target=self.handle_client,
                    args=(client_sock,),
                    daemon=True
                ).start()
            except socket.timeout:
                continue  # check self.running again

    # Handle one client
    def handle_client(self, sock: socket.socket):
        try:
            data = sock.recv(Protocol.REQUEST_SIZE)
            request = Protocol.parse_request_packet(data)

            rounds = request["rounds"]
            client_name = request["client_name"]

            print(f"{client_name} requested {rounds} rounds")

            for _ in range(rounds):
                self.play_round(sock)

        except Exception as e:
            print("Client error:", e)

        finally:
            sock.close()
            print("Client disconnected")

    # Play one round
    def play_round(self, sock: socket.socket):
        game = BlackjackRound()
        print("Dealing initial cards")
        game.initial_deal()

        # Player turn
        while not game.finished:
            data = sock.recv(Protocol.PAYLOAD_SIZE)
            payload = Protocol.parse_payload_packet(data)

            decision = payload["decision"]

            if decision == Protocol.HIT:
                card = game.player_hit()
                print(f"Player hits: {card}")
                response = Protocol.build_payload_packet(
                    decision=b"\x00" * 5,
                    result=Protocol.ROUND_NOT_OVER,
                    rank=card.rank,
                    suit=card.suit
                )
                sock.sendall(response)

            elif decision == Protocol.STAND:
                game.player_stand()
                print("Player stands")
                break
            
        print(f"Dealer hand: {game.dealer_hand}")
        print(f"Round result: {game.result()}")

        # Send final result
        result_code = Protocol.result_to_code(game.result())
        final_packet = Protocol.build_payload_packet(
            decision=b"\x00" * 5,
            result=result_code
        )
        sock.sendall(final_packet)

    # Run server
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