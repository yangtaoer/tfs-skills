"""
Batch create and close TFS daily tasks for a date range.
Skips weekends automatically. Accepts optional exclude dates (holidays, PTO).

Usage (from Hermes execute_code or terminal):
    python3 scripts/batch_create_tasks.py --parent 1476929 --from 2026-05-25 --to 2026-05-29 --exclude 2026-05-27 --assigned-to DOMAIN\\alias --area PROJECT\\team

If --pat is omitted, reads from the TFS_PAT environment variable.
If --assigned-to or --area is omitted, reads from TFS_ASSIGNED_TO and TFS_AREA_PATH.
"""
import json, subprocess, sys, os, argparse
from datetime import datetime, timedelta

TFS = os.environ.get("TFS_BASE_URL", "http://dev.tellhowsoft.com/DefaultCollection").rstrip("/")
PROJECT = os.environ.get("TFS_PROJECT", "XiNanArea-New")
AREA = os.environ.get("TFS_AREA_PATH", "")
ASSIGNED_TO = os.environ.get("TFS_ASSIGNED_TO", "")
ACTIVITY = os.environ.get("TFS_ACTIVITY", "开发")
HOURS = float(os.environ.get("TFS_DAILY_HOURS", "8"))


def iteration_path_from_classification_path(path):
    """Convert classification API path to System.IterationPath field value."""
    normalized = path.replace('\\\\', '\\').lstrip('\\')
    prefix = PROJECT + '\\迭代\\'
    if normalized.startswith(prefix):
        return PROJECT + '\\' + normalized[len(prefix):]
    return normalized


def get_iteration_for_date(date_str, pat):
    """Find the System.IterationPath for the task StartDate."""
    result = subprocess.run(
        ['curl', '-s', '-u', f':{pat}',
         f'{TFS}/{PROJECT}/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0',
         '-o', os.path.join(os.environ.get('TEMP', '/tmp'), 'tfs_iters.json')],
        capture_output=True, text=True, timeout=30
    )
    import re
    tmp = os.path.join(os.environ.get('TEMP', '/tmp'), 'tfs_iters.json')
    with open(tmp, 'r', encoding='utf-8') as f:
        raw = f.read()
    segments = re.findall(
        r'"path":\s*"([^"]*迭代[^"]*?)".*?"startDate":\s*"(2026-[^"]+)".*?"finishDate":\s*"(2026-[^"]+)"',
        raw
    )
    target = datetime.strptime(date_str, '%Y-%m-%d').date()
    for path, start, end in segments:
        s = datetime.strptime(start[:10], '%Y-%m-%d').date()
        e = datetime.strptime(end[:10], '%Y-%m-%d').date()
        if s <= target <= e:
            return iteration_path_from_classification_path(path)
    return None


def create_task(date, title, detail, iteration, parent_id, pat, assigned_to, area, activity, hours):
    """Create a single task and return its ID."""
    desc = (f'<div>1、今日完成开发情况（{detail}）<br>'
            f'2、BUG修复情况（无）<br>'
            f'3、需求沟通情况（无）<br>'
            f'4、其他（无）</div>')
    patch_data = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to},
        {"op": "add", "path": "/fields/System.AreaPath", "value": area},
        {"op": "add", "path": "/fields/System.IterationPath", "value": iteration},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": hours},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": hours},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.StartDate", "value": f"{date}T00:30:00Z"},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.FinishDate", "value": f"{date}T09:30:00Z"},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Activity", "value": activity},
        {"op": "add", "path": "/fields/System.Description", "value": desc},
        {"op": "add", "path": "/relations/-", "value": {
            "rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": f"{TFS}/_apis/wit/workItems/{parent_id}"
        }}
    ]

    tmp = os.path.join(os.environ.get('TEMP', '/tmp'), f'tfs_create_{date}.json')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(patch_data, f, ensure_ascii=False)

    url = f"{TFS}/{PROJECT}/_apis/wit/workitems/$%E4%BB%BB%E5%8A%A1?api-version=2.0"
    result = subprocess.run(
        ['curl', '-s', '-u', f':{pat}', '-X', 'POST',
         '-H', 'Content-Type: application/json-patch+json',
         '-d', f'@{tmp}', url],
        capture_output=True, text=True, timeout=30
    )
    resp = json.loads(result.stdout)
    if 'id' not in resp:
        print(f"ERROR creating task for {date}: {json.dumps(resp, ensure_ascii=False)[:300]}")
        return None
    return resp['id']


