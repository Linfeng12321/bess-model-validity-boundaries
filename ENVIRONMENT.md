# Software environment

| Task | Dependencies | Recorded environment |
|---|---|---|
| Inspect files and verify saved evidence | Python standard library | Python 3.12.14 on Windows 11 |
| Run the original device studies | Numerical and logical solvers | Python 3.12.14, NumPy 2.3.5, SciPy 1.16.2, HiGHS 1.8.0 and Z3 4.15.3 |
| Run later exact network routes | Additional symbolic and logical packages | cvc5 and SymPy versions must be taken from their route records |
| Edit native graphs held separately | Licensed scientific plotting software | OriginPro 2026; not needed for saved evidence checks |

[Recorded_Environment.json](Recorded_Environment.json) retains solver options and hardware context. [requirements-for-original-solvers.txt](requirements-for-original-solvers.txt) records the corresponding package pins. The [optional rerun guide](docs/optional_full_research_rerun.md) identifies route specific requirements.

The saved evidence entry was checked with Python 3.12.14 on Windows 11. This environment statement does not claim a new full solver run or matching computation times on other machines.
