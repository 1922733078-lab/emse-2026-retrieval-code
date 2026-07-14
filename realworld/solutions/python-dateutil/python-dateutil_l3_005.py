import datetime
import dateutil.relativedelta

def solve(d: datetime.date, n: int) -> str:
    cur = d
    added = 0
    while added < n:
        cur += dateutil.relativedelta.relativedelta(days=+1)
        if cur.weekday() < 5:
            added += 1
    return cur.isoformat()
