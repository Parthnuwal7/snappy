"""The SQLAlchemy engine is configured to shed dead/stale pooled connections.

This is half of the fix for orphaned `idle in transaction` connections: a worker
killed mid-request can leave a dead connection in the pool; pool_pre_ping drops
it on next checkout, and pool_recycle caps how long any connection lives.
"""


def test_engine_options_harden_pool(app):
    opts = app.config.get('SQLALCHEMY_ENGINE_OPTIONS') or {}
    assert opts.get('pool_pre_ping') is True
    assert isinstance(opts.get('pool_recycle'), int) and opts['pool_recycle'] > 0