def close_task(task_id, date, pat, hours):
    """Close a task by setting state to 已关闭."""
    close_data = [
        {"op": "replace", "path": "/fields/System.State", "value": "已关闭"},
        {"op": "replace", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": hours},
        {"op": "replace", "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": hours},
        {"op": "replace", "path": "/fields/Microsoft.VSTS.Scheduling.TargetDate", "value": f"{date}T09:30:00Z"}
    ]

    tmp = os.path.join(os.environ.get('TEMP', '/tmp'), f'tfs_close_{date}.json')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(close_data, f, ensure_ascii=False)

    url = f"{TFS}/_apis/wit/workitems/{task_id}?api-version=2.0"
    result = subprocess.run(
        ['curl', '-s', '-u', f':{pat}', '-X', 'PATCH',
         '-H', 'Content-Type: application/json-patch+json',
         '-d', f'@{tmp}', url],
        capture_output=True, text=True, timeout=30
    )
    resp = json.loads(result.stdout)
    state = resp.get('fields', {}).get('System.State', 'UNKNOWN')
    return state


def main():
    parser = argparse.ArgumentParser(description='Batch create TFS daily tasks')
    parser.add_argument('--parent', required=True, help='Parent user story ID')
    parser.add_argument('--from', dest='from_date', required=True, help='Start date YYYY-MM-DD')
    parser.add_argument('--to', dest='to_date', required=True, help='End date YYYY-MM-DD')
    parser.add_argument('--exclude', nargs='*', default=[], help='Dates to skip (YYYY-MM-DD)')
    parser.add_argument('--title-prefix', default='', help='Prefix for task titles')
    parser.add_argument('--detail', default='', help='Work description for all tasks')
    parser.add_argument('--pat', default='', help='PAT token')
    parser.add_argument('--assigned-to', default=ASSIGNED_TO, help='TFS assignee, e.g. DOMAIN\\alias')
    parser.add_argument('--area', default=AREA, help='TFS area path')
    parser.add_argument('--activity', default=ACTIVITY, help='TFS activity field value')
    parser.add_argument('--hours', type=float, default=HOURS, help='Original/remaining/completed hours')
    args = parser.parse_args()

    pat = args.pat or os.environ.get('TFS_PAT', '')
    if not pat:
        print("ERROR: No PAT provided. Use --pat or set TFS_PAT env var.")
        sys.exit(1)
    if not args.assigned_to:
        print("ERROR: No assignee provided. Use --assigned-to or set TFS_ASSIGNED_TO.")
        sys.exit(1)
    if not args.area:
        print("ERROR: No area path provided. Use --area or set TFS_AREA_PATH.")
        sys.exit(1)

    exclude = set(args.exclude)
    start = datetime.strptime(args.from_date, '%Y-%m-%d').date()
    end = datetime.strptime(args.to_date, '%Y-%m-%d').date()

    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current.isoformat() not in exclude:
            dates.append(current.isoformat())
        current += timedelta(days=1)

    if not dates:
        print("No work days to fill.")
        sys.exit(0)

    print(f"Will create {len(dates)} tasks under parent {args.parent}")
    print(f"Dates: {', '.join(dates)}")

    created = []
    for d in dates:
        iteration = get_iteration_for_date(d, pat)
        if not iteration:
            print(f"WARNING: No iteration found for {d}, skipping")
            continue
        title = f"{args.title_prefix} - {d}" if args.title_prefix else f"日报-{d}"
        detail = args.detail or "日常开发工作"
        task_id = create_task(d, title, detail, iteration, args.parent, pat, args.assigned_to, args.area, args.activity, args.hours)
        if task_id:
            created.append((d, task_id))
            print(f"  Created {task_id} for {d}")

    for d, task_id in created:
        state = close_task(task_id, d, pat, args.hours)
        print(f"  Closed {task_id} for {d} -> {state}")

    print(f"\nDone: {len(created)} tasks created and closed.")


if __name__ == '__main__':
    main()
