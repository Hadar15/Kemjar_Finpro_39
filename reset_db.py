from pathlib import Path

import app


database = Path(app.DATABASE)
if database.exists():
    database.unlink()
app.init_db()
print(f"Database reset successfully: {database}")
