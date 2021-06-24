"""
Add update index
"""

from yoyo import step

__depends__ = {'20210610_01_w7oGH-add-updated-field-to-lookup-table'}

steps = [
    step('DROP INDEX updated_idx', 'CREATE INDEX updated_idx ON posts USING btree ("user", "service", "added")'),
    step('CREATE INDEX updated_idx ON lookup USING btree ("updated")', 'DROP INDEX updated_idx'),
]
