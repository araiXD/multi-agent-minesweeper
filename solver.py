"""
solver.py — Three-tier Minesweeper solver

Tiers are applied in order. Each tier returns a list of moves.
If Tier 1 finds moves, Tier 2 and 3 are skipped.
If Tier 2 finds moves, Tier 3 is skipped.
Tier 3 always returns exactly one move (a best guess).

A Move is a (row, col, action) tuple where action is "reveal" or "flag".

The solver is stateless — it takes a Board and returns moves.
It never modifies the Board directly.
"""

from collections import defaultdict
from board import Board


# Type alias for clarity
Move = tuple[int, int, str]  # (row, col, "reveal" | "flag")

# Backtracking performance caps
MAX_SOLUTIONS = 200       # stop collecting solutions after this many
MAX_COMPONENT_SIZE = 20   # skip Tier 2 for components larger than this


class Solver:
    def __init__(self, board: Board):
        """
        Args:
            board: the current game Board (read-only from solver's perspective)
        """
        self.board = board

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def get_moves(self) -> list[Move]:
        """
        Run all three tiers in order and return the best available moves.
        Tiers are short-circuited: if a higher tier finds moves, lower
        tiers are not run.

        Returns:
            List of Move tuples. May be multiple (all safe flags/reveals
            found). Never empty — Tier 3 always provides a fallback.
        """
        moves = self.tier1()
        if moves:
            return moves
        moves = self.tier2()
        if moves:
            return moves
        return self.tier3()

    # ------------------------------------------------------------------
    # Tier 1 — Deterministic single-cell rules
    # ------------------------------------------------------------------

    def tier1(self) -> list[Move]:
        """
        For each revealed border cell with value n:
          - If n == flagged_neighbors: all covered neighbors are safe → reveal them
          - If n == covered_neighbors + flagged_neighbors: all covered neighbors are mines → flag them

        Fast O(n^2), always correct, handles the majority of moves.

        Returns:
            List of moves if any found, else empty list.
        """
        moves = []
        seen = set()  # deduplicate: a cell can border multiple revealed cells

        for r, c in self.board.get_revealed_border():
            n = int(self.board.visible[r, c])
            flagged = self.board.get_flagged_neighbors(r, c)
            covered = self.board.get_covered_neighbors(r, c)

            if n == len(flagged):
                # All mines accounted for — every covered neighbor is safe
                for cell in covered:
                    if cell not in seen:
                        seen.add(cell)
                        moves.append((cell[0], cell[1], "reveal"))

            elif n == len(covered) + len(flagged):
                # Every covered neighbor must be a mine
                for cell in covered:
                    if cell not in seen:
                        seen.add(cell)
                        moves.append((cell[0], cell[1], "flag"))

        return moves

    # ------------------------------------------------------------------
    # Tier 2 — CSP with backtracking search
    # ------------------------------------------------------------------

    def tier2(self) -> list[Move]:
        """
        Model the frontier as a CSP:
          - Variables: covered, unflagged cells adjacent to revealed numbers
          - Constraints: for each revealed cell, sum of neighboring variables == n - flagged_neighbors

        Steps:
          1. Build constraint list from frontier
          2. Partition constraints into connected components (cells that
             share variables are in the same component)
          3. Run backtracking search per component to enumerate all solutions
          4. Any cell that is 0 in ALL solutions → safe to reveal
             Any cell that is 1 in ALL solutions → safe to flag

        Returns:
            List of moves if any certain moves found, else empty list.
        """
        constraints = self._build_constraints()
        if not constraints:
            return []

        components = self._get_connected_components(constraints)
        moves = []
        seen = set()

        for component in components:
            variables = list({cell for c in component for cell in c["cells"]})
            if not variables:
                continue

            if len(variables) > MAX_COMPONENT_SIZE:
                continue  # too large — let Tier 3 handle probabilistically

            solutions = []
            self._backtrack(component, variables, {}, solutions)

            if not solutions:
                continue

            num_solutions = len(solutions)
            for cell in variables:
                mine_count = sum(sol[cell] for sol in solutions)
                if mine_count == 0 and cell not in seen:
                    seen.add(cell)
                    moves.append((cell[0], cell[1], "reveal"))
                elif mine_count == num_solutions and cell not in seen:
                    seen.add(cell)
                    moves.append((cell[0], cell[1], "flag"))

        return moves

    def _build_constraints(self) -> list[dict]:
        """
        Build constraint list from the current board frontier.

        Each constraint is:
        {
            "cells": frozenset of (row, col) tuples,
            "count": int  (number of mines among these cells)
        }

        Returns:
            List of constraint dicts.
        """
        constraints = []
        seen_cells = set()  # deduplicate constraints with identical cell sets

        for r, c in self.board.get_revealed_border():
            n = int(self.board.visible[r, c])
            flagged = self.board.get_flagged_neighbors(r, c)
            covered = self.board.get_covered_neighbors(r, c)

            cells = frozenset(covered)
            mine_count = n - len(flagged)

            if not cells or cells in seen_cells:
                continue
            seen_cells.add(cells)

            constraints.append({"cells": cells, "count": mine_count})

        return constraints

    def _get_connected_components(self, constraints: list[dict]) -> list[list[dict]]:
        """
        Partition constraints into groups where constraints in the same
        group share at least one variable (cell). Allows us to solve
        each independent subproblem separately — huge speedup.

        Args:
            constraints: full list of constraints from _build_constraints()

        Returns:
            List of constraint groups (each group is a list of constraints).
        """
        n = len(constraints)
        if n == 0:
            return []

        # Map each cell to the constraint indices that reference it
        cell_to_indices = defaultdict(list)
        for i, c in enumerate(constraints):
            for cell in c["cells"]:
                cell_to_indices[cell].append(i)

        # Union-Find over constraint indices
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # path compression
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for indices in cell_to_indices.values():
            for i in range(1, len(indices)):
                union(indices[0], indices[i])

        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(constraints[i])

        return list(groups.values())

    def _backtrack(self, constraints: list[dict], variables: list, assignment: dict, solutions: list):
        """
        Recursive backtracking search. Enumerates all valid assignments
        of 0/1 to variables that satisfy all constraints.

        Args:
            constraints: constraints for this connected component
            variables: list of unassigned (row, col) cells
            assignment: current partial assignment {(row,col): 0 or 1}
            solutions: accumulator list — each valid complete assignment appended here
        """
        if len(solutions) >= MAX_SOLUTIONS:
            return

        if not variables:
            # All assigned — verify every constraint is exactly met
            for c in constraints:
                if sum(assignment[cell] for cell in c["cells"]) != c["count"]:
                    return
            solutions.append(dict(assignment))
            return

        var = variables[0]
        rest = variables[1:]

        for val in (0, 1):
            assignment[var] = val
            if self._is_consistent(constraints, assignment):
                self._backtrack(constraints, rest, assignment, solutions)
            del assignment[var]

    def _is_consistent(self, constraints: list[dict], assignment: dict) -> bool:
        """
        Check whether the current partial assignment violates any constraint.
        A constraint is violated if:
          - assigned mines already exceed its count, or
          - remaining unassigned cells can't possibly fill the mine count

        Args:
            constraints: constraints to check against
            assignment: current partial assignment

        Returns:
            True if consistent, False if violated.
        """
        for c in constraints:
            assigned_mines = sum(
                assignment[cell] for cell in c["cells"] if cell in assignment
            )
            unassigned = sum(1 for cell in c["cells"] if cell not in assignment)

            if assigned_mines > c["count"]:
                return False
            if assigned_mines + unassigned < c["count"]:
                return False

        return True

    # ------------------------------------------------------------------
    # Tier 3 — Probabilistic guessing
    # ------------------------------------------------------------------

    def tier3(self) -> list[Move]:
        """
        When no deterministic move exists, estimate mine probability for
        each covered cell and pick the safest one.

        Probability estimate:
          - For frontier cells: frequency of appearing as mine across all
            CSP solutions from a fresh Tier 2 run
          - For non-frontier cells: global baseline = remaining_mines / remaining_covered

        Returns:
            List containing exactly one Move (the best guess).
        """
        probs = self._estimate_probabilities()
        best_cell = min(probs, key=lambda cell: probs[cell])
        return [(best_cell[0], best_cell[1], "reveal")]

    def _estimate_probabilities(self) -> dict[tuple[int, int], float]:
        """
        Run CSP solution enumeration across all components and compute
        per-cell mine probability.

        Returns:
            Dict mapping (row, col) → float probability of being a mine.
            Covers all covered, unflagged cells.
        """
        covered_cells = self.board.get_covered_cells()
        if not covered_cells:
            return {}

        remaining = self.board.remaining_mines()
        total_covered = len(covered_cells)
        baseline = remaining / total_covered if total_covered > 0 else 0.5

        probs = {}

        # Compute per-cell mine frequency for frontier cells via CSP
        constraints = self._build_constraints()
        if constraints:
            components = self._get_connected_components(constraints)
            for component in components:
                variables = list({cell for c in component for cell in c["cells"]})
                if not variables:
                    continue

                solutions = []
                self._backtrack(component, variables, {}, solutions)

                if solutions:
                    num_solutions = len(solutions)
                    for cell in variables:
                        mine_count = sum(sol[cell] for sol in solutions)
                        probs[cell] = mine_count / num_solutions
                else:
                    for cell in variables:
                        probs[cell] = baseline

        # Assign baseline probability to non-frontier covered cells
        for cell in covered_cells:
            if cell not in probs:
                probs[cell] = baseline

        return probs
