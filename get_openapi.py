# Copyright (c) 2024.
"""Extracts OpenAPI json from FastAPI"""

from pathlib import Path

import yaml
from uvicorn.importer import import_from_string

if __name__ == "__main__":
    app = import_from_string("main:app")  # pyright: ignore[reportAny]
    openapi = app.openapi()  # pyright: ignore[reportAny]

    with Path.open(Path("openapi.yaml"), "w") as f:
        yaml.dump(openapi, f, sort_keys=False)
