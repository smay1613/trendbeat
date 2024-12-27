def format_price(price, diff=False):
    return f'{int(price):,}$' if not diff else f'{"+" if price >= 0 else ""}{int(price):,}$'


def format_number(number, dollars=True):
    return f'{number:,.2f}'.rstrip('0').rstrip('.') + ('$' if dollars else '')
