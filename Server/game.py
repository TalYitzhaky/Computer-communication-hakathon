import random

class Card:
    """
    Represents a single playing card.
    """

    SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
    RANK_NAMES = {
        1: "A",
        11: "J",
        12: "Q",
        13: "K"
    }

    def __init__(self, rank: int, suit: int):
        if not (1 <= rank <= 13):
            raise ValueError("Rank must be between 1 and 13")
        if not (0 <= suit <= 3):
            raise ValueError("Suit must be between 0 and 3")

        self.rank = rank
        self.suit = suit

    @property
    def value(self) -> int:
        """
        Blackjack value of the card.
        Ace = 1, Face cards = 10.
        """
        if self.rank == 1:
            return 1
        if self.rank >= 11:
            return 10
        return self.rank

    def __str__(self):
        rank = self.RANK_NAMES.get(self.rank, str(self.rank))
        return f"{rank} of {self.SUITS[self.suit]}"


class Deck:
    """
    Represents a standard shuffled 52-card deck.
    """

    def __init__(self):
        self.cards = []
        self._build()
        self.shuffle()

    def _build(self):
        """
        Create a fresh 52-card deck.
        """
        self.cards.clear()
        for suit in range(4):
            for rank in range(1, 14):
                self.cards.append(Card(rank, suit))

    def shuffle(self):
        """
        Shuffle the deck in place.
        """
        random.shuffle(self.cards)

    def draw(self) -> Card:
        """
        Draw the top card from the deck.
        """
        if not self.cards:
            raise RuntimeError("Deck is empty")
        return self.cards.pop()

class Hand:
    """
    Represents a blackjack hand.
    """

    def __init__(self):
        self.cards = []

    def add_card(self, card: Card):
        self.cards.append(card)

    @property
    def total(self) -> int:
        """
        Total blackjack value of the hand.
        """
        return sum(card.value for card in self.cards)

    def is_bust(self) -> bool:
        return self.total > 21

    def __str__(self):
        return ", ".join(str(card) for card in self.cards)

class BlackjackRound:
    """
    Encapsulates a single blackjack round.
    """

    def __init__(self):
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.finished = False

    def initial_deal(self):
        """
        Deal initial 2 cards to player and dealer.
        """
        self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())
        self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())

    # Player actions
    def player_hit(self) -> Card:
        """
        Player takes a hit.
        """
        if self.finished:
            raise RuntimeError("Round already finished")

        card = self.deck.draw()
        self.player_hand.add_card(card)

        if self.player_hand.is_bust():
            self.finished = True

        return card

    def player_stand(self):
        """
        Player stands, dealer's turn begins.
        """
        if self.finished:
            raise RuntimeError("Round already finished")

        self._dealer_turn()
        self.finished = True

    # Dealer logic
    def _dealer_turn(self):
        """
        Dealer draws until total >= 17 or busts.
        """
        while self.dealer_hand.total < 17:
            self.dealer_hand.add_card(self.deck.draw())

    # Result calculation
    def result(self) -> str:
        """
        Determine the round result.
        Returns: 'win', 'loss', or 'tie'
        """
        if self.player_hand.is_bust():
            return "loss"
        if self.dealer_hand.is_bust():
            return "win"

        if self.player_hand.total > self.dealer_hand.total:
            return "win"
        if self.player_hand.total < self.dealer_hand.total:
            return "loss"
        return "tie"
    

