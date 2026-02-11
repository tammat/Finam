from finam_bot.storage_sqlite import StorageSQLite
from finam_bot.instruments import asset_class_by_symbol

def main():
    s = StorageSQLite()

    rows = s.conn.execute(
        """
        SELECT instrument
        FROM positions
        WHERE asset_class IS NULL OR asset_class = ''
        """
    ).fetchall()

    updated = 0
    for (instrument,) in rows:
        ac = asset_class_by_symbol(instrument)
        s.conn.execute(
            "UPDATE positions SET asset_class=? WHERE instrument=?",
            (ac, instrument),
        )
        updated += 1

    s.conn.commit()
    print("asset_class updated:", updated)

if __name__ == "__main__":
    main()