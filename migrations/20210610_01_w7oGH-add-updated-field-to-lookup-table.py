"""
Add updated field to lookup table
"""

from yoyo import step
from datetime import datetime
from psycopg2.extras import RealDictCursor

__depends__ = {'20210529_01_LO1OU-add-primary-keys-to-discord-posts'}

steps = [
    step(
        "ALTER TABLE lookup ADD COLUMN updated timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE lookup DROP COLUMN updated"
    )
]