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
        self.flags = 0
        self.reveals = 0

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def choose_move(self, board: Board, battle_mode: bool = False, opponent_score: int = 0) -> Move:
        """
        Choose the next move given the current board state.

        In solo mode (battle_mode=False):
            Delegates directly to solver.get_moves() and returns the first move.

        In battle mode (battle_mode=True):
            Gets candidate moves from solver, then runs Minimax with Alpha-Beta
            pruning to pick the move that maximizes own advantage while minimizing
            the opponent's best response.

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
            return Solver(board).get_moves()[0]

        solver = Solver(board)

        if self.strategy == "tier1":
            candidates = solver.tier1()
            if not candidates:
                covered = board.get_covered_cells()
                if covered:
                    r, c = random.choice(covered)
                    return (r, c, "reveal")
                candidates = solver.tier3()
        else:
            candidates = solver.get_moves()

        if not battle_mode or len(candidates) == 1:
            return candidates[0]

        if len(candidates) > MAX_BATTLE_CANDIDATES:
            candidates = candidates[:MAX_BATTLE_CANDIDATES]

        # ------------------------------------------------------------------
        # Root of Minimax with Alpha-Beta Pruning
        # ------------------------------------------------------------------
        best_move = None
        best_score = float("-inf")
        alpha = float("-inf")
        beta = float("inf")

        for move in candidates:
            sim = board.copy()
            r, c, action = move
            my_score = self.score
            extra_turn = False

            if action == "flag":
                sim.flag(r, c)
                my_score += 1
                extra_turn = True
            else:
                if sim.reveal(r, c) == "mine":
                    my_score -= 1

            # If we flag a mine, we get an extra turn, so we maximize again.
            # Otherwise, hand off to opponent (minimize).
            score = self._alphabeta(
                sim,
                depth=2,
                alpha=alpha,
                beta=beta,
                maximizing_player=extra_turn,
                my_score=my_score,
                op_score=opponent_score,
            )

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, best_score)

        return best_move if best_move else candidates[0]

    # ------------------------------------------------------------------
    # Battle mode — Minimax with Alpha-Beta Pruning
    # ------------------------------------------------------------------

    def _alphabeta(self, board: Board, depth: int, alpha: float, beta: float,
                   maximizing_player: bool, my_score: int, op_score: int) -> float:
        """
        Minimax search tree with Alpha-Beta pruning.
        Explores future game states by simulating candidate moves generated by the CSP solver.
        """
        if depth == 0 or board.game_over:
            return self._static_eval(board, my_score, op_score)

        solver = Solver(board)
        candidates = solver.get_moves()[:MAX_BATTLE_CANDIDATES]

        if not candidates:
            return self._static_eval(board, my_score, op_score)

        if maximizing_player:
            max_eval = float("-inf")
            for move in candidates:
                sim = board.copy()
                r, c, action = move
                next_score = my_score
                extra_turn = False

                if action == "flag":
                    sim.flag(r, c)
                    next_score += 1
                    extra_turn = True
                else:
                    if sim.reveal(r, c) == "mine":
                        next_score -= 1

                eval_score = self._alphabeta(sim, depth - 1, alpha, beta, extra_turn, next_score, op_score)
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Beta cut-off
            return max_eval

        else:
            min_eval = float("inf")
            for move in candidates:
                sim = board.copy()
                r, c, action = move
                next_op_score = op_score
                extra_turn = False

                if action == "flag":
                    sim.flag(r, c)
                    next_op_score += 1
                    extra_turn = True
                else:
                    if sim.reveal(r, c) == "mine":
                        next_op_score -= 1

                # If opponent gets an extra turn, they maximize again (so we stay in minimize mode).
                eval_score = self._alphabeta(sim, depth - 1, alpha, beta, not extra_turn, my_score, next_op_score)
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha cut-off
            return min_eval

    def _static_eval(self, board: Board, my_score: int, op_score: int) -> float:
        """Leaf node evaluation for Minimax."""
        score_diff = (my_score - op_score) * 10.0
        ambiguity = self._count_opponent_ambiguity(board) * 0.5
        mine_risk = self._opponent_mine_risk(board) * 1.5
        return score_diff + ambiguity + mine_risk

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
            self.flags += 1
        elif result == "mine":
            self.score -= 1
            self.mines_hit += 1
        elif result == "reveal":
            self.reveals += 1

    def __repr__(self) -> str:
        return f"Agent {self.agent_id} | Score: {self.score} | Hits: {self.mines_hit} | Moves: {self.moves_made}"
