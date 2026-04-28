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

import json
import sys
import pygame
from board import Board, DIFFICULTIES
from agent import Agent
from battle import BattleGame


# ------------------------------------------------------------------
# Constants — tweak these for different screen sizes
# ------------------------------------------------------------------

CELL_SIZE = 40          # pixels per cell
SCOREBOARD_H = 60       # height of top scoreboard bar
STATUS_BAR_H = 40       # height of bottom status bar
SIDEBAR_W = 0           # reserved for future move log panel

FPS = 30
FLASH_DURATION = 500    # ms — duration of mine-hit flash
DEFAULT_MOVE_MS = 500   # ms between auto-moves
MIN_MOVE_MS = 100
MAX_MOVE_MS = 2000
MOVE_STEP = 100

# Custom pygame event fired by the auto-play timer
MOVE_TIMER = pygame.USEREVENT + 1

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

# UI palette
COLOR_COVERED      = (78, 78, 78)
COLOR_REVEALED     = (188, 188, 188)
COLOR_REVEALED_N   = (212, 212, 212)
COLOR_FLAGGED_BG   = (160, 28, 28)
COLOR_MINE_BG      = (155, 40, 0)
COLOR_FLASH_A      = (255, 120, 0)    # start of flash (orange)
COLOR_FLASH_B      = (200, 30, 0)     # end of flash (dark red)
COLOR_GRID         = (48, 48, 48)
COLOR_BG           = (22, 22, 32)
COLOR_SCOREBOARD   = (16, 16, 44)
COLOR_STATUS_BG    = (14, 14, 24)
COLOR_DIVIDER      = (55, 55, 90)
COLOR_TEXT         = (228, 228, 228)
COLOR_DIM          = (120, 120, 140)
COLOR_MINE_TEXT    = (210, 60, 60)
COLOR_PAUSED       = (220, 220, 60)
COLOR_GAMEOVER_TXT = (255, 240, 80)

# ------------------------------------------------------------------
# Menu constants
# ------------------------------------------------------------------

MENU_W = 600
MENU_H = 500

MENU_BTN_W    = 112   # button width
MENU_BTN_H    = 34    # button height
MENU_BTN_GAP  = 8     # gap between buttons in a row
MENU_LABEL_X  = 25    # x of section labels
MENU_BTN_X    = 168   # x where buttons start
MENU_ROW_H    = 55    # vertical spacing between section rows
MENU_FIRST_Y  = 102   # y of first section row

# Sections: (attr_name, display_label, [(btn_label, value), ...])
MENU_SECTIONS = [
    ("difficulty", "DIFFICULTY", [("Beginner", "beginner"), ("Intermediate", "intermediate"), ("Expert", "expert")]),
    ("agent1",     "AGENT 1",    [("CSP", "csp"), ("Tier1", "tier1"), ("Random", "random")]),
    ("agent2",     "AGENT 2",    [("CSP", "csp"), ("Tier1", "tier1"), ("Random", "random")]),
    ("speed",      "SPEED",      [("Slow", "slow"), ("Medium", "medium"), ("Fast", "fast")]),
    ("first_move", "FIRST MOVE", [("Auto", "auto"), ("Manual", "manual")]),
]

SPEED_MS = {"slow": 1000, "medium": 500, "fast": 150}

# Menu palette
COLOR_BTN_SEL      = (70, 115, 200)
COLOR_BTN_UNSEL    = (42, 42, 58)
COLOR_BTN_BORDER   = (75, 75, 105)
COLOR_BTN_DIMMED   = (28, 28, 38)
COLOR_SECTION_LBL  = (175, 175, 198)
COLOR_MENU_TITLE   = (255, 240, 80)
COLOR_START_NORMAL = (38, 150, 75)
COLOR_START_HOVER  = (55, 190, 100)


# ------------------------------------------------------------------
# MenuScreen
# ------------------------------------------------------------------

