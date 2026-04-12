"""
uat/run_uat.py — Orchestrator for all UAT test suites.
Run with:  python uat/run_uat.py [suite_key ...]

Without arguments all suites are run.  Pass one or more suite keys to run a
subset, e.g.:  python uat/run_uat.py calendar
"""

import sys
import os
import importlib
import subprocess

# ── Suite registry ─────────────────────────────────────────────────────────────

# Each entry: key -> module name within uat/ (no .py extension)
SUITES = {
    'calendar': 'test_calendar',
}

# ── Runner ─────────────────────────────────────────────────────────────────────

def run_suite(key, module_name):
    """Run a test module as a subprocess and return (passed, failed)."""
    uat_dir  = os.path.dirname(os.path.abspath(__file__))
    script   = os.path.join(uat_dir, f'{module_name}.py')
    root_dir = os.path.dirname(uat_dir)

    print(f'\n{"="*60}')
    print(f'  Suite: {key}  ({module_name}.py)')
    print(f'{"="*60}')

    result = subprocess.run(
        [sys.executable, script],
        cwd=root_dir,
    )
    return result.returncode == 0


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(SUITES.keys())

    unknown = [k for k in requested if k not in SUITES]
    if unknown:
        print(f'Unknown suite(s): {", ".join(unknown)}')
        print(f'Available: {", ".join(SUITES.keys())}')
        sys.exit(1)

    results = {}
    for key in requested:
        results[key] = run_suite(key, SUITES[key])

    print(f'\n{"="*60}')
    print('  UAT Summary')
    print(f'{"="*60}')
    all_passed = True
    for key, ok in results.items():
        status = 'PASSED' if ok else 'FAILED'
        print(f'  {key:<20}  {status}')
        if not ok:
            all_passed = False

    print()
    if all_passed:
        print('All UAT suites PASSED')
    else:
        print('One or more suites FAILED')
        sys.exit(1)


if __name__ == '__main__':
    main()
