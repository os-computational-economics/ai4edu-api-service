# Copyright (c) 2024.
"""Script to run the unicorn server locally."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        reload=True,
    )
