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
        client_name = "Unknown"
        try:
            sock.settimeout(None) # Wait forever for human input
            data = sock.recv(Protocol.REQUEST_SIZE)
            if not data: return
            
            request = Protocol.parse_request_packet(data)
            num_rounds = request["rounds"]
            client_name = request["client_name"]
            
            print(f"Starting {num_rounds} rounds with {client_name}")

            for _ in range(num_rounds):
                self.play_round(sock)
                # Brief pause between rounds to let the TCP buffer clear
                time.sleep(0.1)

            # --- THE FIX ---
            # Give the client a full second to receive and print the final 
            # Round 5 result before we destroy the socket object.
            print(f"Finished rounds for {client_name}. Cleaning up...")
            time.sleep(1.5) 

        except (ConnectionResetError, BrokenPipeError):
            print(f"Client {client_name} disconnected abruptly.")
        except Exception as e:
            print(f"Error handling {client_name}: {e}")
        finally:
            try:
                # Tell the client we are done sending, but stay open for a moment
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            sock.close()
            print(f"Socket for {client_name} closed safely.")

    # Play one round
    def play_round(self, sock: socket.socket):
        sock.settimeout(None) 
        game = BlackjackRound()
        game.initial_deal()
        
        # 1. Initial 3 cards
        for c in [game.player_hand.cards[0], game.player_hand.cards[1], game.dealer_hand.cards[0]]:
            sock.sendall(Protocol.build_payload_packet(b"\x00"*5, Protocol.ROUND_NOT_OVER, c.rank, c.suit))

        # 2. Player Turn
        while not game.finished:
            data = sock.recv(Protocol.PAYLOAD_SIZE)
            if not data:
                return

            payload = Protocol.parse_payload_packet(data)

            if payload["decision"] == "Hittt":
                game.player_hit()
                c = game.player_hand.cards[-1]
                sock.sendall(
                    Protocol.build_payload_packet(b"\x00"*5, Protocol.ROUND_NOT_OVER, c.rank, c.suit)
                )

                if game.player_hand.is_bust():
                    break

            else:
                game.player_stand()
                break

            try:
                data = sock.recv(Protocol.PAYLOAD_SIZE)
                if not data: return
                payload = Protocol.parse_payload_packet(data)
                
                if payload["decision"] == "Hittt":
                    game.player_hit()
                    # We ONLY send the card here. We don't send the result yet.
                    c = game.player_hand.cards[-1]
                    sock.sendall(Protocol.build_payload_packet(b"\x00"*5, Protocol.ROUND_NOT_OVER, c.rank, c.suit))
                else: 
                    game.player_stand()
                    break
            except:
                return
        
        # 3. Dealer Reveal (Crucial: Always send these!)
        # Send the hidden card and any hits the dealer took
        for i in range(1, len(game.dealer_hand.cards)):
            c = game.dealer_hand.cards[i]
            sock.sendall(
                Protocol.build_payload_packet(b"\x00"*5, Protocol.ROUND_NOT_OVER, c.rank, c.suit)
            )

        # 4. Final Result (Rank 0, Suit 0)
        # This is the "End of Round" signal the client is waiting for
        result_code = Protocol.result_to_code(game.result())
        sock.sendall(
            Protocol.build_payload_packet(b"\x00"*5, result_code, 0, 0)
        )

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