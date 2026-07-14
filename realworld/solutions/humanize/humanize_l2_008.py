import datetime
import humanize

def solve(dt_str: str, when_str: str) -> str:
    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
    when = datetime.datetime.strptime(when_str, '%Y-%m-%dT%H:%M:%S')
    return humanize.naturaltime(dt, when=when)
