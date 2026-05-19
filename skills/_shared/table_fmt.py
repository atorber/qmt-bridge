"""终端 ASCII 表格（stdlib，无第三方依赖）。"""

from __future__ import annotations


def _display_width(text: str) -> int:
    w = 0
    for ch in str(text):
        if "\u4e00" <= ch <= "\u9fff":
            w += 2
        else:
            w += 1
    return w


def _pad_cell(text: str, width: int, align: str) -> str:
    gap = max(0, width - _display_width(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def print_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    aligns: list[str] | None = None,
    footer: list[str] | None = None,
) -> None:
    """打印框线表格。"""
    if not headers:
        return
    n = len(headers)
    aligns = (aligns or ["left"] * n)[:n]
    if len(aligns) < n:
        aligns = aligns + ["left"] * (n - len(aligns))

    matrix: list[list[str]] = [headers, *rows]
    if footer:
        matrix.append(footer)

    widths = [0] * n
    for row in matrix:
        for i in range(n):
            cell = str(row[i]) if i < len(row) else ""
            widths[i] = max(widths[i], _display_width(cell), _display_width(headers[i]))

    def border(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def render(cells: list[str]) -> str:
        parts = [
            _pad_cell(str(cells[i]) if i < len(cells) else "", widths[i], aligns[i])
            for i in range(n)
        ]
        return "│ " + " │ ".join(parts) + " │"

    print(border("┌", "┬", "┐"))
    print(render(headers))
    print(border("├", "┼", "┤"))
    for row in rows:
        print(render(row))
    if footer:
        print(border("├", "┼", "┤"))
        print(render(footer))
    print(border("└", "┴", "┘"))
