import dateutil.parser
import dateutil.relativedelta

def solve(s: str) -> tuple:
    dt = dateutil.parser.isoparse(s)
    start = dt - dateutil.relativedelta.relativedelta(days=dt.weekday())
    end = start + dateutil.relativedelta.relativedelta(days=6)
    return (start.date().isoformat(), end.date().isoformat())
