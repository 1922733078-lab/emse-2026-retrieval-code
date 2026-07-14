def intword(value: NumberOrString, format: str = "%.1f") -> str:
    """Converts a large integer to a friendly text representation.

    Works best for numbers over 1 million. For example, 1_000_000 becomes "1.0 million",
    1200000 becomes "1.2 million" and "1_200_000_000" becomes "1.2 billion". Supports up
    to decillion (33 digits) and googol (100 digits).

    Examples:
        ```pycon
        >>> intword("100")
        '100'
        >>> intword("12400")
        '12.4 thousand'
        >>> intword("1000000")
        '1.0 million'
        >>> intword(1_200_000_000)
        '1.2 billion'
        >>> intword(8100000000000000000000000000000000)
        '8.1 decillion'
        >>> intword(None)
        'None'
        >>> intword("1234000", "%0.3f")
        '1.234 million'

        ```

    Args:
        value (int, float, str): Integer to convert.
        format (str): To change the number of decimal or general format of the number
            portion.

    Returns:
        str: Friendly text representation as a string, unless the value passed could not
            be coaxed into an `int`.
    """
    try:
        if not math.isfinite(float(value)):
            return _format_not_finite(float(value))
        value = int(value)
    except (TypeError, ValueError):
        return str(value)

    if value < 0:
        value *= -1
        negative_prefix = "-"
    else:
        negative_prefix = ""

    if value < powers[0]:
        return negative_prefix + str(value)

    for ordinal_, power in enumerate(powers[1:], 1):
        if value < power:
            chopped = value / float(powers[ordinal_ - 1])
            powers_difference = powers[ordinal_] / powers[ordinal_ - 1]
            if float(format % chopped) == powers_difference:
                chopped = value / float(powers[ordinal_])
                singular, plural = human_powers[ordinal_]
                return (
                    negative_prefix
                    + " ".join(
                        [format, _ngettext(singular, plural, math.ceil(chopped))]
                    )
                ) % chopped

            singular, plural = human_powers[ordinal_ - 1]
            return (
                negative_prefix
                + " ".join([format, _ngettext(singular, plural, math.ceil(chopped))])
            ) % chopped

    return negative_prefix + str(value)
