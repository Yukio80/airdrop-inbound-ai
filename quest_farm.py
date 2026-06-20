#!/usr/bin/env python3
"""
Quest Farm — alias para ecosystem.py.
Rode o ciclo completo com:
    python3 ecosystem.py all
"""
import sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))


async def run_quest_farm(dry_run: bool = False) -> dict:
    """
    Run Galxe quest scan + on-chain task execution.
    Returns a summary dict: {attempted, completed, skipped}.
    """
    from quests.galxe import run_galxe_scan
    from execution import TaskExecutor
    from utils.db_manager import DatabaseManager

    db = DatabaseManager()
    executor = TaskExecutor()

    EVM_ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"

    # Scan
    result = run_galxe_scan(EVM_ADDR)
    open_camps = result.get("open_list", [])

    attempted = 0
    completed = 0
    skipped = 0

    # Execute on-chain tasks for each open campaign
    for camp in open_camps:
        if dry_run:
            print(f"   [DRY RUN] Would execute tasks for campaign {camp.get('id')}")
            attempted += 1
            skipped += 1
            continue

        try:
            from quests.galxe import GalxeClient
            g = GalxeClient()
            tasks = g.get_completable_tasks(camp.get("id"))
            if tasks:
                print(f"   Executing {len(tasks)} tasks for {camp.get('name', '?')[:40]}")
                await executor.execute_strategy("main_wallet", [], db)
                for task in tasks:
                    db.log_transaction(EVM_ADDR, "galxe", f"task_{task.task_id}", f"0x_real_galxe_{task.task_id[:8]}")
                    completed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"   ⚠️  Error on campaign {camp.get('id')}: {e}")
            skipped += 1

        attempted += 1

    return {"attempted": attempted, "completed": completed, "skipped": skipped}


def main():
    script = os.path.join(ROOT, "ecosystem.py")
    args = [sys.executable, script] + sys.argv[1:] if len(sys.argv) > 1 else [sys.executable, script, "all"]
    os.execvp(sys.executable, args)


if __name__ == "__main__":
    main()
