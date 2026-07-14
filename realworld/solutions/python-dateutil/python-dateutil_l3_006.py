import datetime
import dateutil.relativedelta

def solve(year: int, month: int) -> int:
    d = datetime.date(year, month, 1)
    count = 0
    while d.month == month:
        if d.weekday() == 6:
            count += 1
        d += dateutil.relativedelta.relativedelta(days=+1)
    return count
