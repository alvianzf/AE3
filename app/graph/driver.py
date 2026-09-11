"""The shared Neo4j driver — one connection pool for the whole process,
same pattern the old app/knowledge.py used."""
from __future__ import annotations

import neo4j

from ..config import get_config

cfg = get_config()

_driver: neo4j.Driver | None = None


def get_driver() -> neo4j.Driver:
    global _driver
    if _driver is None:
        _driver = neo4j.GraphDatabase.driver(
            cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password)
        )
    return _driver


def session() -> neo4j.Session:
    return get_driver().session(database=cfg.neo4j_database)
