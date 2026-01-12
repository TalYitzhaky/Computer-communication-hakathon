import socket
import struct
import time
import sys

MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13122 
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

# Card Mapping
SUITS = {0: 'H', 1: 'D', 2: 'C', 3: 'S'}
RANKS = {1: 'A', 11: 'J', 12: 'Q', 13: 'K'}

class BlackjackClient:
    def __init__(self, team_name="Team Joker"):
        self.team_name = team_name
        self.wins = 0
        self.total_rounds = 0

    def start(self):
        print("Client started, listening for offer requests...")
        while True:
            try:
                server_ip, tcp_port = self.listen_for_offer()
                print(f"Received offer from {server_ip}")

                self.play_game(server_ip, tcp_port)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

    def listen_for_offer(self):
        """Listens for UDP broadcast offers from servers."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            
            s.bind(('', UDP_PORT))
            
            while True:
                data, addr = s.recvfrom(1024)
                if len(data) < 39: continue
                
                cookie, msg_type, port = struct.unpack('!IbH', data[:7])
                if cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
                    return addr[0], port

    def play_game(self, ip, port):
        """Handles the TCP game logic."""
        num_rounds = int(input("Enter number of rounds to play: "))
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
            tcp_sock.connect((ip, port))
            
            request_pkt = struct.pack('!IbB32s', MAGIC_COOKIE, REQUEST_TYPE, num_rounds, self.team_name.encode().ljust(32, b'\x00'))
            tcp_sock.sendall(request_pkt)

            for r in range(num_rounds):
                print(f"\n--- Round {r+1} ---")
                self.handle_round(tcp_sock)
            
            win_rate = (self.wins / num_rounds) * 100 if num_rounds > 0 else 0
            print(f"\nFinished playing {num_rounds} rounds, win rate: {win_rate}%")

    def handle_round(self, sock):
        """Manages the Hit/Stand cycle and result for a single round."""
        while True:
            data = sock.recv(1024)
            if not data: break
            
            cookie, msg_type, _, result, rank, suit = struct.unpack('!Ib5sB2sB', data[:13])
            
            if cookie != MAGIC_COOKIE: continue

            rank_val = int.from_bytes(rank, 'big')
            card_str = f"{RANKS.get(rank_val, rank_val)}{SUITS.get(suit, '?')}"
            print(f"Card drawn: {card_str}")

            if result == 0x0:
                choice = ""
                while choice not in ['h', 's']:
                    choice = input("Hit (h) or Stand (s)? ").lower()
                
                decision = "Hittt" if choice == 'h' else "Stand"
                payload = struct.pack('!Ib5sB3s', MAGIC_COOKIE, PAYLOAD_TYPE, decision.encode(), 0, b'\x00\x00\x00')
                sock.sendall(payload)
                
                if choice == 's': 
                    continue
            else:
                if result == 0x3:
                    print("Result: YOU WIN!")
                    self.wins += 1
                elif result == 0x2:
                    print("Result: YOU LOSE!")
                else:
                    print("Result: TIE!")
                break

if __name__ == "__main__":
    client = BlackjackClient(team_name="AceSpades")
    client.start()