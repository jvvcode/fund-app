"""Populate the security master with a starter universe. Thin CLI wrapper
around db/seed/seed_universe.py so it lives alongside the other admin scripts."""
from db.seed.seed_universe import run

if __name__ == "__main__":
    run()
