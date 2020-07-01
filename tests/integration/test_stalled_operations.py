import datetime

import pytest
from broker.extensions import db
from broker.models import Operation
from broker.tasks.cron import scan_for_stalled_pipelines

import tests.lib.factories as factories


def test_finds_stalled_operations(clean_db):
    stalled_operation = factories.OperationFactory.create(
        id=1234, state="in progress", action="Deprovision"
    )

    unstalled = factories.OperationFactory.create(
        id=4321, state="in progress", action="Deprovision"
    )

    db.session.add(unstalled)
    db.session.add(stalled_operation)
    db.session.commit()

    ok = datetime.datetime.now() - datetime.timedelta(hours=1)
    ok = ok.replace(tzinfo=datetime.timezone.utc)
    too_old = datetime.datetime.now() - datetime.timedelta(hours=2, minutes=1)
    too_old = too_old.replace(tzinfo=datetime.timezone.utc)

    # have to do this manually to skip the onupdate on the model
    db.session.execute(
        "UPDATE operation SET updated_at = :time WHERE id = 1234",
        {"time": too_old.isoformat()},
    )
    db.session.execute(
        "UPDATE operation SET updated_at = :time WHERE id = 4321",
        {"time": ok.isoformat()},
    )
    db.session.commit()

    # sanity check - did we actually set updated_at?
    stalled_operation = Operation.query.get(1234)
    assert stalled_operation.updated_at.isoformat() == too_old.isoformat()

    assert scan_for_stalled_pipelines() == [1234]


@pytest.mark.parametrize("state", ["completed", "failed"])
def test_does_not_find_ended_operations(clean_db, state):
    complete = factories.OperationFactory.create(
        id=1234, state=state, action="Deprovision"
    )

    too_old = datetime.datetime.now() - datetime.timedelta(hours=2)
    too_old = too_old.replace(tzinfo=datetime.timezone.utc)

    # have to do this manually to skip the onupdate on the model
    db.session.execute(
        "UPDATE operation SET updated_at = :time WHERE id = 1234",
        {"time": too_old.isoformat()},
    )
    db.session.commit()
    complete = Operation.query.get(1234)

    assert scan_for_stalled_pipelines() == []


def test_does_not_find_canceled_operations(clean_db):
    complete = factories.OperationFactory.create(
        id=1234,
        state="in progress",
        action="Deprovision",
        canceled_at=datetime.datetime.now(),
    )

    too_old = datetime.datetime.now() - datetime.timedelta(hours=2)
    too_old = too_old.replace(tzinfo=datetime.timezone.utc)

    # have to do this manually to skip the onupdate on the model
    db.session.execute(
        "UPDATE operation SET updated_at = :time WHERE id = 1234",
        {"time": too_old.isoformat()},
    )
    db.session.commit()
    complete = Operation.query.get(1234)

    assert scan_for_stalled_pipelines() == []
