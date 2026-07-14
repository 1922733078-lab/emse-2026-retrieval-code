def solve(subject: str, resource: str) -> bool:
    return parse_subject(subject)["department"] == parse_resource(resource)["owner"]
