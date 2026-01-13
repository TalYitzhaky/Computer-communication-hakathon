import struct

class Protocol:
    # Protocol constants
    MAGIC_COOKIE = 0xabcddcba

    # Message types
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4

    # Round results (server -> client)
    ROUND_NOT_OVER = 0x0
    TIE = 0x1
    LOSS = 0x2
    WIN = 0x3

    # Decisions (client -> server)
    HIT = b"Hittt"
    STAND = b"Stand"

    # Struct formats
    OFFER_FORMAT = "!IBH32s"
    REQUEST_FORMAT = "!IBB32s"
    PAYLOAD_FORMAT = "!IB5sBHB"

    OFFER_SIZE = struct.calcsize(OFFER_FORMAT)
    REQUEST_SIZE = struct.calcsize(REQUEST_FORMAT)
    PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)

    # Helper methods
    @staticmethod
    def _encode_name(name: str) -> bytes:
        """
        Encode a team/server name to exactly 32 bytes.
        """
        encoded = name.encode("utf-8")
        return encoded[:32].ljust(32, b"\x00")

    @staticmethod
    def _decode_name(raw: bytes) -> str:
        """
        Decode a 32-byte padded name into a Python string.
        """
        return raw.rstrip(b"\x00").decode("utf-8")

    @staticmethod
    def _validate_cookie_and_type(cookie, msg_type, expected_type):
        """
        Validate magic cookie and message type.
        """
        if cookie != Protocol.MAGIC_COOKIE:
            raise ValueError("Invalid magic cookie")
        if msg_type != expected_type:
            raise ValueError("Invalid message type")

    # OFFER packet (server -> client, UDP)
    @staticmethod
    def build_offer_packet(tcp_port: int, server_name: str) -> bytes:
        """
        Build an OFFER packet to broadcast via UDP.
        """
        name_bytes = Protocol._encode_name(server_name)

        return struct.pack(
            Protocol.OFFER_FORMAT,
            Protocol.MAGIC_COOKIE,
            Protocol.OFFER,
            tcp_port,
            name_bytes
        )

    @staticmethod
    def parse_offer_packet(data: bytes) -> dict:
        """
        Parse an OFFER packet received via UDP.
        """
        if len(data) != Protocol.OFFER_SIZE:
            raise ValueError("Invalid offer packet size")

        cookie, msg_type, tcp_port, raw_name = struct.unpack(
            Protocol.OFFER_FORMAT, data
        )

        Protocol._validate_cookie_and_type(cookie, msg_type, Protocol.OFFER)

        return {
            "tcp_port": tcp_port,
            "server_name": Protocol._decode_name(raw_name)
        }

    # REQUEST packet (client -> server, TCP)
    @staticmethod
    def parse_request_packet(data: bytes) -> dict:
        """
        Parse a REQUEST packet received from a client.
        """
        if len(data) != Protocol.REQUEST_SIZE:
            raise ValueError("Invalid request packet size")

        cookie, msg_type, rounds, raw_name = struct.unpack(
            Protocol.REQUEST_FORMAT, data
        )

        Protocol._validate_cookie_and_type(cookie, msg_type, Protocol.REQUEST)

        if rounds <= 0:
            raise ValueError("Invalid number of rounds")

        return {
            "rounds": rounds,
            "client_name": Protocol._decode_name(raw_name)
        }

    # PAYLOAD packet (both directions, TCP)
    @staticmethod
    def build_payload_packet(
        decision: bytes = b"\x00" * 5,
        result: int = ROUND_NOT_OVER,
        rank: int = 0,
        suit: int = 0
    ) -> bytes:
        """
        Build a PAYLOAD packet.
        """
        if len(decision) != 5:
            raise ValueError("Decision must be exactly 5 bytes")

        return struct.pack(
            Protocol.PAYLOAD_FORMAT,
            Protocol.MAGIC_COOKIE,
            Protocol.PAYLOAD,
            decision,
            result,
            rank,
            suit
        )

    @staticmethod
    def parse_payload_packet(data: bytes) -> dict:
        """
        Parse a PAYLOAD packet.
        """
        if len(data) != Protocol.PAYLOAD_SIZE:
            raise ValueError("Invalid payload packet size")

        cookie, msg_type, decision, result, rank, suit = struct.unpack(
            Protocol.PAYLOAD_FORMAT, data
        )

        Protocol._validate_cookie_and_type(cookie, msg_type, Protocol.PAYLOAD)

        return {
            "decision": decision,
            "result": result,
            "rank": rank,
            "suit": suit
        }
        
    @staticmethod
    def result_to_code(result: str) -> int:
        if result == "win":
            return Protocol.WIN
        if result == "loss":
            return Protocol.LOSS
        if result == "tie":
            return Protocol.TIE
        return Protocol.ROUND_NOT_OVER