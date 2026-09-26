import json
from pathlib import Path

from app.main import app

Path(__file__).with_name('openapi.json').write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + '\n')
