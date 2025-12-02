from tabulate import tabulate


def generate_html_table(headers: list, rows: list, css_class: str = "data-table") -> str:
    """Generate an HTML table string with the given headers and rows using tabulate."""
    html = tabulate(rows, headers=headers, tablefmt="html")
    html = html.replace("<table>", f'<table class="{css_class}">')
    return html

