"""
main.py — Entry point

Usage:
    python main.py                          # Battle mode, intermediate, csp vs csp
    python main.py --mode solo              # Solo solver, intermediate
    python main.py --difficulty expert      # Change difficulty
    python main.py --agent1 csp --agent2 tier1   # Mix strategies
    python main.py --headless --games 1000  # Batch benchmark, no GUI
    python main.py --headless --games 1000 --out results.json

Modes:
    battle    — two agents, adversarial scoring, pygame GUI
    solo      — single agent solves board, pygame GUI
    headless  — batch benchmark, no GUI, outputs stats to stdout or JSON
"""

import argparse
import json
from board import Board, DIFFICULTIES
from agent import Agent
from battle import BattleGame
from gui import GUI, launch


def parse_args():
    """
    Parse CLI arguments.

    Returns:
        argparse.Namespace
    """
    p = argparse.ArgumentParser(
        description="Adversarial Multi-Agent Minesweeper Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p.add_argument(
        "--mode",
        choices=["battle", "solo", "headless"],
        default="battle",
        help="game mode (default: battle)",
    )
    # --headless is a shorthand flag that maps to --mode headless
    p.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="shorthand for --mode headless",
    )
    p.add_argument(
        "--difficulty",
        choices=list(DIFFICULTIES.keys()),
        default="intermediate",
        help="board difficulty (default: intermediate)",
    )
    p.add_argument(
        "--agent1",
        choices=["csp", "tier1", "random"],
        default="csp",
        help="strategy for agent 1 (default: csp)",
    )
    p.add_argument(
        "--agent2",
        choices=["csp", "tier1", "random"],
        default="csp",
        help="strategy for agent 2 (default: csp)",
    )
    p.add_argument(
        "--games",
        type=int,
        default=10,
        help="number of games to run in headless mode (default: 10)",
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="path to write JSON results in headless mode",
    )

    args = p.parse_args()

    # --headless overrides --mode
    if args.headless:
        args.mode = "headless"

    return args


def run_battle(args):
    """
    Launch GUI in battle mode — forwards to the menu-based launcher.
    CLI args for difficulty/strategy are ignored; user configures via menu.

    Args:
        args: parsed CLI args
    """
    launch()


def run_solo(args):
    """
    Launch GUI in solo mode — forwards to the menu-based launcher.
    User can select Solo mode inside the menu.

    Args:
        args: parsed CLI args
    """
    launch()


def run_headless(args):
    """
    Run N games in batch without GUI and print stats summary.
    Used for benchmarking agent strategies against each other.

    Outputs per-run stats and aggregate win rate, avg score, avg mines hit.

    Args:
        args: parsed CLI args
    """
    cfg = DIFFICULTIES[args.difficulty]
    n = args.games

    print(f"Headless: {args.agent1} vs {args.agent2}  "
          f"| {n} games | {args.difficulty}")
    print(f"{'-'*58}")
    print(f"  {'#':>4}  {'winner':<9} {'s1':>4}  {'s2':>4}  "
          f"{'diff':>5}  {'hits1':>5}  {'hits2':>5}  {'turns':>5}")
    print(f"{'-'*58}")

    results = []
    for i in range(n):
        board = Board(cfg["rows"], cfg["cols"], cfg["mines"])
        a1 = Agent(agent_id=1, strategy=args.agent1)
        a2 = Agent(agent_id=2, strategy=args.agent2)
        game = BattleGame(board, a1, a2, headless=True)
        game.start(cfg["rows"] // 2, cfg["cols"] // 2)
        s = game.get_stats()
        results.append(s)

        winner_label = f"agent {s['winner']}" if s["winner"] else "tie      "
        diff = s["score1"] - s["score2"]
        print(
            f"  {i+1:>4}  {winner_label:<9} {s['score1']:>4}  {s['score2']:>4}  "
            f"{diff:>+5}  {s['mines_hit1']:>5}  {s['mines_hit2']:>5}  {s['turns']:>5}",
            flush=True,
        )

    print(f"{'-'*58}")
    print_stats_summary(results)

    if args.out:
        payload = {
            "matchup":    f"{args.agent1} vs {args.agent2}",
            "difficulty": args.difficulty,
            "games":      n,
            "results":    results,
            "summary":    _summarize(results, args.agent1, args.agent2),
        }
        with open(args.out, "w") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nSaved -> {args.out}")


def print_stats_summary(results: list[dict]):
    """
    Print a human-readable summary of batch benchmark results.

    Args:
        results: list of stat dicts from BattleGame.get_stats()
    """
    s = _summarize(results, "agent1", "agent2")
    print(f"\n  agent1 win rate     {s['win_rate_1_pct']:>6.1f}%")
    print(f"  agent2 win rate     {s['win_rate_2_pct']:>6.1f}%")
    print(f"  tie rate            {s['tie_rate_pct']:>6.1f}%")
    print(f"  avg score agent1    {s['avg_score_1']:>+7.2f}")
    print(f"  avg score agent2    {s['avg_score_2']:>+7.2f}")
    print(f"  avg differential    {s['avg_score_differential']:>+7.2f}  (agent1 - agent2)")
    print(f"  avg mines hit a1    {s['avg_mines_hit_1']:>7.2f}")
    print(f"  avg mines hit a2    {s['avg_mines_hit_2']:>7.2f}")
    print(f"  avg turns/game      {s['avg_turns']:>7.1f}")


def _summarize(results: list[dict], name1: str, name2: str) -> dict:
    """Aggregate a list of get_stats() dicts into a summary dict."""
    n = len(results)
    if n == 0:
        return {}
    wins1 = sum(1 for r in results if r["winner"] == 1)
    wins2 = sum(1 for r in results if r["winner"] == 2)
    ties  = n - wins1 - wins2
    return {
        "matchup":                f"{name1} vs {name2}",
        "games":                  n,
        "win_rate_1_pct":         round(wins1 / n * 100, 1),
        "win_rate_2_pct":         round(wins2 / n * 100, 1),
        "tie_rate_pct":           round(ties  / n * 100, 1),
        "avg_score_1":            round(sum(r["score1"] for r in results) / n, 2),
        "avg_score_2":            round(sum(r["score2"] for r in results) / n, 2),
        "avg_score_differential": round(sum(r["score1"] - r["score2"] for r in results) / n, 2),
        "avg_mines_hit_1":        round(sum(r["mines_hit1"] for r in results) / n, 2),
        "avg_mines_hit_2":        round(sum(r["mines_hit2"] for r in results) / n, 2),
        "avg_turns":              round(sum(r["turns"] for r in results) / n, 1),
    }


if __name__ == "__main__":
    args = parse_args()

    if args.mode == "battle":
        run_battle(args)
    elif args.mode == "solo":
        run_solo(args)
    elif args.mode == "headless":
        run_headless(args)
