import socket
import struct
import time

MAGIC_COOKIE = 0xabcddcba
UDP_PORT = 13117 
PAYLOAD_FORMAT = "!IB5sBHB"
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)

RANKS = {1: 'A', 11: 'J', 12: 'Q', 13: 'K'}
SUITS = {0: 'H', 1: 'D', 2: 'C', 3: 'S'}

class BlackjackClient:
    def __init__(self, team_name="Team Joker"):
        self.team_name = team_name
        self.wins = 0

    def start(self):
        print("Client started, listening for offer requests...")
        while True:
            try:
                server_ip, tcp_port = self.listen_for_offer()
                self.play_game(server_ip, tcp_port)
            except Exception as e:
                print(f"Connection lost or Error: {e}")
                time.sleep(1)

    def listen_for_offer(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', 13117)) 
            while True:
                data, addr = s.recvfrom(1024)
                if len(data) >= 39:
                    cookie, msg_type, port, name = struct.unpack("!IBH32s", data[:39])
                    if cookie == MAGIC_COOKIE and msg_type == 0x2:
                        print(f"Received offer from {addr[0]}")
                        return addr[0], port

    def play_game(self, ip, port):
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            tcp_sock.connect((ip, port))
            
            rounds_input = input("Enter number of rounds to play: ")
            num_rounds = int(rounds_input)
            
            name_bytes = self.team_name.encode().ljust(32, b'\x00')
            request_pkt = struct.pack("!IBB32s", MAGIC_COOKIE, 0x3, num_rounds, name_bytes)
            tcp_sock.sendall(request_pkt)

            for r in range(num_rounds):
                print(f"\n--- Round {r+1} ---")
                success = self.handle_round(tcp_sock)
                if not success:
                    print("Connection lost during round.")
                    break
            
            print(f"\nFinished playing {num_rounds} rounds. Wins: {self.wins}")

        except Exception as e:
            print(f"\nGame Error: {e}")
        finally:
            try:
                tcp_sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            tcp_sock.close()

    def get_value(self, rank):
        if rank >= 10: 
            return 10
        return rank

    def handle_round(self, sock):
        has_stood = False
        player_sum = 0
        cards_received = 0

        while True:
            data = self.recv_all(sock, PAYLOAD_SIZE)
            if not data:
                return False 

            cookie, msg_type, _, result, rank, suit = struct.unpack(
                PAYLOAD_FORMAT, data
            )

            if rank == 0:
                res_map = {0x1: "TIE", 0x2: "LOSS", 0x3: "WIN"}
                print(f"--- Round Result: {res_map.get(result, '???')} ---")

                if result == 0x3:
                    self.wins += 1

                return True

            cards_received += 1

            r_name = RANKS.get(rank, str(rank))
            s_name = SUITS.get(suit, "")

            if not has_stood and cards_received != 3:
                card_value = rank if rank < 10 else 10
                player_sum += card_value
                print(f"Card dealt: {r_name}{s_name} (Total: {player_sum})")
            else:
                print(f"Dealer dealt: {r_name}{s_name}")

            if cards_received >= 3 and not has_stood:

                if player_sum >= 21:
                    has_stood = True
                    continue

                choice = input("Your turn - (h)it or (s)tand? ").lower()

                if choice == 'h':
                    decision = b"Hittt"
                else:
                    decision = b"Stand"
                    has_stood = True

                sock.sendall(
                    struct.pack(
                        PAYLOAD_FORMAT,
                        MAGIC_COOKIE,
                        0x4,
                        decision,
                        0, 0, 0
                    )
                )


    def recv_all(self, sock, n):
        data = b''
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet: 
                    return None
                data += packet
            except Exception:
                return None
        return data

if __name__ == "__main__":
    client = BlackjackClient(team_name="AceSpades")
    client.start()