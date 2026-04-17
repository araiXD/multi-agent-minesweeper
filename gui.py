"""
gui.py — pygame visualization for solo solver and Battle mode

Layout (Battle mode):
  ┌─────────────────────────────────────┐
  │  Agent 1: Score  │  Agent 2: Score  │  ← scoreboard bar
  ├─────────────────────────────────────┤
  │                                     │
  │           MINESWEEPER BOARD         │  ← main board (shared)
  │                                     │
  ├─────────────────────────────────────┤
  │  Move log / event feed              │  ← status bar
  └─────────────────────────────────────┘

Color scheme (can be tweaked):
  Covered cell:   dark gray
  Revealed 0:     light gray
  Revealed 1-8:   white bg, colored number (standard minesweeper colors)
  Flagged:        red flag icon / red cell
  Mine hit:       orange/red explosion
  Agent 1 last:   blue highlight
  Agent 2 last:   green highlight
"""

import pygame
from board import Board
from battle import BattleGame


# ------------------------------------------------------------------
# Constants — tweak these for different screen sizes
# ------------------------------------------------------------------

CELL_SIZE = 40          # pixels per cell
SCOREBOARD_H = 60       # height of top scoreboard bar
STATUS_BAR_H = 40       # height of bottom status bar
SIDEBAR_W = 0           # reserved for future move log panel

FPS = 30

# Number colors (index = cell value 1–8, standard minesweeper palette)
NUMBER_COLORS = [
    None,                        # 0 — not displayed
    (0,   0,   255),             # 1 — blue
    (0,   128, 0),               # 2 — green
    (255, 0,   0),               # 3 — red
    (0,   0,   128),             # 4 — dark blue
    (128, 0,   0),               # 5 — dark red
    (0,   128, 128),             # 6 — teal
    (0,   0,   0),               # 7 — black
    (128, 128, 128),             # 8 — gray
]

AGENT_COLORS = {
    1: (100, 149, 237),  # cornflower blue
    2: (144, 238, 144),  # light green
}


class GUI:
    def __init__(self, battle: BattleGame):
        """
        Args:
            battle: the BattleGame instance to visualize.
                    GUI registers itself as the event callback.
        """
        self.battle = battle
        self.board = battle.board
        self.screen = None
        self.font = None
        self.font_large = None
        self.clock = None
        self.running = False
        self.last_event = None   # most recent GameEvent, for highlighting

        # Register GUI as the battle event listener
        self.battle.on_move = self.handle_event
        self.battle.on_game_over = self.handle_game_over

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self):
        """
        Initialize pygame, create window sized to board + UI chrome.
        Called once before the game loop starts.
        """
        pass

    def run(self):
        """
        Main pygame event + render loop.
        Calls battle.run_turn() on a timer or keypress, renders after each.
        """
        pass

    def quit(self):
        """Cleanly shut down pygame."""
        pass

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self):
        """Master render call — clears screen and draws all layers."""
        pass

    def draw_scoreboard(self):
        """
        Draw top bar with both agent names, scores, and whose turn it is.
        Highlight the active agent's side.
        """
        pass

    def draw_board(self):
        """
        Draw all cells. For each cell in board.visible:
          -2 → flagged (red)
          -1 → covered (dark gray)
           0 → revealed, blank (light gray)
          1-8 → revealed number (white bg + colored digit)

        Also draw highlight on the cell from last_event.
        """
        pass

    def draw_cell(self, row: int, col: int, highlight_agent: int = None):
        """
        Draw a single cell at (row, col).

        Args:
            row, col: board coordinates
            highlight_agent: if set, draw a colored border (agent color)
        """
        pass

    def draw_status_bar(self):
        """
        Draw bottom bar with last move description.
        e.g. "Agent 1 flagged (3,4) → +1 point, extra turn!"
        """
        pass

    def draw_game_over(self):
        """
        Overlay a game-over screen with winner, final scores, and
        a 'Press R to restart or Q to quit' prompt.
        """
        pass

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: dict):
        """
        Callback registered with BattleGame.on_move.
        Receives a GameEvent dict, updates last_event, triggers render.

        Args:
            event: GameEvent dict from battle.emit_event()
        """
        pass

    def handle_game_over(self, winner):
        """
        Callback registered with BattleGame.on_game_over.
        Triggers game over overlay.

        Args:
            winner: winning Agent or None if tie
        """
        pass

    def handle_input(self, pygame_event):
        """
        Handle keyboard/mouse input during the game loop.
        R → restart, Q → quit, SPACE → step one move (debug mode).

        Args:
            pygame_event: a pygame.event object
        """
        pass

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def board_to_screen(self, row: int, col: int) -> tuple[int, int]:
        """
        Convert board (row, col) to top-left pixel coords of that cell.

        Returns:
            (x, y) pixel position
        """
        pass

    def screen_to_board(self, x: int, y: int) -> tuple[int, int] | None:
        """
        Convert pixel coords to board (row, col). Returns None if outside board.

        Args:
            x, y: pixel coordinates

        Returns:
            (row, col) or None
        """
        pass
