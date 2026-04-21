"""
bench.py — Headless benchmark runner for Minesweeper Battle.

Runs N games per matchup and reports win rates, score differentials,
mine-hit rates, and turn counts. Results saved to bench_results.json.
"""

import json
import time

from board import Board, DIFFICULTIES
from agent import Agent
from battle import BattleGame


def run_matchup(n: int, strategy1: str, strategy2: str, difficulty: str = "intermediate") -> list[dict]:
    """Run n headless games, printing one result line per game."""
    cfg = DIFFICULTIES[difficulty]
    stats = []

    label = f"{strategy1} vs {strategy2}"
    print(f"\n{'='*56}")
    print(f"  {label}  |  {n} games  |  {difficulty}")
    print(f"{'-'*56}")
    print(f"  {'#':>4}  {'winner':<8}  {'s1':>4}  {'s2':>4}  "
          f"{'diff':>5}  {'hits1':>5}  {'hits2':>5}  {'turns':>5}")
    print(f"{'-'*56}")

    for i in range(n):
        board = Board(cfg["rows"], cfg["cols"], cfg["mines"])
        a1 = Agent(agent_id=1, strategy=strategy1)
        a2 = Agent(agent_id=2, strategy=strategy2)
        game = BattleGame(board, a1, a2, headless=True)

        center_r = cfg["rows"] // 2
        center_c = cfg["cols"] // 2
        game.start(center_r, center_c)

        s = game.get_stats()
        stats.append(s)

        winner_label = (
            f"agent {s['winner']}" if s["winner"] else "tie    "
        )
        diff = s["score1"] - s["score2"]
        print(
            f"  {i+1:>4}  {winner_label:<8}  {s['score1']:>4}  {s['score2']:>4}  "
            f"{diff:>+5}  {s['mines_hit1']:>5}  {s['mines_hit2']:>5}  {s['turns']:>5}",
            flush=True,
        )

    return stats


def summarize(stats: list[dict], name1: str, name2: str) -> dict:
    n = len(stats)
    wins1 = sum(1 for s in stats if s["winner"] == 1)
    wins2 = sum(1 for s in stats if s["winner"] == 2)
    ties  = n - wins1 - wins2

    return {
        "matchup":                f"{name1} vs {name2}",
        "games":                  n,
        "win_rate_1_pct":         round(wins1 / n * 100, 1),
        "win_rate_2_pct":         round(wins2 / n * 100, 1),
        "tie_rate_pct":           round(ties  / n * 100, 1),
        "avg_score_1":            round(sum(s["score1"] for s in stats) / n, 2),
        "avg_score_2":            round(sum(s["score2"] for s in stats) / n, 2),
        "avg_score_differential": round(sum(s["score1"] - s["score2"] for s in stats) / n, 2),
        "avg_mines_hit_1":        round(sum(s["mines_hit1"] for s in stats) / n, 2),
        "avg_mines_hit_2":        round(sum(s["mines_hit2"] for s in stats) / n, 2),
        "avg_turns":              round(sum(s["turns"] for s in stats) / n, 1),
    }


def print_summary(r: dict, elapsed: float):
    n1, n2 = r["matchup"].split(" vs ")
    w = 56
    print(f"\n  Summary")
    print(f"{'-'*w}")
    print(f"  {n1:8s} win rate     {r['win_rate_1_pct']:>6.1f}%")
    print(f"  {n2:8s} win rate     {r['win_rate_2_pct']:>6.1f}%")
    print(f"  Tie rate             {r['tie_rate_pct']:>6.1f}%")
    print(f"{'-'*w}")
    print(f"  Avg score  {n1:8s}  {r['avg_score_1']:>+7.2f}")
    print(f"  Avg score  {n2:8s}  {r['avg_score_2']:>+7.2f}")
    print(f"  Avg differential     {r['avg_score_differential']:>+7.2f}  ({n1} - {n2})")
    print(f"{'-'*w}")
    print(f"  Avg mines hit {n1:5s}  {r['avg_mines_hit_1']:>7.2f}")
    print(f"  Avg mines hit {n2:5s}  {r['avg_mines_hit_2']:>7.2f}")
    print(f"  Avg turns/game       {r['avg_turns']:>7.1f}")
    print(f"  Elapsed              {elapsed:>7.1f}s  ({elapsed/r['games']:.2f}s/game)")
    print(f"{'='*w}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=20,
                        help="games per matchup (default 20)")
    args = parser.parse_args()

    N = args.games
    all_results = []

    # ---- CSP vs tier1 ----
    t0 = time.time()
    raw_ct = run_matchup(N, "csp", "tier1")
    elapsed_ct = time.time() - t0
    r_ct = summarize(raw_ct, "csp", "tier1")
    r_ct["elapsed_s"] = round(elapsed_ct, 1)
    print_summary(r_ct, elapsed_ct)
    all_results.append(r_ct)

    # ---- CSP vs random ----
    t1 = time.time()
    raw_cr = run_matchup(N, "csp", "random")
    elapsed_cr = time.time() - t1
    r_cr = summarize(raw_cr, "csp", "random")
    r_cr["elapsed_s"] = round(elapsed_cr, 1)
    print_summary(r_cr, elapsed_cr)
    all_results.append(r_cr)

    out = "bench_results.json"
    with open(out, "w") as fh:
        json.dump(all_results, fh, indent=2)
    print(f"\nSaved -> {out}")
