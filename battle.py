"""
battle.py — Two-agent adversarial game loop

Manages turn structure, scoring, win conditions, and the overall
flow of a Minesweeper Battle game between two agents.

Turn rules:
  - Agents alternate turns
  - Correctly flagging a mine earns +1 point AND an extra turn
  - Hitting a mine costs -1 point and ends the turn (mine is revealed)
  - Revealing a safe cell ends the turn (no point change)
  - Game ends when all mines are flagged or no covered cells remain

The battle loop is decoupled from the GUI — it emits game events
that gui.py listens to and renders. Can also run headless for benchmarking.
"""

from board import Board
from agent import Agent


class BattleGame:
    def __init__(self, board: Board, agent1: Agent, agent2: Agent, headless: bool = False):
        """
        Args:
            board: initialized Board (mines not yet placed)
            agent1: first agent (goes first)
            agent2: second agent
            headless: if True, skip GUI callbacks (for batch benchmarking)
        """
        self.board = board
        self.agents = [agent1, agent2]
        self.current = 0       # index into self.agents, 0 or 1
        self.headless = headless
        self.turn_count = 0
        self.game_over = False
        self.winner = None
        self.history = []      # list of GameEvent dicts for replay/logging

        # GUI callback hooks — set by gui.py if not headless
        self.on_move = None    # callable(event) called after each move
        self.on_game_over = None  # callable(winner) called at game end

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def start(self, first_reveal_row: int, first_reveal_col: int):
        """
        Kick off the game. Places mines (safe around first reveal),
        makes the first reveal, then hands off to run_turn().

        Args:
            first_reveal_row, first_reveal_col: agent1's opening move.
            In Battle mode, agent1 always makes the first reveal for free
            (no score implications, just opens the board).
        """
        pass

    def run_turn(self):
        """
        Execute one full turn for the current agent.

        Flow:
          1. Ask current agent for a move via agent.choose_move()
          2. Apply move to board
          3. Evaluate result (flag hit, safe reveal, mine hit)
          4. Update agent score via agent.apply_result()
          5. Emit event to history and GUI callback
          6. If agent flagged a mine → agent gets extra turn (don't advance current)
          7. Else → advance to next agent
          8. Check win/end conditions
        """
        pass

    def run_all(self):
        """
        Run the full game to completion (used in headless/benchmark mode).
        Loops run_turn() until self.game_over.
        """
        pass

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    def advance_turn(self):
        """Switch to the other agent and increment turn counter."""
        pass

    def current_agent(self) -> Agent:
        """Return the Agent whose turn it currently is."""
        pass

    def other_agent(self) -> Agent:
        """Return the Agent who is waiting."""
        pass

    # ------------------------------------------------------------------
    # Win / end conditions
    # ------------------------------------------------------------------

    def check_end(self) -> bool:
        """
        Check if the game is over.

        End conditions:
          - All mines have been flagged
          - No covered cells remain
          - (Optional) Turn limit reached

        Sets self.game_over and self.winner, returns True if game ended.
        """
        pass

    def determine_winner(self) -> Agent | None:
        """
        Compare scores. Returns winning Agent or None if tied.
        """
        pass

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def emit_event(self, event: dict):
        """
        Log event to self.history and fire GUI callback if set.

        Event dict structure:
        {
            "type":    "reveal" | "flag" | "mine_hit" | "game_over",
            "agent":   agent_id (1 or 2),
            "row":     int,
            "col":     int,
            "result":  "safe" | "mine" | "flag",
            "score1":  int,
            "score2":  int,
            "turn":    int
        }
        """
        pass

    # ------------------------------------------------------------------
    # Benchmarking helpers
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """
        Return end-of-game stats dict for batch benchmarking.

        Returns:
        {
            "winner":       agent_id or None (tie),
            "score1":       int,
            "score2":       int,
            "turns":        int,
            "mines_hit1":   int,
            "mines_hit2":   int,
            "moves1":       int,
            "moves2":       int,
        }
        """
        pass
