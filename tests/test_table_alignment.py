import pytest

from reporting.summary_tables import _format_table


def test_numeric_columns_right_aligned():
    headers = ["Name", "Value", "Percent"]
    rows = [["a", "1", "1.0"], ["bb", "23", "12.5"], ["ccc", "456", "100"]]
    table = _format_table(headers, rows)
    lines = table.splitlines()
    # compute width of first column to find start of numeric columns
    w1 = max(len("Name"), max(len(r[0]) for r in rows))
    w2 = max(len("Value"), max(len(r[1]) for r in rows))
    # first data line index is 2 (0 header,1 separator)
    for idx, row in enumerate(rows, start=2):
        line = lines[idx]
        cell_val = line[w1 + 3 : w1 + 3 + w2]
        assert cell_val.startswith(" " * (w2 - len(row[1])) + row[1])
