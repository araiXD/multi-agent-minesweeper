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

import random
from board import Board
from solver import Solver, Move

# Cap on candidates evaluated per turn in battle mode — bounds CSP calls
MAX_BATTLE_CANDIDATES = 5


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
        if self.strategy == "random":
            covered = board.get_covered_cells()
            if covered:
                r, c = random.choice(covered)
                return (r, c, "reveal")
            # Fallback: nothing covered, let solver handle it
            return Solver(board).get_moves()[0]

        solver = Solver(board)

        if self.strategy == "tier1":
            candidates = solver.tier1()
            if not candidates:
                # Tier 1 only — fall back to a random covered cell rather
                # than running CSP, since strategy intentionally limits depth
                covered = board.get_covered_cells()
                if covered:
                    r, c = random.choice(covered)
                    return (r, c, "reveal")
                candidates = solver.tier3()
        else:
            # Full CSP strategy
            candidates = solver.get_moves()

        # Solo mode — just return the first candidate
        if not battle_mode:
            return candidates[0]

        # Battle mode — skip evaluation if only one option
        if len(candidates) == 1:
            return candidates[0]

        # Evaluate at most MAX_BATTLE_CANDIDATES to bound CSP calls per turn
        if len(candidates) > MAX_BATTLE_CANDIDATES:
            candidates = candidates[:MAX_BATTLE_CANDIDATES]

        # Score every candidate and pick the best
        best_move = None
        best_score = float("-inf")
        scores = {}

        for move in candidates:
            s = self.evaluate_move(board, move, opponent_score)
            scores[move] = s
            if s > best_score:
                best_score = s
                best_move = move

        return best_move

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
        row, col, action = move

        # Simulate the move on a copy
        sim = board.copy()

        if action == "flag":
            sim.flag(row, col)
            # Flagging a confirmed mine: immediate +1 point + extra-turn advantage
            immediate = 2.0
        else:
            result = sim.reveal(row, col)
            if result == "mine":
                immediate = -1.0
            else:
                immediate = 0.0

        ambiguity = self._count_opponent_ambiguity(sim)
        mine_risk  = self._opponent_mine_risk(sim)

        return immediate + ambiguity * 0.5 + mine_risk * 1.5

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
        solver = Solver(simulated_board)
        certain_moves = solver.tier1()

        # Certain cells are those Tier 1 can resolve; everything else on the
        # frontier is ambiguous from the opponent's perspective.
        certain_cells = {(r, c) for r, c, _ in certain_moves}

        frontier_cells = set()
        for r, c in simulated_board.get_revealed_border():
            for cell in simulated_board.get_covered_neighbors(r, c):
                frontier_cells.add(cell)

        return len(frontier_cells - certain_cells)

    def _opponent_mine_risk(self, simulated_board: Board) -> float:
        """
        Estimate the probability that the opponent's best available move
        (their lowest-risk Tier 3 guess) still hits a mine.

        Args:
            simulated_board: board state after the move is applied

        Returns:
            Float probability 0.0–1.0.
        """
        # If there are no covered cells the game is effectively over
        covered = simulated_board.get_covered_cells()
        if not covered:
            return 0.0

        # Use the global baseline (remaining_mines / remaining_covered) instead
        # of running a full CSP on the simulated board — cheap and good enough
        # for an adversarial heuristic that is already an approximation.
        remaining = simulated_board.remaining_mines()
        if remaining <= 0:
            return 0.0

        # The opponent will pick the cell with the lowest mine probability.
        # That minimum probability IS their chance of hitting a mine.
        return remaining / len(covered)

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
        self.moves_made += 1
        if result == "flag":
            self.score += 1
        elif result == "mine":
            self.score -= 1
            self.mines_hit += 1

    def __repr__(self) -> str:
        return f"Agent {self.agent_id} | Score: {self.score} | Hits: {self.mines_hit} | Moves: {self.moves_made}"
