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
        # First reveal seeds mine placement and opens the board — no scoring
        self.board.reveal(first_reveal_row, first_reveal_col)

        # Emit the free opening move as a neutral event
        self.emit_event({
            "type":   "reveal",
            "agent":  self.agents[0].agent_id,
            "row":    first_reveal_row,
            "col":    first_reveal_col,
            "result": "safe",
            "score1": self.agents[0].score,
            "score2": self.agents[1].score,
            "turn":   self.turn_count,
        })

        if not self.check_end():
            self.run_all()

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
        if self.game_over:
            return

        agent = self.current_agent()
        opponent = self.other_agent()
        move = agent.choose_move(
            self.board,
            battle_mode=True,
            opponent_score=opponent.score,
        )

        row, col, action = move
        extra_turn = False

        if action == "flag":
            placed = self.board.flag(row, col)
            if placed and self.board.mines[row, col] == 1:
                # Correctly flagged a mine
                agent.apply_result("flag")
                event_type = "flag"
                event_result = "flag"
                extra_turn = True
            else:
                # Flag placed on a safe cell (shouldn't happen with a good solver,
                # but handle gracefully — treat as a wasted move, turn advances)
                agent.apply_result("reveal")
                event_type = "flag"
                event_result = "safe"
        else:
            # action == "reveal"
            result = self.board.reveal(row, col)
            if result == "mine":
                agent.apply_result("mine")
                event_type = "mine_hit"
                event_result = "mine"
            else:
                agent.apply_result("reveal")
                event_type = "reveal"
                event_result = "safe"

        self.emit_event({
            "type":   event_type,
            "agent":  agent.agent_id,
            "row":    row,
            "col":    col,
            "result": event_result,
            "score1": self.agents[0].score,
            "score2": self.agents[1].score,
            "turn":   self.turn_count,
        })

        if self.check_end():
            return

        if not extra_turn:
            self.advance_turn()

    def run_all(self):
        """
        Run the full game to completion (used in headless/benchmark mode).
        Loops run_turn() until self.game_over.
        """
        while not self.game_over:
            self.run_turn()

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    def advance_turn(self):
        """Switch to the other agent and increment turn counter."""
        self.current = 1 - self.current
        self.turn_count += 1

    def current_agent(self) -> Agent:
        """Return the Agent whose turn it currently is."""
        return self.agents[self.current]

    def other_agent(self) -> Agent:
        """Return the Agent who is waiting."""
        return self.agents[1 - self.current]

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
        if self.game_over:
            return True

        flags_placed = int((self.board.visible == -2).sum())
        all_mines_flagged = flags_placed == self.board.num_mines
        no_covered_left = len(self.board.get_covered_cells()) == 0

        if all_mines_flagged or no_covered_left or self.board.game_over:
            self.game_over = True
            self.winner = self.determine_winner()
            self.emit_event({
                "type":   "game_over",
                "agent":  self.winner.agent_id if self.winner else None,
                "row":    -1,
                "col":    -1,
                "result": "game_over",
                "score1": self.agents[0].score,
                "score2": self.agents[1].score,
                "turn":   self.turn_count,
            })
            if self.on_game_over and not self.headless:
                self.on_game_over(self.winner)
            return True

        return False

    def determine_winner(self) -> Agent | None:
        """
        Compare scores. Returns winning Agent or None if tied.
        """
        s1 = self.agents[0].score
        s2 = self.agents[1].score
        if s1 > s2:
            return self.agents[0]
        if s2 > s1:
            return self.agents[1]
        return None

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
        self.history.append(event)
        if self.on_move and not self.headless and event["type"] != "game_over":
            self.on_move(event)

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
        return {
            "winner":     self.winner.agent_id if self.winner else None,
            "score1":     self.agents[0].score,
            "score2":     self.agents[1].score,
            "turns":      self.turn_count,
            "mines_hit1": self.agents[0].mines_hit,
            "mines_hit2": self.agents[1].mines_hit,
            "moves1":     self.agents[0].moves_made,
            "moves2":     self.agents[1].moves_made,
        }
