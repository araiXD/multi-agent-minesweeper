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
        pass

    def compute_neighbor_counts(self):
        """
        Precompute how many mines neighbor each cell and store in
        self.mine_counts. Called once after place_mines().
        """
        pass

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
        pass

    def flag(self, row: int, col: int) -> bool:
        """
        Toggle a flag on a covered cell.

        Args:
            row, col: target cell

        Returns:
            True if flag was placed, False if removed or cell not coverable
        """
        pass

    def check_win(self) -> bool:
        """
        Win condition: all non-mine cells are revealed.
        Updates self.win and returns result.
        """
        pass

    # ------------------------------------------------------------------
    # Read-only helpers — used heavily by solver and agent
    # ------------------------------------------------------------------

    def get_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """
        Return list of valid (row, col) neighbors for a given cell.
        Handles edge/corner bounds automatically.
        """
        pass

    def get_covered_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return neighbors that are currently covered (visible == -1)."""
        pass

    def get_flagged_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return neighbors that are currently flagged (visible == -2)."""
        pass

    def get_revealed_border(self) -> list[tuple[int, int]]:
        """
        Return all revealed cells that have at least one covered neighbor.
        This is the 'frontier' the solver operates on.
        """
        pass

    def get_covered_cells(self) -> list[tuple[int, int]]:
        """Return all cells that are still covered and unflagged."""
        pass

    def remaining_mines(self) -> int:
        """Return num_mines minus number of flags placed."""
        pass

    def is_valid(self, row: int, col: int) -> bool:
        """Return True if (row, col) is within board bounds."""
        pass

    def copy(self):
        """
        Return a deep copy of the board. Used by Minimax to simulate
        moves without mutating the real game state.
        """
        pass

    def __repr__(self) -> str:
        """Pretty-print the visible board for debugging."""
        pass


# ------------------------------------------------------------------
# Preset difficulty configs — used by main.py and battle.py
# ------------------------------------------------------------------

DIFFICULTIES = {
    "beginner":     {"rows": 9,  "cols": 9,  "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 16, "cols": 30, "mines": 99},
}
