import dateutil.parser

def solve(s: str, fmt: str) -> str:
    return dateutil.parser.isoparse(s).strftime(fmt)
