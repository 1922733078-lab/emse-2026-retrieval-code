import dateutil.parser
import dateutil.relativedelta

def solve(s1: str, s2: str) -> str:
    d1 = dateutil.parser.isoparse(s1).date()
    d2 = dateutil.parser.isoparse(s2).date()
    rd = dateutil.relativedelta.relativedelta(d2, d1)
    return f"{rd.years}y{rd.months}m{rd.days}d"
