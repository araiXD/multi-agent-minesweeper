# Adversarial Multi-Agent Minesweeper Solver

A Minesweeper AI where two agents compete on the same shared board. Each agent uses a three-tier CSP solver under the hood, but in Battle mode the objective shifts from "minimize my mine risk" to "which move leaves my opponent in the hardest possible position?" Agents evaluate candidate moves using Minimax with Alpha-Beta pruning to look ahead and exploit opponent vulnerability.

This is a CPSC 481 (Artificial Intelligence) capstone project at California State University, Fullerton.

---

## Setup

```bash
pip install -r requirements.txt
```

**Requirements:** Python 3.10+, numpy, pygame

---

## Running

```bash
python main.py                                   # Battle mode, intermediate difficulty
python main.py --mode solo                       # Solo solver with GUI
python main.py --difficulty expert               # Change difficulty (beginner / intermediate / expert)
python main.py --agent1 csp --agent2 tier1       # Mix agent strategies
python main.py --headless --games 100            # Batch benchmark, no GUI
python main.py --headless --games 100 --out results.json
```

A menu screen appears before each game letting you configure mode, difficulty, agent strategies, and animation speed.

---

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / resume auto-play |
| `+` / `-` | Speed up / slow down animation |
| `R` | Return to menu (after game over) |
| `Q` | Quit |

---

## Team

**Course:** CPSC 481 — Artificial Intelligence, California State University, Fullerton

| Name |
|------|
| Alberto Molina |
| Arai Leyva |
| Dylan Ruiz |
