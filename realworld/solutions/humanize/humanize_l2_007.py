import datetime
import humanize

def solve(seconds: float) -> str:
    return humanize.naturaldelta(datetime.timedelta(seconds=seconds), minimum_unit='milliseconds')
