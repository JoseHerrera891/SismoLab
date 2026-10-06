# SismoLab AVL

A desktop application for simulating the management of a seismic observatory. The active event catalog uses an AVL tree ordered by `(priority, magnitude, event ID)`. The project also implements an unbalanced binary search tree (BST) for structural comparison.

> **Academic use only:** the territory and simulator rules are fictional. This application does not predict earthquakes or assess real seismic risk.

## Requirements

- Python 3.10 or later.
- PyQt6.
- `test_zones.json` in the project root. The controller loads this file at startup to configure the map zones.

## Installation

From the repository root, create and activate a virtual environment.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install PyQt6
```

### Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install PyQt6
```

## Run

With the virtual environment active, run this command from the repository root:

```bash
python main.py
```

Select an event row in the table to update, mark as reviewed, or delete it. Manual event creation uses the simulation clock as the event time and generates the event ID automatically.

## Features

- Create, search, correct, review, and delete active events.
- Calculate event priorities and order events in the AVL tree by `(P, M, ID)`.
- View the map, zones, events, and AVL, BST, and association trees.
- Queue station reports in FIFO order and process them one at a time.
- Enable stress mode to defer rotations, then request AVL balance recovery.
- Configure association time and distance limits, the costly-access limit, and the archive age threshold.
- Query pending events, magnitude ranges, shallow events by date, associations, and costly-access events.
- Archive an eligible branch, view archived events, and undo actions.
- Verify the AVL structure and inspect traversals and system metrics.
- Save and load JSON scenarios, including topology, configuration, queue, zones, metrics, active events, and archived events.

## Data Files

- `test_zones.json`: fictional populated and unpopulated zones. This file is required at startup and must remain in the project root.
- `test_data.json`: a small sample event dataset in a JSON format supported by the event loader.

Complete scenarios are saved using the `SismoLabScenario` format, version 2. The export dialog lets you choose the output path.

## Tests

From the repository root, with the virtual environment active, run:

```bash
python -m unittest discover -s tests -v
```

The current suite tests controller behavior including structural auditing, queries, stress mode, archiving, FIFO processing, undo, and scenario restoration.

## Project Structure

```text
core/                       Event model, AVL, BST, queue, stack, and stress manager
services/                   Zones, associations, persistence, and auditing
gui/                        Application interface, map, and tree visualizations
sismolab_controller.py      System rules and operation coordination
main.py                     Application entry point
test_zones.json             Fictional scenario zones
test_data.json              Sample events
tests/                       Automated tests
```

## Core Rules

- Numeric event IDs range from 1 to 999999.
- Priority is derived from magnitude, depth, and whether the epicenter is in a populated zone.
- The tree key is lexicographic: priority, magnitude, and numeric event ID.
- Events retain their identity; AVL rotations do not change event data.