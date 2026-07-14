import datetime
import humanize

def solve(total_seconds: int) -> str:
    return humanize.precisedelta(datetime.timedelta(seconds=total_seconds), suppress=['seconds', 'milliseconds'])
