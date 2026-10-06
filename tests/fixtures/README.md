# SismoLab test fixtures

Run the automated suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

The JSON files can also be selected in the application's load dialog:

| File | Purpose |
| --- | --- |
| `load_insertions.json` | Load unique events by insertion; includes magnitude/depth thresholds and populated-zone examples. |
| `load_duplicate_ids_invalid.json` | Reject a batch containing a repeated event ID. |
| `scenario_normal_topology.json` | Restore an explicitly linked, balanced AVL topology. All seven events are old and low-priority, so the branch is eligible for archiving. |
| `scenario_stress_topology.json` | Restore a valid but unbalanced topology in stress mode; use the recovery action to rebalance it. |
| `scenario_invalid_topology.json` | Reject topology whose stored balance factor is inconsistent. |
| `report_burst.json` | Restore five queued station reports and process them one by one with **Process Next**. |
| `archive_mixed_priority.json` | Show that an old branch is not eligible when it contains a higher-priority event. |
| `rotations/ll.json`, `rotations/rr.json`, `rotations/lr.json`, `rotations/rl.json` | Ordered insertion sequences that exercise each AVL rotation case. |

Use the load dialog to select each file. A regular events file exercises insertion loading; a `SismoLabScenario` file restores the saved topology and settings. The rotation files are event batches, so select them one at a time and inspect the AVL/BST view and metrics after loading.

The fixtures use their own IDs and fictional data. Load a fresh scenario before each demonstration. The invalid fixtures are expected to display an error and leave the current scenario unchanged.

The automated tests validate these fixtures and core controller operations. Some visual interactions, such as clicking through the GUI, still need to be demonstrated manually.
