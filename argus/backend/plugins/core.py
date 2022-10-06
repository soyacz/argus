import logging
from datetime import datetime
from uuid import UUID
from time import time

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from cassandra.cqlengine.usertype import UserType
from flask import Blueprint
from argus.backend.db import ScyllaCluster
from argus.backend.models.web import (
    ArgusTest,
    ArgusGroup,
    ArgusRelease,
    ArgusScheduleGroup,
    ArgusSchedule,
    ArgusScheduleTest,
    ArgusScheduleAssignee
)
from argus.backend.util.enums import TestInvestigationStatus, TestStatus

LOGGER = logging.getLogger(__name__)


class PluginModelBase(Model):
    # Metadata
    build_id = columns.Text(required=True, partition_key=True)
    start_time = columns.DateTime(required=True, primary_key=True, clustering_order="DESC", default=datetime.now)
    id = columns.UUID(index=True, required=True)
    release_id = columns.UUID(index=True)
    group_id = columns.UUID(index=True)
    test_id = columns.UUID(index=True)
    assignee = columns.UUID(index=True)
    status = columns.Text(default=lambda: TestStatus.CREATED.value)
    investigation_status = columns.Text(default=lambda: TestInvestigationStatus.NOT_INVESTIGATED.value)
    heartbeat = columns.Integer(default=lambda: int(time()))
    end_time = columns.DateTime(default=lambda: datetime.utcfromtimestamp(0))
    build_job_url = columns.Text()

    # Test Logs Collection
    logs = columns.List(value_type=columns.Tuple(columns.Text(), columns.Text()))

    @classmethod
    def table_name(cls) -> str:
        return cls.__table_name__

    def assign_categories(self):
        key = self.build_id
        try:
            test: ArgusTest = ArgusTest.get(build_system_id=key)
            self.release_id = test.release_id
            self.group_id = test.group_id
            self.test_id = test.id
        except ArgusTest.DoesNotExist:
            LOGGER.warning("Test entity missing for key \"%s\", run won't be visible until this is corrected", key)

    def get_scheduled_assignee(self) -> UUID:
        """
            Iterate over all schedules (groups and tests) and return first available assignee
        """
        associated_test = ArgusTest.get(build_system_id=self.build_id)
        associated_group = ArgusGroup.get(id=associated_test.group_id)
        associated_release = ArgusRelease.get(id=associated_test.release_id)

        scheduled_groups = ArgusScheduleGroup.filter(
            release_id=associated_release.id,
            group_id=associated_group.id,
        ).all()

        scheduled_tests = ArgusScheduleTest.filter(
            release_id=associated_release.id,
            test_id=associated_test.id
        ).all()

        unique_schedule_ids = {scheduled_obj.schedule_id for scheduled_obj in [
            *scheduled_tests, *scheduled_groups]}

        schedules = ArgusSchedule.filter(
            release_id=associated_release.id,
            id__in=tuple(unique_schedule_ids),
        ).all()

        today = datetime.utcnow()

        valid_schedules = []
        for schedule in schedules:
            if schedule.period_start <= today <= schedule.period_end:
                valid_schedules.append(schedule)

        assignees_uuids = []
        for schedule in valid_schedules:
            assignees = ArgusScheduleAssignee.filter(
                schedule_id=schedule.id
            ).all()
            assignees_uuids.append(*[assignee.assignee for assignee in assignees])

        return assignees_uuids[0] if len(assignees_uuids) > 0 else None

    @classmethod
    def load_test_run(cls, run_id: UUID) -> 'PluginModelBase':
        raise NotImplementedError()

    @classmethod
    def submit_run(cls, request_data: dict) -> 'PluginModelBase':
        raise NotImplementedError()

    @classmethod
    def get_distinct_product_versions(cls, cluster: ScyllaCluster, release_id: UUID) -> list[str]:
        raise NotImplementedError()

    @classmethod
    def get_stats_rows_for_release(cls,  cluster: ScyllaCluster, release_id: UUID) -> list:
        raise NotImplementedError()

    def update_heartbeat(self):
        self.heartbeat = int(time())

    def change_status(self, new_status: TestStatus):
        self.status = new_status.value

    def change_investigation_status(self, new_investigation_status: TestInvestigationStatus):
        self.investigation_status = new_investigation_status.value

    def submit_product_version(self, version: str):
        raise NotImplementedError()

    def submit_logs(self, logs: list[dict]):
        raise NotImplementedError()

    def finish_run(self):
        raise NotImplementedError()


class PluginInfoBase:
    # pylint: disable=too-few-public-methods
    name: str
    controller: Blueprint
    model: PluginModelBase
    all_models: list[Model]
    all_types: list[UserType]
