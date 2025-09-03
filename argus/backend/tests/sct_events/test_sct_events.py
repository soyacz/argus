from dataclasses import asdict
from datetime import datetime, UTC
import logging

import pytest

from argus.backend.models.web import ArgusRelease, ArgusGroup, ArgusTest
from argus.backend.plugins.sct.testrun import SCTEventSeverity, SCTTestRun
from argus.backend.service.client_service import ClientService
from argus.backend.plugins.sct.service import SCTService
from argus.backend.service.testrun import TestRunService
from argus.backend.tests.conftest import get_fake_test_run
from argus.common.sct_types import RawEventPayload

LOGGER = logging.getLogger(__name__)

def test_submit_event(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_data: RawEventPayload = {
        "duration": 30.0,
        "event_type": "end",
        "known_issue": None,
        "message": "Sample event - body contains\nmultiple lines.",
        "nemesis_name": None,
        "nemesis_status": None,
        "node": None,
        "received_timestamp": None,
        "run_id": run.id,
        "severity": SCTEventSeverity.CRITICAL.value,
        "target_node": None,
        "ts": datetime.now(tz=UTC).timestamp()
    }

    _ = sct_service.submit_event(str(run.id), event_data)

    all_events = run.get_all_events()
    assert len(all_events) == 1, "Event not found"


def test_get_events_by_severity(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_template: RawEventPayload = {
        "duration": 30.0,
        "event_type": "end",
        "known_issue": None,
        "message": "Sample event - body contains\nmultiple lines.",
        "nemesis_name": None,
        "nemesis_status": None,
        "node": None,
        "received_timestamp": None,
        "run_id": run.id,
        "severity": None,
        "target_node": None,
        "ts": None
    }

    events = []
    for i in range(3):
        raw_event = dict(event_template)
        raw_event["ts"] = datetime.now(tz=UTC).timestamp() - i
        raw_event["severity"] = SCTEventSeverity.CRITICAL.value
        events.append(raw_event)

    for i in range(10):
        raw_event = dict(event_template)
        raw_event["ts"] = datetime.now(tz=UTC).timestamp() - i
        raw_event["severity"] = SCTEventSeverity.NORMAL.value
        events.append(raw_event)

    for event in events:
        _ = sct_service.submit_event(str(run.id), event)

    all_events = run.get_all_events()
    assert len(all_events) == 13, "Event not found"

    events_by_severity = run.get_events_by_severity(SCTEventSeverity.CRITICAL)
    assert len(events_by_severity) == 3, "Not all events were added or count mismatch"


def test_submit_event_sparse_fields(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_data: RawEventPayload = {
        "message": "Sample event - body contains\nmultiple lines.",
        "run_id": run.id,
        "severity": SCTEventSeverity.CRITICAL.value,
        "ts": datetime.now(tz=UTC).timestamp(),
        "event_type": "DatabaseEvent"
    }

    _ = sct_service.submit_event(str(run.id), event_data)

    all_events = run.get_all_events()
    assert len(all_events) == 1, "Event not found"


def test_submit_event_ordering(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_template: RawEventPayload = {
        "message": None,
        "run_id": run.id,
        "severity": SCTEventSeverity.CRITICAL.value,
        "ts": None,
        "event_type": "DatabaseEvent"
    }

    for i in range(100):
        event_data = dict(event_template)
        event_data["ts"] = datetime.now(tz=UTC).timestamp() - 1
        event_data["message"] = f"This is event {i}"
        _ = sct_service.submit_event(str(run.id), event_data)


    all_events = run.get_all_events()
    assert len(all_events) > 0 and all_events[0]["message"] == "This is event 99", "Incorrect event in set!"

    # Insert more
    for i in range(100):
        event_data = dict(event_template)
        event_data["ts"] = datetime.now(tz=UTC).timestamp() + 1
        event_data["message"] = f"This is event r{i}"
        _ = sct_service.submit_event(str(run.id), event_data)

    all_events = run.get_all_events()
    assert len(all_events) > 0 and all_events[0]["message"] == "This is event r99", "Incorrect event in set!"


def test_fetch_partition_limit(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_template: RawEventPayload = {
        "message": None,
        "run_id": run.id,
        "severity": SCTEventSeverity.CRITICAL.value,
        "ts": None,
        "event_type": "DatabaseEvent"
    }

    for i in range(200):
        event_data = dict(event_template)
        event_data["ts"] = datetime.now(tz=UTC).timestamp() - 1
        event_data["message"] = f"This is event {i}"
        _ = sct_service.submit_event(str(run.id), event_data)

    for i in range(200):
        event_data = dict(event_template)
        event_data["severity"] = SCTEventSeverity.NORMAL.value
        event_data["ts"] = datetime.now(tz=UTC).timestamp() - 1
        event_data["message"] = f"This is event {i}"
        _ = sct_service.submit_event(str(run.id), event_data)

    all_events = run.get_events_limited(run.id)
    assert len(all_events) == 200, "Incorrect event in set!"


def test_submit_event_with_nemesis_data(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_data: RawEventPayload = {
        "duration": 30.0,
        "event_type": "NemesisEvent",
        "known_issue": "http://example.com/yes/1",
        "message": "Sample event - body contains\nmultiple lines.",
        "nemesis_name": "NemesisName",
        "nemesis_status": "passed",
        "run_id": run.id,
        "severity": SCTEventSeverity.CRITICAL.value,
        "target_node": "127.0.0.1",
        "ts": datetime.now(tz=UTC).timestamp()
    }

    _ = sct_service.submit_event(str(run.id), event_data)

    all_events = run.get_all_events()
    assert len(all_events) == 1, "Event not found"


def test_submit_event_db_event(client_service: ClientService, sct_service: SCTService, testrun_service: TestRunService, fake_test: ArgusTest):
    run_type, run_req = get_fake_test_run(fake_test)
    client_service.submit_run(run_type, asdict(run_req))
    run: SCTTestRun = testrun_service.get_run(run_type, run_req.run_id)

    event_data: RawEventPayload = {
        "duration": 30.0,
        "event_type": "DatabaseEvent",
        "message": "Sample event - body contains\nmultiple lines.",
        "node": "127.0.0.1",
        "received_timestamp": "2025-05-01T19:30:21.666Z",
        "run_id": run.id,
        "severity": SCTEventSeverity.CRITICAL.value,
        "ts": datetime.now(tz=UTC).timestamp()
    }

    _ = sct_service.submit_event(str(run.id), event_data)

    all_events = run.get_all_events()
    assert len(all_events) == 1, "Event not found"