class MenuScreen:
    """
    Pre-game configuration screen. Lets the player choose mode,
    difficulty, agent strategies, and playback speed before launching.
    Shares the pygame window with GUI — call run() to block until
    the player clicks START, then use the returned config dict.
    """

    def __init__(self, screen, font, font_large, clock):
        self.screen    = screen
        self.font      = font
        self.font_large = font_large
        self.clock     = clock

        self.font_title = pygame.font.Font(None, 46)
        self.font_start = pygame.font.Font(None, 34)

        # Defaults
        self.difficulty = "intermediate"
        self.agent1     = "csp"
        self.agent2     = "csp"
        self.speed      = "medium"
        self.first_move = "auto"

        self._buttons    = {}   # (attr, value) -> Rect
        self._start_rect = None
        self._stats_rect = None
        self._build_layout()

    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Block until START is clicked; return config dict."""
        self.screen = pygame.display.set_mode((MENU_W, MENU_H))
        pygame.display.set_caption("Minesweeper Battle")
        self._build_layout()

        while True:
            mouse_pos = pygame.mouse.get_pos()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                        pygame.quit()
                        sys.exit()
                    elif ev.key == pygame.K_RETURN:
                        return self._config()
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self._start_rect.collidepoint(ev.pos):
                        return self._config()
                    elif self._stats_rect.collidepoint(ev.pos):
                        return "stats"
                    self._handle_click(ev.pos)

            self._render(mouse_pos)
            self.clock.tick(FPS)

    # ------------------------------------------------------------------

    def _build_layout(self):
        """Precompute button rects from section definitions."""
        self._buttons = {}
        for row_i, (attr, _label, options) in enumerate(MENU_SECTIONS):
            row_y = MENU_FIRST_Y + row_i * MENU_ROW_H
            for btn_i, (_lbl, value) in enumerate(options):
                x = MENU_BTN_X + btn_i * (MENU_BTN_W + MENU_BTN_GAP)
                self._buttons[(attr, value)] = pygame.Rect(x, row_y, MENU_BTN_W, MENU_BTN_H)

        btn_h   = 48
        start_w = 160
        stats_w = 120
        btn_gap = 16
        total_btn_w = start_w + btn_gap + stats_w
        btn_left = MENU_W // 2 - total_btn_w // 2
        btn_y    = MENU_FIRST_Y + len(MENU_SECTIONS) * MENU_ROW_H + 18

        self._start_rect = pygame.Rect(btn_left, btn_y, start_w, btn_h)
        self._stats_rect = pygame.Rect(btn_left + start_w + btn_gap, btn_y, stats_w, btn_h)

    def _handle_click(self, pos):
        for (attr, value), rect in self._buttons.items():
            if rect.collidepoint(pos):
                setattr(self, attr, value)
                return

    def _config(self) -> dict:
        return {
            "difficulty": self.difficulty,
            "agent1":     self.agent1,
            "agent2":     self.agent2,
            "speed":      self.speed,
            "first_move": self.first_move,
        }

    # ------------------------------------------------------------------

    def _render(self, mouse_pos):
        self.screen.fill(COLOR_BG)

        # Title
        title_surf = self.font_title.render("MINESWEEPER  BATTLE", True, COLOR_MENU_TITLE)
        self.screen.blit(title_surf, (MENU_W // 2 - title_surf.get_width() // 2, 16))
        sub = self.font.render("Configure your game, then press START", True, COLOR_DIM)
        self.screen.blit(sub, (MENU_W // 2 - sub.get_width() // 2, 60))
        pygame.draw.line(self.screen, COLOR_DIVIDER,
                         (MENU_LABEL_X, 90), (MENU_W - MENU_LABEL_X, 90), 1)

        # Section rows
        current = {
            "difficulty": self.difficulty,
            "agent1": self.agent1, "agent2": self.agent2,
            "speed": self.speed, "first_move": self.first_move,
        }

        for row_i, (attr, label_txt, options) in enumerate(MENU_SECTIONS):
            row_y = MENU_FIRST_Y + row_i * MENU_ROW_H

            # Section label
            lbl_surf = self.font_large.render(label_txt, True, COLOR_SECTION_LBL)
            lbl_y    = row_y + (MENU_BTN_H - lbl_surf.get_height()) // 2
            self.screen.blit(lbl_surf, (MENU_LABEL_X, lbl_y))

            # Buttons
            for _btn_lbl, value in options:
                rect     = self._buttons[(attr, value)]
                selected = (current[attr] == value)

                if selected:
                    bg = AGENT_COLORS[1] if attr == "agent1" else \
                         AGENT_COLORS[2] if attr == "agent2" else COLOR_BTN_SEL
                    txt_col, border = (255, 255, 255), bg
                else:
                    bg, txt_col, border = COLOR_BTN_UNSEL, COLOR_DIM, COLOR_BTN_BORDER

                pygame.draw.rect(self.screen, bg, rect, border_radius=4)
                pygame.draw.rect(self.screen, border, rect, 1, border_radius=4)
                t = self.font.render(_btn_lbl, True, txt_col)
                self.screen.blit(t, (
                    rect.x + (rect.w - t.get_width()) // 2,
                    rect.y + (rect.h - t.get_height()) // 2,
                ))

        # Divider above start
        div_y = self._start_rect.y - 10
        pygame.draw.line(self.screen, COLOR_DIVIDER,
                         (MENU_LABEL_X, div_y), (MENU_W - MENU_LABEL_X, div_y), 1)

        # START button
        hover    = self._start_rect.collidepoint(mouse_pos)
        start_bg = COLOR_START_HOVER if hover else COLOR_START_NORMAL
        pygame.draw.rect(self.screen, start_bg, self._start_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 230, 140), self._start_rect, 1, border_radius=6)
        st = self.font_start.render("START", True, (255, 255, 255))
        self.screen.blit(st, (
            self._start_rect.x + (self._start_rect.w - st.get_width()) // 2,
            self._start_rect.y + (self._start_rect.h - st.get_height()) // 2,
        ))

        # STATS button
        hover_s  = self._stats_rect.collidepoint(mouse_pos)
        stats_bg = (80, 80, 140) if hover_s else (46, 46, 88)
        pygame.draw.rect(self.screen, stats_bg, self._stats_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BTN_BORDER, self._stats_rect, 1, border_radius=6)
        ss = self.font_start.render("STATS", True, (200, 200, 255))
        self.screen.blit(ss, (
            self._stats_rect.x + (self._stats_rect.w - ss.get_width()) // 2,
            self._stats_rect.y + (self._stats_rect.h - ss.get_height()) // 2,
        ))

        # Keyboard hint
        hint = self.font.render("Enter to start  |  Q to quit", True, (60, 60, 80))
        self.screen.blit(hint, (MENU_W // 2 - hint.get_width() // 2, MENU_H - 22))

        pygame.display.flip()


# ------------------------------------------------------------------
# StatsScreen
# ------------------------------------------------------------------

class StatsScreen:
    """
    Reads bench_results.json and renders per-matchup win-rate bars
    and summary stats using pygame only. BACK returns to MenuScreen.
    """

    _SECTION_START_Y = 80
    _SECTION_H       = 175   # vertical space allocated per matchup
    _BAR_AREA_X      = 160   # x where bars begin (after agent name label)
    _BAR_MAX_W       = 310   # bar width representing 100 %
    _BAR_H           = 18
    _BAR_GAP         = 8     # gap between A1 and A2 bars

    def __init__(self, screen, font, font_large, clock):
        self.screen     = screen
        self.font       = font
        self.font_large = font_large
        self.clock      = clock
        self.font_title = pygame.font.Font(None, 46)
        self._back_rect = None
        self._data      = self._load_data()

    def _load_data(self):
        try:
            with open("bench_results.json") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None

    def run(self):
        """Block until BACK is clicked or Esc/Q pressed."""
        self.screen = pygame.display.set_mode((MENU_W, MENU_H))
        pygame.display.set_caption("Minesweeper Battle - Stats")

        back_w, back_h = 140, 40
        self._back_rect = pygame.Rect(
            MENU_W // 2 - back_w // 2,
            MENU_H - back_h - 14,
            back_w, back_h,
        )

        while True:
            mouse_pos = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_q, pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        return
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self._back_rect.collidepoint(ev.pos):
                        return

            self._render(mouse_pos)
            self.clock.tick(FPS)

    def _render(self, mouse_pos):
        self.screen.fill(COLOR_BG)

        # Title
        title = self.font_title.render("BENCHMARK STATS", True, COLOR_MENU_TITLE)
        self.screen.blit(title, (MENU_W // 2 - title.get_width() // 2, 14))
        pygame.draw.line(self.screen, COLOR_DIVIDER,
                         (MENU_LABEL_X, 68), (MENU_W - MENU_LABEL_X, 68), 1)

        if self._data is None:
            msg1 = self.font_large.render("No benchmark data found.", True, COLOR_DIM)
            msg2 = self.font.render(
                "Run: python main.py --mode headless to generate.", True, COLOR_DIM)
            self.screen.blit(msg1, (MENU_W // 2 - msg1.get_width() // 2, MENU_H // 2 - 30))
            self.screen.blit(msg2, (MENU_W // 2 - msg2.get_width() // 2, MENU_H // 2 + 5))
        else:
            for i, matchup in enumerate(self._data):
                self._render_matchup(matchup, i)

        # BACK button
        hover   = self._back_rect.collidepoint(mouse_pos)
        back_bg = (80, 80, 115) if hover else (50, 50, 72)
        pygame.draw.rect(self.screen, back_bg, self._back_rect, border_radius=5)
        pygame.draw.rect(self.screen, COLOR_BTN_BORDER, self._back_rect, 1, border_radius=5)
        bt = self.font_large.render("BACK", True, COLOR_TEXT)
        self.screen.blit(bt, (
            self._back_rect.x + (self._back_rect.w - bt.get_width()) // 2,
            self._back_rect.y + (self._back_rect.h - bt.get_height()) // 2,
        ))

        pygame.display.flip()

    def _render_matchup(self, matchup: dict, index: int):
        base_y = self._SECTION_START_Y + index * self._SECTION_H
        BX     = self._BAR_AREA_X
        BMW    = self._BAR_MAX_W
        BH     = self._BAR_H
        BGAP   = self._BAR_GAP

        parts = matchup.get("matchup", "").split(" vs ")
        n1    = parts[0].upper() if parts else "A1"
        n2    = parts[1].upper() if len(parts) > 1 else "A2"
        games = matchup.get("games", 0)

        # Section label
        lbl = self.font_large.render(f"{n1} vs {n2}  |  {games} games", True, COLOR_TEXT)
        self.screen.blit(lbl, (MENU_LABEL_X, base_y))

        bar_y = base_y + 30

        # Agent name labels (left column)
        a1_lbl = self.font.render(n1, True, AGENT_COLORS[1])
        a2_lbl = self.font.render(n2, True, AGENT_COLORS[2])
        self.screen.blit(a1_lbl, (MENU_LABEL_X,
                                   bar_y + (BH - a1_lbl.get_height()) // 2))
        self.screen.blit(a2_lbl, (MENU_LABEL_X,
                                   bar_y + BH + BGAP + (BH - a2_lbl.get_height()) // 2))

        wr1 = matchup.get("win_rate_1_pct", 0)
        wr2 = matchup.get("win_rate_2_pct", 0)
        tie = matchup.get("tie_rate_pct", 0)

        # Background tracks
        pygame.draw.rect(self.screen, (35, 35, 52),
                         pygame.Rect(BX, bar_y, BMW, BH), border_radius=3)
        pygame.draw.rect(self.screen, (35, 35, 52),
                         pygame.Rect(BX, bar_y + BH + BGAP, BMW, BH), border_radius=3)

        # Filled bars proportional to win rate
        w1 = int(BMW * wr1 / 100)
        w2 = int(BMW * wr2 / 100)
        if w1 > 0:
            pygame.draw.rect(self.screen, AGENT_COLORS[1],
                             pygame.Rect(BX, bar_y, w1, BH), border_radius=3)
        if w2 > 0:
            pygame.draw.rect(self.screen, AGENT_COLORS[2],
                             pygame.Rect(BX, bar_y + BH + BGAP, w2, BH), border_radius=3)

        # Percentage labels to the right of each bar
        p1 = self.font.render(f"{wr1:.1f}%", True, COLOR_TEXT)
        p2 = self.font.render(f"{wr2:.1f}%", True, COLOR_TEXT)
        self.screen.blit(p1, (BX + max(w1, 4) + 6,
                               bar_y + (BH - p1.get_height()) // 2))
        self.screen.blit(p2, (BX + max(w2, 4) + 6,
                               bar_y + BH + BGAP + (BH - p2.get_height()) // 2))

        # Tie rate right-aligned (only if non-zero)
        if tie > 0:
            tie_txt = self.font.render(f"Tie: {tie:.1f}%", True, COLOR_DIM)
            self.screen.blit(tie_txt,
                             (MENU_W - MENU_LABEL_X - tie_txt.get_width(),
                              bar_y + (BH - tie_txt.get_height()) // 2))

        # Stats rows below bars
        stats_y = bar_y + BH * 2 + BGAP + 12
        s1    = matchup.get("avg_score_1", 0)
        s2    = matchup.get("avg_score_2", 0)
        m1    = matchup.get("avg_mines_hit_1", 0)
        m2    = matchup.get("avg_mines_hit_2", 0)
        turns = matchup.get("avg_turns", 0)

        for line_i, text in enumerate([
            f"Avg Score:  {n1} {s1:+.2f}  |  {n2} {s2:+.2f}",
            f"Mine Hits:  {n1} {m1:.2f}  |  {n2} {m2:.2f}",
            f"Avg Turns:  {turns:.1f}",
        ]):
            surf = self.font.render(text, True, COLOR_DIM)
            self.screen.blit(surf, (MENU_LABEL_X, stats_y + line_i * 22))

        # Divider between sections (not after the last one)
        if self._data and index < len(self._data) - 1:
            div_y = base_y + self._SECTION_H - 6
            pygame.draw.line(self.screen, COLOR_DIVIDER,
                             (MENU_LABEL_X, div_y), (MENU_W - MENU_LABEL_X, div_y), 1)


# ------------------------------------------------------------------
# GUI
# ------------------------------------------------------------------

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

        # Extra runtime state
        self.winner = None
        self.paused = False
        self.flash_cell = None   # (row, col) of active mine flash
        self.flash_start = None  # pygame.time.get_ticks() when flash began
        self.hit_cells = set()   # all cells that have been hit (stay marked)
        self.move_interval = DEFAULT_MOVE_MS
        self.go_to_menu = False  # set True when user presses R on game-over screen
        self.first_move = "auto"          # "auto" or "manual"
        self.waiting_first_move = False   # True while awaiting manual first click

        # Remember strategies so we can recreate agents on restart
        self._strategy1 = battle.agents[0].strategy
        self._strategy2 = battle.agents[1].strategy

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
        pygame.init()
        w = self.board.cols * CELL_SIZE + SIDEBAR_W
        h = SCOREBOARD_H + self.board.rows * CELL_SIZE + STATUS_BAR_H
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Minesweeper Battle")
        self.font = pygame.font.Font(None, 22)
        self.font_large = pygame.font.Font(None, 26)
        self.clock = pygame.time.Clock()

    def run(self, first_move: str = "auto") -> str | None:
        """
        Main pygame event + render loop.

        Args:
            first_move: "auto" performs the opening reveal at board center;
                        "manual" shows an overlay and waits for a user click.

        Returns "menu" if the user pressed R on the game-over screen
        (caller should show MenuScreen again). Otherwise calls quit().
        """
        self.first_move = first_move

        # Resize window to fit this board
        w = self.board.cols * CELL_SIZE + SIDEBAR_W
        h = SCOREBOARD_H + self.board.rows * CELL_SIZE + STATUS_BAR_H
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Minesweeper Battle")

        if first_move == "manual":
            self.waiting_first_move = True
            # Timer stays off until the player clicks
        else:
            center_r = self.board.rows // 2
            center_c = self.board.cols // 2
            self.board.reveal(center_r, center_c)
            self.last_event = {
                "type":   "reveal",
                "agent":  self.battle.agents[0].agent_id,
                "row":    center_r,
                "col":    center_c,
                "result": "safe",
                "score1": 0,
                "score2": 0,
                "turn":   0,
            }
            pygame.time.set_timer(MOVE_TIMER, self.move_interval)

        self.running = True
        self.render()

        while self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.time.set_timer(MOVE_TIMER, 0)
                    self.quit()
                elif ev.type == pygame.KEYDOWN:
                    if self.waiting_first_move:
                        if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                            self.running = False
                    else:
                        self.handle_input(ev)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.waiting_first_move:
                        cell = self.screen_to_board(ev.pos[0], ev.pos[1])
                        if cell is not None:
                            r, c = cell
                            self.board.reveal(r, c)
                            self.last_event = {
                                "type":   "reveal",
                                "agent":  self.battle.agents[0].agent_id,
                                "row":    r,
                                "col":    c,
                                "result": "safe",
                                "score1": 0,
                                "score2": 0,
                                "turn":   0,
                            }
                            self.waiting_first_move = False
                            pygame.time.set_timer(MOVE_TIMER, self.move_interval)
                elif ev.type == MOVE_TIMER:
                    if not self.paused and not self.battle.game_over:
                        self.battle.run_turn()

            self.render()
            self.clock.tick(FPS)

        pygame.time.set_timer(MOVE_TIMER, 0)

        if self.go_to_menu:
            return "menu"

        self.quit()

    def quit(self):
        """Cleanly shut down pygame."""
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self):
        """Master render call — clears screen and draws all layers."""
        self.screen.fill(COLOR_BG)
        self.draw_scoreboard()
        self.draw_board()
        self.draw_status_bar()
        if self.battle.game_over:
            self.draw_game_over()
        elif self.waiting_first_move:
            self.draw_first_move_overlay()
        pygame.display.flip()

    def draw_scoreboard(self):
        """
        Draw top bar with both agent names, scores, and whose turn it is.
        Highlight the active agent's side.
        """
        w = self.screen.get_width()
        pygame.draw.rect(self.screen, COLOR_SCOREBOARD, (0, 0, w, SCOREBOARD_H))

        a1, a2 = self.battle.agents
        if not self.battle.game_over:
            current_id = self.battle.current_agent().agent_id
        else:
            current_id = None

        # Subtle active-agent glow on their half
        if current_id == 1:
            pygame.draw.rect(self.screen, (20, 20, 60), (0, 0, w // 2, SCOREBOARD_H))
        elif current_id == 2:
            pygame.draw.rect(self.screen, (10, 30, 10), (w // 2, 0, w // 2, SCOREBOARD_H))

        # Agent 1 — left side
        a1_nc = AGENT_COLORS[1] if current_id == 1 else COLOR_DIM
        t = self.font_large.render(f"Agent 1  ({a1.strategy.upper()})", True, a1_nc)
        self.screen.blit(t, (12, 7))
        s = self.font_large.render(f"Score: {a1.score:+d}", True, COLOR_TEXT)
        self.screen.blit(s, (12, 33))

        # Center — mines remaining + turn indicator
        mines = self.board.remaining_mines()
        mt = self.font_large.render(f"Mines: {mines}", True, COLOR_MINE_TEXT)
        self.screen.blit(mt, (w // 2 - mt.get_width() // 2, 7))

        if self.battle.game_over:
            ti, ti_c = "GAME OVER", COLOR_TEXT
        elif self.paused:
            ti, ti_c = "[ PAUSED ]", COLOR_PAUSED
        else:
            ti, ti_c = f"Agent {current_id}'s turn", AGENT_COLORS[current_id]
        tt = self.font.render(ti, True, ti_c)
        self.screen.blit(tt, (w // 2 - tt.get_width() // 2, 36))

        # Agent 2 — right side
        a2_nc = AGENT_COLORS[2] if current_id == 2 else COLOR_DIM
        t2 = self.font_large.render(f"Agent 2  ({a2.strategy.upper()})", True, a2_nc)
        self.screen.blit(t2, (w - t2.get_width() - 12, 7))
        s2 = self.font_large.render(f"Score: {a2.score:+d}", True, COLOR_TEXT)
        self.screen.blit(s2, (w - s2.get_width() - 12, 33))

        # Bottom divider
        pygame.draw.line(self.screen, COLOR_DIVIDER, (0, SCOREBOARD_H - 1), (w, SCOREBOARD_H - 1), 2)

    def draw_board(self):
        """
        Draw all cells. For each cell in board.visible:
          -2 → flagged (red)
          -1 → covered (dark gray)
           0 → revealed, blank (light gray)
          1-8 → revealed number (white bg + colored digit)

        Also draw highlight on the cell from last_event.
        """
        # Determine which cell to highlight and which agent owns it
        highlight_cell = None
        highlight_agent = None
        if self.last_event:
            r = self.last_event.get("row", -1)
            c = self.last_event.get("col", -1)
            if r >= 0 and c >= 0 and self.last_event.get("type") != "game_over":
                highlight_cell = (r, c)
                highlight_agent = self.last_event.get("agent")

        for row in range(self.board.rows):
            for col in range(self.board.cols):
                ha = highlight_agent if (row, col) == highlight_cell else None
                self.draw_cell(row, col, ha)

    def draw_cell(self, row: int, col: int, highlight_agent: int = None):
        """
        Draw a single cell at (row, col).

        Args:
            row, col: board coordinates
            highlight_agent: if set, draw a colored border (agent color)
        """
        x, y = self.board_to_screen(row, col)
        rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        v = int(self.board.visible[row, col])

        # ---- Flash animation ----
        now = pygame.time.get_ticks()
        is_flashing = (
            self.flash_cell == (row, col)
            and self.flash_start is not None
            and (now - self.flash_start) < FLASH_DURATION
        )

        if is_flashing:
            t = (now - self.flash_start) / FLASH_DURATION  # 0 → 1
            r_ch = int(COLOR_FLASH_A[0] + (COLOR_FLASH_B[0] - COLOR_FLASH_A[0]) * t)
            g_ch = int(COLOR_FLASH_A[1] + (COLOR_FLASH_B[1] - COLOR_FLASH_A[1]) * t)
            b_ch = int(COLOR_FLASH_A[2] + (COLOR_FLASH_B[2] - COLOR_FLASH_A[2]) * t)
            pygame.draw.rect(self.screen, (r_ch, g_ch, b_ch), rect)

        elif (row, col) in self.hit_cells:
            # Previously exploded cell — permanently marked
            pygame.draw.rect(self.screen, COLOR_MINE_BG, rect)
            sym = self.font.render("*", True, (255, 200, 50))
            self.screen.blit(sym, rect.move(
                (CELL_SIZE - sym.get_width()) // 2,
                (CELL_SIZE - sym.get_height()) // 2,
            ).topleft)

        elif v == -2:
            # Flagged
            pygame.draw.rect(self.screen, COLOR_FLAGGED_BG, rect)
            f = self.font.render("F", True, (255, 230, 230))
            self.screen.blit(f, rect.move(
                (CELL_SIZE - f.get_width()) // 2,
                (CELL_SIZE - f.get_height()) // 2,
            ).topleft)

        elif v == -1:
            # Covered — 3-D bevel
            pygame.draw.rect(self.screen, COLOR_COVERED, rect)
            pygame.draw.line(self.screen, (112, 112, 112), (x, y), (x + CELL_SIZE - 2, y))
            pygame.draw.line(self.screen, (112, 112, 112), (x, y), (x, y + CELL_SIZE - 2))
            pygame.draw.line(self.screen, (36, 36, 36),
                             (x + CELL_SIZE - 1, y), (x + CELL_SIZE - 1, y + CELL_SIZE - 1))
            pygame.draw.line(self.screen, (36, 36, 36),
                             (x, y + CELL_SIZE - 1), (x + CELL_SIZE - 1, y + CELL_SIZE - 1))

        elif v == 0:
            # Revealed empty
            pygame.draw.rect(self.screen, COLOR_REVEALED, rect)

        else:
            # Revealed number 1–8
            pygame.draw.rect(self.screen, COLOR_REVEALED_N, rect)
            nc = NUMBER_COLORS[v] if 1 <= v <= 8 else (0, 0, 0)
            ns = self.font.render(str(v), True, nc)
            self.screen.blit(ns, rect.move(
                (CELL_SIZE - ns.get_width()) // 2,
                (CELL_SIZE - ns.get_height()) // 2,
            ).topleft)

        # Grid border
        pygame.draw.rect(self.screen, COLOR_GRID, rect, 1)

        # Agent highlight border (3 px, drawn on top)
        if highlight_agent is not None:
            pygame.draw.rect(self.screen, AGENT_COLORS[highlight_agent], rect, 3)

    def draw_status_bar(self):
        """
        Draw bottom bar with last move description.
        e.g. "Agent 1 flagged (3,4) → +1 point, extra turn!"
        """
        bar_y = SCOREBOARD_H + self.board.rows * CELL_SIZE
        w = self.screen.get_width()
        pygame.draw.rect(self.screen, COLOR_STATUS_BG, (0, bar_y, w, STATUS_BAR_H))
        pygame.draw.line(self.screen, COLOR_DIVIDER, (0, bar_y), (w, bar_y), 2)

        ev = self.last_event
        if self.waiting_first_move:
            msg = "Manual first move -- click any cell to open the board"
        elif ev is None:
            msg = "Game starting..."
        else:
            aid = ev.get("agent", "?")
            r, c = ev.get("row", 0), ev.get("col", 0)
            et = ev.get("type", "")
            if et == "flag":
                msg = f"Agent {aid} flagged ({r},{c})  ->  +1 point, extra turn!"
            elif et == "mine_hit":
                msg = f"Agent {aid} hit a mine at ({r},{c})  ->  -1 point"
            elif et == "reveal":
                msg = f"Agent {aid} revealed ({r},{c})  ->  turn ends"
            elif et == "game_over":
                msg = (f"GAME OVER  -  Agent {self.winner.agent_id} wins!"
                       if self.winner else "GAME OVER  -  It's a TIE!")
            else:
                msg = ""

        speed_tag = f"  [speed: {self.move_interval}ms  +/- to adjust]"
        if self.paused:
            speed_tag = "  [PAUSED — SPACE to resume]"

        txt = self.font.render(msg + speed_tag, True, COLOR_TEXT)
        self.screen.blit(txt, (10, bar_y + (STATUS_BAR_H - txt.get_height()) // 2))

    def draw_game_over(self):
        """
        Semi-transparent overlay with a two-column post-match stats table.
        """
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        w, h   = self.screen.get_size()
        a1, a2 = self.battle.agents

        PANEL_W = min(420, w - 20)
        PANEL_H = 328
        px = (w - PANEL_W) // 2
        py = max(SCOREBOARD_H + 6, (h - PANEL_H) // 2)

        # Panel background
        pygame.draw.rect(self.screen, (14, 14, 28), (px, py, PANEL_W, PANEL_H), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_DIVIDER, (px, py, PANEL_W, PANEL_H), 1, border_radius=8)

        font_title  = pygame.font.Font(None, 38)
        font_winner = pygame.font.Font(None, 28)
        font_row    = self.font        # size 22
        font_hdr    = self.font_large  # size 26

        def blit_cx(surf, y):
            self.screen.blit(surf, (px + PANEL_W // 2 - surf.get_width() // 2, py + y))

        # Header
        blit_cx(font_title.render("G A M E   O V E R", True, COLOR_GAMEOVER_TXT), 14)
        if self.winner:
            wstr   = f"Agent {self.winner.agent_id}  ({self.winner.strategy.upper()})  wins!"
            wcolor = AGENT_COLORS[self.winner.agent_id]
        else:
            wstr, wcolor = "It's a TIE!", COLOR_TEXT
        blit_cx(font_winner.render(wstr, True, wcolor), 48)
        pygame.draw.line(self.screen, COLOR_DIVIDER,
                         (px + 12, py + 78), (px + PANEL_W - 12, py + 78), 1)

        # Column positions (proportional so they scale with PANEL_W)
        LABEL_X = px + 14
        SEP1_X  = px + int(PANEL_W * 0.52)
        A1_RX   = px + int(PANEL_W * 0.70)
        SEP2_X  = px + int(PANEL_W * 0.73)
        A2_RX   = px + PANEL_W - 12

        ROW_START_Y = py + 88
        ROW_H       = 22

        # Column headers
        a1_hdr = font_hdr.render(f"A1 ({a1.strategy.upper()})", True, AGENT_COLORS[1])
        a2_hdr = font_hdr.render(f"A2 ({a2.strategy.upper()})", True, AGENT_COLORS[2])
        a1_hdr_cx = (SEP1_X + SEP2_X) // 2
        a2_hdr_cx = (SEP2_X + px + PANEL_W - 12) // 2
        self.screen.blit(a1_hdr, (a1_hdr_cx - a1_hdr.get_width() // 2, ROW_START_Y))
        self.screen.blit(a2_hdr, (a2_hdr_cx - a2_hdr.get_width() // 2, ROW_START_Y))

        # Computed stats
        eff1 = (a1.flags / a1.moves_made * 100) if a1.moves_made > 0 else 0.0
        eff2 = (a2.flags / a2.moves_made * 100) if a2.moves_made > 0 else 0.0
        ppt1 = (a1.score / a1.moves_made) if a1.moves_made > 0 else 0.0
        ppt2 = (a2.score / a2.moves_made) if a2.moves_made > 0 else 0.0

        rows = [
            ("Score",      f"{a1.score:+d}",   f"{a2.score:+d}"),
            ("Flags",      str(a1.flags),       str(a2.flags)),
            ("Reveals",    str(a1.reveals),     str(a2.reveals)),
            ("Mine Hits",  str(a1.mines_hit),   str(a2.mines_hit)),
            ("Moves",      str(a1.moves_made),  str(a2.moves_made)),
            ("Efficiency", f"{eff1:.1f}%",      f"{eff2:.1f}%"),
            ("Pts/Turn",   f"{ppt1:.2f}",       f"{ppt2:.2f}"),
        ]

        table_top    = ROW_START_Y + ROW_H + 2
        table_bottom = ROW_START_Y + ROW_H * (len(rows) + 1) + 4
        pygame.draw.line(self.screen, COLOR_DIVIDER, (SEP1_X, table_top), (SEP1_X, table_bottom))
        pygame.draw.line(self.screen, COLOR_DIVIDER, (SEP2_X, table_top), (SEP2_X, table_bottom))

        for i, (label, v1, v2) in enumerate(rows):
            row_y = ROW_START_Y + ROW_H * (i + 1) + 4
            vc    = COLOR_TEXT if i % 2 == 0 else (210, 210, 218)
            lbl_s = font_row.render(label, True, COLOR_DIM)
            v1_s  = font_row.render(v1,    True, vc)
            v2_s  = font_row.render(v2,    True, vc)
            self.screen.blit(lbl_s, (LABEL_X,                      row_y))
            self.screen.blit(v1_s,  (A1_RX - v1_s.get_width(),     row_y))
            self.screen.blit(v2_s,  (A2_RX - v2_s.get_width(),     row_y))

        # Insight + footer
        div_y = table_bottom + 4
        pygame.draw.line(self.screen, COLOR_DIVIDER,
                         (px + 12, div_y), (px + PANEL_W - 12, div_y), 1)
        ins = font_row.render(self._game_over_insight(a1, a2, eff1, eff2), True, COLOR_DIM)
        self.screen.blit(ins, (px + PANEL_W // 2 - ins.get_width() // 2, div_y + 8))

        footer_div_y = div_y + 32
        pygame.draw.line(self.screen, COLOR_DIVIDER,
                         (px + 12, footer_div_y), (px + PANEL_W - 12, footer_div_y), 1)
        ft = font_row.render("R - Menu     Q - Quit", True, (170, 170, 190))
        self.screen.blit(ft, (px + PANEL_W // 2 - ft.get_width() // 2, footer_div_y + 6))

    def draw_first_move_overlay(self):
        """
        Semi-transparent overlay over the board area prompting the player
        to click a cell for the manual first move.
        """
        bw = self.board.cols * CELL_SIZE
        bh = self.board.rows * CELL_SIZE
        overlay = pygame.Surface((bw, bh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (SIDEBAR_W, SCOREBOARD_H))

        font_big = pygame.font.Font(None, 34)
        line1 = font_big.render("Click any cell to make", True, (255, 255, 255))
        line2 = font_big.render("the first move", True, (255, 255, 255))
        cx = SIDEBAR_W + bw // 2
        cy = SCOREBOARD_H + bh // 2
        self.screen.blit(line1, (cx - line1.get_width() // 2, cy - 22))
        self.screen.blit(line2, (cx - line2.get_width() // 2, cy + 6))

    def _game_over_insight(self, a1, a2, eff1: float, eff2: float) -> str:
        """Pick the most interesting single-line insight about the finished game."""
        # Mine avoidance
        if a1.mines_hit == 0 and a2.mines_hit > 0:
            n = a2.mines_hit
            return (f"{a1.strategy.upper()} avoided all mines — "
                    f"{a2.strategy.upper()} made {n} forced guess{'es' if n > 1 else ''}")
        if a2.mines_hit == 0 and a1.mines_hit > 0:
            n = a1.mines_hit
            return (f"{a2.strategy.upper()} avoided all mines — "
                    f"{a1.strategy.upper()} made {n} forced guess{'es' if n > 1 else ''}")

        # Flag dominance (5+ flag lead)
        total_mines = self.board.num_mines
        if abs(a1.flags - a2.flags) >= 5 and total_mines > 0:
            leader = a1 if a1.flags > a2.flags else a2
            pct = round(leader.flags / total_mines * 100)
            return f"{leader.strategy.upper()} flagged {pct}% of all mines"

        # Efficiency gap (5%+)
        eff_diff = abs(eff1 - eff2)
        if eff_diff >= 5.0:
            leader = a1.strategy.upper() if eff1 > eff2 else a2.strategy.upper()
            return f"{leader} was {eff_diff:.1f}% more efficient per move"

        return "Well played — close game!"

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: dict):
        """
        Callback registered with BattleGame.on_move.
        Receives a GameEvent dict, updates last_event, triggers render.
        """
        self.last_event = event
        if event.get("type") == "mine_hit":
            cell = (event["row"], event["col"])
            self.flash_cell = cell
            self.flash_start = pygame.time.get_ticks()
            self.hit_cells.add(cell)
        self.render()

    def handle_game_over(self, winner):
        """Callback registered with BattleGame.on_game_over."""
        self.winner = winner
        self.render()

    def handle_input(self, pygame_event):
        """
        R → menu (after game over) or restart same config (mid-game)
        Q / Esc → quit
        SPACE → pause / resume
        + / - → speed up / slow down
        """
        key = pygame_event.key

        if key in (pygame.K_q, pygame.K_ESCAPE):
            self.running = False

        elif key == pygame.K_r:
            if self.battle.game_over:
                # Return to menu so the player can change settings
                self.go_to_menu = True
                self.running = False
            else:
                self._restart()

        elif key == pygame.K_SPACE:
            self.paused = not self.paused

        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.move_interval = max(MIN_MOVE_MS, self.move_interval - MOVE_STEP)
            pygame.time.set_timer(MOVE_TIMER, self.move_interval)

        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.move_interval = min(MAX_MOVE_MS, self.move_interval + MOVE_STEP)
            pygame.time.set_timer(MOVE_TIMER, self.move_interval)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def board_to_screen(self, row: int, col: int) -> tuple[int, int]:
        """Convert board (row, col) to top-left pixel coords of that cell."""
        x = SIDEBAR_W + col * CELL_SIZE
        y = SCOREBOARD_H + row * CELL_SIZE
        return x, y

    def screen_to_board(self, x: int, y: int) -> tuple[int, int] | None:
        """Convert pixel coords to board (row, col). Returns None if outside board."""
        bx = x - SIDEBAR_W
        by = y - SCOREBOARD_H
        if bx < 0 or by < 0:
            return None
        col = bx // CELL_SIZE
        row = by // CELL_SIZE
        if 0 <= row < self.board.rows and 0 <= col < self.board.cols:
            return (row, col)
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _restart(self):
        """Recreate board + agents + battle and begin a fresh game (same settings)."""
        board = Board(self.board.rows, self.board.cols, self.board.num_mines)
        agent1 = Agent(1, self._strategy1)
        agent2 = Agent(2, self._strategy2)
        new_battle = BattleGame(board, agent1, agent2, headless=False)
        new_battle.on_move = self.handle_event
        new_battle.on_game_over = self.handle_game_over

        self.battle = new_battle
        self.board = board
        self.last_event = None
        self.winner = None
        self.flash_cell = None
        self.flash_start = None
        self.hit_cells = set()
        self.paused = False
        self.go_to_menu = False
        self.waiting_first_move = False

        if self.first_move == "manual":
            self.waiting_first_move = True
            pygame.time.set_timer(MOVE_TIMER, 0)
        else:
            center_r = board.rows // 2
            center_c = board.cols // 2
            board.reveal(center_r, center_c)
            self.last_event = {
                "type": "reveal", "agent": agent1.agent_id,
                "row": center_r, "col": center_c, "result": "safe",
                "score1": 0, "score2": 0, "turn": 0,
            }
            pygame.time.set_timer(MOVE_TIMER, self.move_interval)
        self.render()


# ------------------------------------------------------------------
# Top-level entry point
# ------------------------------------------------------------------

def launch():
    """
    Show MenuScreen, launch a game with the chosen settings, and loop
    back to the menu whenever the player presses R on the game-over screen.
    Entry point for all GUI modes.
    """
    pygame.init()
    clock      = pygame.time.Clock()
    font       = pygame.font.Font(None, 22)
    font_large = pygame.font.Font(None, 26)

    screen = pygame.display.set_mode((MENU_W, MENU_H))
    pygame.display.set_caption("Minesweeper Battle")

    menu = MenuScreen(screen, font, font_large, clock)

    while True:
        config = menu.run()       # blocks until player clicks START or STATS

        if config == "stats":
            StatsScreen(screen, font, font_large, clock).run()
            screen = pygame.display.set_mode((MENU_W, MENU_H))
            continue

        cfg = DIFFICULTIES[config["difficulty"]]
        board  = Board(cfg["rows"], cfg["cols"], cfg["mines"])
        a1     = Agent(1, config["agent1"])
        a2     = Agent(2, config["agent2"])
        battle = BattleGame(board, a1, a2, headless=False)

        gui            = GUI(battle)
        gui.font       = font
        gui.font_large = font_large
        gui.clock      = clock
        gui.move_interval = SPEED_MS[config["speed"]]

        result = gui.run(first_move=config.get("first_move", "auto"))   # blocks until game over + R or Q

        if result != "menu":
            break                 # Q was pressed; gui.run() called sys.exit() — unreachable
        # else: loop → menu.run() again
