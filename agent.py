"""
agent.py — Agent class wrapping the solver with Battle mode strategy

In solo mode, the agent just asks the solver for the best move and executes it.

In Battle mode, the agent has a second layer of reasoning on top of the solver:
given multiple valid moves (especially in Tier 1/2 where several safe cells
may be available), it uses a heuristic evaluation function to pick the move
that best degrades the opponent's position — not just the one that's safest
for itself.

The agent never directly modifies the Board. It returns a chosen Move and
the battle loop applies it.
"""

from board import Board
from solver import Solver, Move


class Agent:
    def __init__(self, agent_id: int, strategy: str = "csp"):
        """
        Args:
            agent_id: 1 or 2, used for scoring and display
            strategy:
                "csp"      — full three-tier solver (default)
                "tier1"    — deterministic rules only, no CSP (weaker, faster)
                "random"   — random covered cell (baseline for benchmarking)
        """
        self.agent_id = agent_id
        self.strategy = strategy
        self.score = 0
        self.mines_hit = 0
        self.moves_made = 0

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def choose_move(self, board: Board, battle_mode: bool = False, opponent_score: int = 0) -> Move:
        """
        Choose the next move given the current board state.

        In solo mode (battle_mode=False):
            Delegates directly to solver.get_moves() and returns the first move.

        In battle mode (battle_mode=True):
            Gets candidate moves from solver, then runs evaluate_move() on
            each to pick the one that maximizes own advantage and minimizes
            opponent's next-turn options.

        Args:
            board: current game state (read-only)
            battle_mode: whether adversarial evaluation is active
            opponent_score: opponent's current score (used in eval function)

        Returns:
            A single Move tuple (row, col, action).
        """
        pass

    # ------------------------------------------------------------------
    # Battle mode — adversarial evaluation
    # ------------------------------------------------------------------

    def evaluate_move(self, board: Board, move: Move, opponent_score: int) -> float:
        """
        Score a candidate move from an adversarial perspective.

        Heuristic considers:
          (a) Immediate score delta for this agent (flagging a mine = +1 point
              and extra turn, revealing safe = 0, hitting mine = -1)
          (b) Number of non-deterministic cells the opponent will face after
              this move is applied — more ambiguity for opponent is better
          (c) Probability that the opponent's best available next move
              results in hitting a mine

        Uses board.copy() to simulate the move without mutating real state.

        Args:
            board: current board state
            move: candidate move to evaluate
            opponent_score: opponent's current score

        Returns:
            Float score — higher is better for this agent.
        """
        pass

    def _count_opponent_ambiguity(self, simulated_board: Board) -> int:
        """
        After simulating a move, count how many covered cells the opponent
        cannot determine with certainty using Tier 1 alone. Higher = better
        for this agent.

        Args:
            simulated_board: board state after the move is applied

        Returns:
            Integer count of non-deterministic frontier cells.
        """
        pass

    def _opponent_mine_risk(self, simulated_board: Board) -> float:
        """
        Estimate the probability that the opponent's best available move
        (their lowest-risk Tier 3 guess) still hits a mine.

        Args:
            simulated_board: board state after the move is applied

        Returns:
            Float probability 0.0–1.0.
        """
        pass

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def apply_result(self, result: str):
        """
        Update agent stats after a move is executed.

        Args:
            result: "flag"  — successfully flagged a mine (+1 point, extra turn)
                    "reveal" — safe cell revealed (no point change)
                    "mine"  — hit a mine (-1 point, turn ends)
        """
        pass

    def __repr__(self) -> str:
        return f"Agent {self.agent_id} | Score: {self.score} | Hits: {self.mines_hit} | Moves: {self.moves_made}"
