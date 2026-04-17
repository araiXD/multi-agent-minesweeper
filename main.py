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
from board import Board, DIFFICULTIES
from agent import Agent
from battle import BattleGame
from gui import GUI


def parse_args():
    """
    Parse CLI arguments.

    Returns:
        argparse.Namespace
    """
    pass


def run_battle(args):
    """
    Set up and launch a single Battle mode game with GUI.

    Args:
        args: parsed CLI args
    """
    pass


def run_solo(args):
    """
    Set up and launch a solo solver game with GUI.

    Args:
        args: parsed CLI args
    """
    pass


def run_headless(args):
    """
    Run N games in batch without GUI and print stats summary.
    Used for benchmarking agent strategies against each other.

    Outputs per-run stats and aggregate win rate, avg score, avg mines hit.

    Args:
        args: parsed CLI args
    """
    pass


def print_stats_summary(results: list[dict]):
    """
    Print a human-readable summary of batch benchmark results.

    Args:
        results: list of stat dicts from BattleGame.get_stats()
    """
    pass


if __name__ == "__main__":
    args = parse_args()

    if args.mode == "battle":
        run_battle(args)
    elif args.mode == "solo":
        run_solo(args)
    elif args.mode == "headless":
        run_headless(args)
