"""Independent same-schema replacement input. Only writes to a NEW external directory."""
import argparse
import csv
import sqlite3
from pathlib import Path


def create(destination: Path, source: Path, empty=False):
    # Use original DDL, not production cleaning or aggregation functions.
    root = Path(__file__).resolve().parents[3]
    destination = destination.resolve()
    if destination == root or root in destination.parents:
        raise ValueError('Synthetic inputs must live outside the checkout')
    destination.mkdir(parents=True, exist_ok=False)
    original = sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)
    db = sqlite3.connect(destination / 'pos.db')
    for table in ('stores', 'products', 'sales'):
        db.execute(original.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0])
    original.close()
    stores = [('X11', '替换·河畔店', '测试餐饮', '新区'), ('X22', '替换·山麓店', '测试餐饮', '西区')]
    products = [('Y91', '桂花新饮', '饮品', 999), ('Y92', '杂粮新碗', '主食', 999), ('Y93', '限定新点心', '点心', 999)]
    # Keep five legitimate lines: one multiline order, another sale, next-day refund, zero amount.
    valid = [('A', '2027/1/2', ' x11 ', 'y91', '2', ' ¥20.01 ', 'cash'),
             ('A', '02-01-2027', 'X11', 'Y92', '1', '5.00', 'cash'),
             ('B', '2027-01-04', 'X22', 'Y93', '3', '30.02', 'card'),
             ('A', '2027-01-05', 'X11', 'Y91', '1', '-3.01', 'cash'),
             ('Z', '2027-01-05', 'X22', 'Y92', '1', '0', 'card')]
    invalid = [('BAD1', 'not-a-date', 'NO', 'NO', '0', '', 'cash'),
               ('BAD2', '2027-01-02', 'NO', 'NO', '0', '', 'cash'),
               ('BAD3', '2027-01-02', 'NO', 'NO', '0', '1', 'cash'),
               ('BAD4', '2027-01-02', 'NO', 'NO', '1', '1', 'cash'),
               ('BAD5', '2027-01-02', 'X11', 'NO', '1', '1', 'cash'),
               ('A', '2027-01-02', 'X11', 'Y91', '2', '20.01', 'cash')]
    sales = [] if empty else valid + invalid
    for table, rows in [('stores', stores), ('products', products), ('sales', sales)]:
        columns = [r[1] for r in db.execute(f'PRAGMA table_info({table})')]
        db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in columns)})', rows)
        with (destination / f'{table}.csv').open('w', newline='') as out:
            writer = csv.writer(out); writer.writerow(columns); writer.writerows(rows)
    db.commit(); db.close()

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('destination', type=Path);p.add_argument('--source', type=Path, required=True);p.add_argument('--empty', action='store_true');a=p.parse_args()
    create(a.destination,a.source,a.empty)
