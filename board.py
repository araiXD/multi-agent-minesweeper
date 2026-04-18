"""
board.py — Game engine and 2D array state management

The Board is the single source of truth for the game state.
Agents and the solver read from it but never write directly —
all mutations go through Board methods.

Cell values in self.visible:
  -2 = flagged
  -1 = covered (hidden)
   0 = revealed, no adjacent mines
   1-8 = revealed, n adjacent mines

Cell values in self.mines:
   0 = safe
   1 = mine
"""

import numpy as np
import random
from collections import deque


class Board:
    def __init__(self, rows: int, cols: int, num_mines: int):
        """
        Initialize a blank board. Mines are not placed until first reveal
        to guarantee the first click is always safe.

        Args:
            rows: number of rows
            cols: number of columns
            num_mines: total mines to place
        """
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines

        self.mines = np.zeros((rows, cols), dtype=int)      # ground truth, hidden from agents
        self.visible = np.full((rows, cols), -1, dtype=int) # what agents can see
        self.mine_counts = np.zeros((rows, cols), dtype=int) # precomputed neighbor mine counts

        self.mines_placed = False
        self.game_over = False
        self.win = False
        self.total_revealed = 0

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def place_mines(self, safe_row: int, safe_col: int):
        """
        Place mines randomly, guaranteeing (safe_row, safe_col) and its
        neighbors are mine-free. Called on first reveal.

        Args:
            safe_row: row of first click
            safe_col: col of first click
        """
        # Collect all cells that must stay safe (first click + its neighbors)
        safe_cells = set()
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r, c = safe_row + dr, safe_col + dc
                if self.is_valid(r, c):
                    safe_cells.add((r, c))

        # Build pool of candidate cells for mine placement
        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in safe_cells
        ]

        mine_cells = random.sample(candidates, self.num_mines)
        for r, c in mine_cells:
            self.mines[r, c] = 1

        self.mines_placed = True
        self.compute_neighbor_counts()

    def compute_neighbor_counts(self):
        """
        Precompute how many mines neighbor each cell and store in
        self.mine_counts. Called once after place_mines().
        """
        # Use 2D convolution with a 3x3 all-ones kernel via numpy slicing
        for r in range(self.rows):
            for c in range(self.cols):
                r0, r1 = max(0, r - 1), min(self.rows, r + 2)
                c0, c1 = max(0, c - 1), min(self.cols, c + 2)
                self.mine_counts[r, c] = int(self.mines[r0:r1, c0:c1].sum())

    # ------------------------------------------------------------------
    # Core actions — called by agents and battle loop
    # ------------------------------------------------------------------

    def reveal(self, row: int, col: int) -> str:
        """
        Reveal a cell. If it's a mine, game over. If count is 0,
        flood-fill reveal all connected zero-count neighbors.

        Args:
            row, col: target cell

        Returns:
            "mine"    — hit a mine, game over
            "safe"    — revealed successfully
            "already" — cell was already revealed or flagged
        """
        if not self.is_valid(row, col):
            return "already"

        if self.visible[row, col] != -1:
            return "already"

        # Place mines on first reveal
        if not self.mines_placed:
            self.place_mines(row, col)

        # Hit a mine
        if self.mines[row, col] == 1:
            self.visible[row, col] = self.mine_counts[row, col]  # reveal the cell
            self.game_over = True
            return "mine"

        # BFS flood fill for zero-count cells
        queue = deque()
        queue.append((row, col))
        visited = set()
        visited.add((row, col))

        while queue:
            r, c = queue.popleft()
            if self.visible[r, c] != -1:
                continue
            count = self.mine_counts[r, c]
            self.visible[r, c] = count
            self.total_revealed += 1

            if count == 0:
                for nr, nc in self.get_neighbors(r, c):
                    if (nr, nc) not in visited and self.visible[nr, nc] == -1:
                        visited.add((nr, nc))
                        queue.append((nr, nc))

        self.check_win()
        return "safe"

    def flag(self, row: int, col: int) -> bool:
        """
        Toggle a flag on a covered cell.

        Args:
            row, col: target cell

        Returns:
            True if flag was placed, False if removed or cell not coverable
        """
        if not self.is_valid(row, col):
            return False

        if self.visible[row, col] == -1:
            # Place flag
            self.visible[row, col] = -2
            return True
        elif self.visible[row, col] == -2:
            # Remove flag
            self.visible[row, col] = -1
            return False
        else:
            # Already revealed — can't flag
            return False

    def check_win(self) -> bool:
        """
        Win condition: all non-mine cells are revealed.
        Updates self.win and returns result.
        """
        non_mine_total = self.rows * self.cols - self.num_mines
        if self.total_revealed >= non_mine_total:
            self.win = True
            self.game_over = True
        return self.win

    # ------------------------------------------------------------------
    # Read-only helpers — used heavily by solver and agent
    # ------------------------------------------------------------------

    def get_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """
        Return list of valid (row, col) neighbors for a given cell.
        Handles edge/corner bounds automatically.
        """
        neighbors = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if self.is_valid(r, c):
                    neighbors.append((r, c))
        return neighbors

    def get_covered_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return neighbors that are currently covered (visible == -1)."""
        return [(r, c) for r, c in self.get_neighbors(row, col) if self.visible[r, c] == -1]

    def get_flagged_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return neighbors that are currently flagged (visible == -2)."""
        return [(r, c) for r, c in self.get_neighbors(row, col) if self.visible[r, c] == -2]

    def get_revealed_border(self) -> list[tuple[int, int]]:
        """
        Return all revealed cells that have at least one covered neighbor.
        This is the 'frontier' the solver operates on.
        """
        border = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.visible[r, c] >= 1:  # revealed with at least 1 mine neighbor
                    if self.get_covered_neighbors(r, c):
                        border.append((r, c))
        return border

    def get_covered_cells(self) -> list[tuple[int, int]]:
        """Return all cells that are still covered and unflagged."""
        rows, cols = np.where(self.visible == -1)
        return list(zip(rows.tolist(), cols.tolist()))

    def remaining_mines(self) -> int:
        """Return num_mines minus number of flags placed."""
        num_flags = int(np.sum(self.visible == -2))
        return self.num_mines - num_flags

    def is_valid(self, row: int, col: int) -> bool:
        """Return True if (row, col) is within board bounds."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def copy(self):
        """
        Return a deep copy of the board. Used by Minimax to simulate
        moves without mutating the real game state.
        """
        new_board = Board(self.rows, self.cols, self.num_mines)
        new_board.mines = self.mines.copy()
        new_board.visible = self.visible.copy()
        new_board.mine_counts = self.mine_counts.copy()
        new_board.mines_placed = self.mines_placed
        new_board.game_over = self.game_over
        new_board.win = self.win
        new_board.total_revealed = self.total_revealed
        return new_board

    def __repr__(self) -> str:
        """Pretty-print the visible board for debugging."""
        symbols = {-2: "F", -1: "."}
        lines = []
        for r in range(self.rows):
            row_str = ""
            for c in range(self.cols):
                v = self.visible[r, c]
                cell = symbols.get(v, str(v))
                row_str += cell + " "
            lines.append(row_str.rstrip())
        return "\n".join(lines)


# ------------------------------------------------------------------
# Preset difficulty configs — used by main.py and battle.py
# ------------------------------------------------------------------

DIFFICULTIES = {
    "beginner":     {"rows": 9,  "cols": 9,  "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 16, "cols": 30, "mines": 99},
}
