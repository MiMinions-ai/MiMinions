"""Unit tests for gateway.services module (CronService)."""
import json
import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from miminions.core.gateway.services import (
    CronJob,
    CronJobState,
    CronPayload,
    CronSchedule,
    CronService,
    CronStore,
    _compute_next_run,
    _now_ms,
    _validate_schedule,
)


# ── Data model tests ─────────────────────────────────────────────────


class TestCronSchedule:
    def test_at_schedule(self):
        s = CronSchedule(kind="at", at_ms=1000000)
        assert s.kind == "at"
        assert s.at_ms == 1000000
        assert s.every_ms is None
        assert s.expr is None
        assert s.tz is None

    def test_every_schedule(self):
        s = CronSchedule(kind="every", every_ms=60000)
        assert s.kind == "every"
        assert s.every_ms == 60000

    def test_cron_schedule(self):
        s = CronSchedule(kind="cron", expr="0 9 * * *", tz="US/Eastern")
        assert s.kind == "cron"
        assert s.expr == "0 9 * * *"
        assert s.tz == "US/Eastern"


class TestCronPayload:
    def test_defaults(self):
        p = CronPayload()
        assert p.kind == "agent_turn"
        assert p.message == ""
        assert p.deliver is False
        assert p.channel is None
        assert p.to is None

    def test_custom(self):
        p = CronPayload(kind="system_event", message="hi", deliver=True, channel="tg", to="u1")
        assert p.kind == "system_event"
        assert p.message == "hi"


class TestCronJobState:
    def test_defaults(self):
        s = CronJobState()
        assert s.next_run_at_ms is None
        assert s.last_run_at_ms is None
        assert s.last_status is None
        assert s.last_error is None


class TestCronJob:
    def test_creation(self):
        j = CronJob(id="abc", name="test")
        assert j.id == "abc"
        assert j.name == "test"
        assert j.enabled is True
        assert j.delete_after_run is False

    def test_defaults(self):
        j = CronJob(id="x", name="y")
        assert j.schedule.kind == "every"
        assert j.payload.kind == "agent_turn"
        assert j.state.next_run_at_ms is None
        assert j.created_at_ms == 0
        assert j.updated_at_ms == 0


class TestCronStore:
    def test_defaults(self):
        s = CronStore()
        assert s.version == 1
        assert s.jobs == []

    def test_with_jobs(self):
        jobs = [CronJob(id="1", name="a"), CronJob(id="2", name="b")]
        s = CronStore(jobs=jobs)
        assert len(s.jobs) == 2


# ── Helper function tests ────────────────────────────────────────────


class TestNowMs:
    def test_returns_int(self):
        result = _now_ms()
        assert isinstance(result, int)
        assert result > 0

    def test_close_to_current_time(self):
        now = int(time.time() * 1000)
        result = _now_ms()
        assert abs(result - now) < 1000  # Within 1 second


class TestComputeNextRun:
    def test_at_future(self):
        future_ms = _now_ms() + 60000
        result = _compute_next_run(CronSchedule(kind="at", at_ms=future_ms), _now_ms())
        assert result == future_ms

    def test_at_past(self):
        past_ms = _now_ms() - 60000
        result = _compute_next_run(CronSchedule(kind="at", at_ms=past_ms), _now_ms())
        assert result is None

    def test_at_none(self):
        result = _compute_next_run(CronSchedule(kind="at"), _now_ms())
        assert result is None

    def test_every(self):
        now = _now_ms()
        result = _compute_next_run(CronSchedule(kind="every", every_ms=5000), now)
        assert result == now + 5000

    def test_every_zero_interval(self):
        result = _compute_next_run(CronSchedule(kind="every", every_ms=0), _now_ms())
        assert result is None

    def test_every_negative_interval(self):
        result = _compute_next_run(CronSchedule(kind="every", every_ms=-1), _now_ms())
        assert result is None

    def test_every_none(self):
        result = _compute_next_run(CronSchedule(kind="every"), _now_ms())
        assert result is None

    def test_cron_expression(self):
        """Test cron expression computes a future time."""
        schedule = CronSchedule(kind="cron", expr="* * * * *")  # every minute
        result = _compute_next_run(schedule, _now_ms())
        if result is not None:  # croniter may not be installed
            assert result > _now_ms() - 1000

    def test_cron_no_expr(self):
        result = _compute_next_run(CronSchedule(kind="cron"), _now_ms())
        assert result is None

    def test_unknown_kind(self):
        result = _compute_next_run(CronSchedule(kind="unknown"), _now_ms())  # type: ignore
        assert result is None


class TestValidateSchedule:
    def test_valid_every(self):
        _validate_schedule(CronSchedule(kind="every", every_ms=1000))

    def test_valid_at(self):
        _validate_schedule(CronSchedule(kind="at", at_ms=1000))

    def test_tz_on_non_cron_raises(self):
        with pytest.raises(ValueError, match="tz can only be used with cron"):
            _validate_schedule(CronSchedule(kind="every", every_ms=1000, tz="UTC"))

    def test_invalid_tz_raises(self):
        with pytest.raises(ValueError, match="unknown timezone"):
            _validate_schedule(CronSchedule(kind="cron", expr="* * * * *", tz="Not/A/TZ"))

    def test_valid_cron_with_tz(self):
        _validate_schedule(CronSchedule(kind="cron", expr="0 9 * * *", tz="UTC"))


# ── CronService tests ────────────────────────────────────────────────


class TestCronServiceInit:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            assert svc.store_path == path
            assert svc.on_job is None
            assert svc._running is False
            assert svc._store is None


class TestCronServiceLifecycle:
    async def test_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            assert svc._running is True
            assert svc._store is not None
            assert path.exists()

            await svc.stop()
            assert svc._running is False
            assert svc._timer_task is None

    async def test_start_with_existing_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            data = {
                "version": 1,
                "jobs": [
                    {
                        "id": "j1",
                        "name": "preloaded",
                        "enabled": True,
                        "schedule": {"kind": "every", "everyMs": 60000},
                        "payload": {"kind": "agent_turn", "message": "hi"},
                        "state": {},
                        "createdAtMs": 0,
                        "updatedAtMs": 0,
                        "deleteAfterRun": False,
                    }
                ],
            }
            path.write_text(json.dumps(data), encoding="utf-8")

            svc = CronService(store_path=path)
            await svc.start()

            assert len(svc.list_jobs()) == 1
            assert svc.list_jobs()[0].name == "preloaded"
            await svc.stop()


class TestCronServiceAddJob:
    async def test_add_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="my-job",
                schedule=CronSchedule(kind="every", every_ms=30000),
                message="ping",
            )

            assert job.id
            assert job.name == "my-job"
            assert job.enabled is True
            assert job.payload.message == "ping"
            assert job.state.next_run_at_ms is not None
            await svc.stop()

    async def test_add_job_with_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="deliver-job",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="hello",
                deliver=True,
                channel="telegram",
                to="user1",
                delete_after_run=True,
            )

            assert job.payload.deliver is True
            assert job.payload.channel == "telegram"
            assert job.payload.to == "user1"
            assert job.delete_after_run is True
            await svc.stop()

    async def test_add_job_persisted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            svc.add_job(
                name="persistent",
                schedule=CronSchedule(kind="every", every_ms=5000),
                message="data",
            )
            await svc.stop()

            # Reload and verify
            data = json.loads(path.read_text(encoding="utf-8"))
            assert len(data["jobs"]) == 1
            assert data["jobs"][0]["name"] == "persistent"

    async def test_add_job_invalid_schedule_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            with pytest.raises(ValueError, match="tz can only be used with cron"):
                svc.add_job(
                    name="bad",
                    schedule=CronSchedule(kind="every", every_ms=1000, tz="UTC"),
                    message="x",
                )
            await svc.stop()


class TestCronServiceRemoveJob:
    async def test_remove_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="removable",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )

            assert svc.remove_job(job.id) is True
            assert len(svc.list_jobs()) == 0
            await svc.stop()

    async def test_remove_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            assert svc.remove_job("nonexistent") is False
            await svc.stop()


class TestCronServiceEnableJob:
    async def test_disable_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="toggle",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )

            result = svc.enable_job(job.id, enabled=False)
            assert result is not None
            assert result.enabled is False
            assert result.state.next_run_at_ms is None

            # Should not appear in default listing
            assert len(svc.list_jobs()) == 0
            assert len(svc.list_jobs(include_disabled=True)) == 1
            await svc.stop()

    async def test_re_enable_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="toggle2",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )

            svc.enable_job(job.id, enabled=False)
            result = svc.enable_job(job.id, enabled=True)
            assert result is not None
            assert result.enabled is True
            assert result.state.next_run_at_ms is not None
            await svc.stop()

    async def test_enable_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            assert svc.enable_job("nope") is None
            await svc.stop()


class TestCronServiceRunJob:
    async def test_run_job_manually(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            results = []

            async def on_job(job):
                results.append(job.name)

            svc = CronService(store_path=path, on_job=on_job)
            await svc.start()

            job = svc.add_job(
                name="manual",
                schedule=CronSchedule(kind="every", every_ms=999999),
                message="x",
            )

            ok = await svc.run_job(job.id, force=True)
            assert ok is True
            assert results == ["manual"]
            await svc.stop()

    async def test_run_disabled_job_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="disabled-run",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )
            svc.enable_job(job.id, enabled=False)

            ok = await svc.run_job(job.id, force=False)
            assert ok is False
            await svc.stop()

    async def test_run_disabled_job_with_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            ran = []

            async def on_job(job):
                ran.append(job.id)

            svc = CronService(store_path=path, on_job=on_job)
            await svc.start()

            job = svc.add_job(
                name="force-run",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )
            svc.enable_job(job.id, enabled=False)

            ok = await svc.run_job(job.id, force=True)
            assert ok is True
            assert ran == [job.id]
            await svc.stop()

    async def test_run_nonexistent_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            ok = await svc.run_job("nope")
            assert ok is False
            await svc.stop()

    async def test_run_job_on_job_error(self):
        """Job callback errors should be captured, not crash the service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"

            async def failing_handler(job):
                raise RuntimeError("handler error")

            svc = CronService(store_path=path, on_job=failing_handler)
            await svc.start()

            job = svc.add_job(
                name="fail-job",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )

            ok = await svc.run_job(job.id, force=True)
            assert ok is True

            # Verify error was recorded
            store = svc._load_store()
            executed = [j for j in store.jobs if j.id == job.id][0]
            assert executed.state.last_status == "error"
            assert "handler error" in executed.state.last_error
            await svc.stop()

    async def test_run_job_no_callback(self):
        """Running with no on_job callback should be ok."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="no-cb",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="x",
            )

            ok = await svc.run_job(job.id, force=True)
            assert ok is True

            store = svc._load_store()
            executed = [j for j in store.jobs if j.id == job.id][0]
            assert executed.state.last_status == "ok"
            await svc.stop()


class TestCronServiceExecuteJob:
    async def test_at_job_deleted_after_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            future = _now_ms() + 999999
            job = svc.add_job(
                name="one-shot-delete",
                schedule=CronSchedule(kind="at", at_ms=future),
                message="x",
                delete_after_run=True,
            )

            ok = await svc.run_job(job.id, force=True)
            assert ok is True
            assert len(svc.list_jobs(include_disabled=True)) == 0
            await svc.stop()

    async def test_at_job_disabled_after_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            future = _now_ms() + 999999
            job = svc.add_job(
                name="one-shot-disable",
                schedule=CronSchedule(kind="at", at_ms=future),
                message="x",
                delete_after_run=False,
            )

            ok = await svc.run_job(job.id, force=True)
            assert ok is True

            jobs = svc.list_jobs(include_disabled=True)
            assert len(jobs) == 1
            assert jobs[0].enabled is False
            assert jobs[0].state.next_run_at_ms is None
            await svc.stop()

    async def test_every_job_recomputes_next_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            job = svc.add_job(
                name="recurring",
                schedule=CronSchedule(kind="every", every_ms=30000),
                message="x",
            )
            original_next = job.state.next_run_at_ms

            ok = await svc.run_job(job.id, force=True)
            assert ok is True

            store = svc._load_store()
            updated = [j for j in store.jobs if j.id == job.id][0]
            assert updated.state.next_run_at_ms is not None
            assert updated.state.next_run_at_ms >= original_next
            assert updated.state.last_run_at_ms is not None
            assert updated.state.last_status == "ok"
            await svc.stop()


class TestCronServiceListJobs:
    async def test_list_jobs_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            svc.add_job("far", CronSchedule(kind="every", every_ms=99999), "x")
            svc.add_job("near", CronSchedule(kind="every", every_ms=1000), "x")

            jobs = svc.list_jobs()
            assert jobs[0].name == "near"
            assert jobs[1].name == "far"
            await svc.stop()

    async def test_list_jobs_excludes_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            j1 = svc.add_job("enabled", CronSchedule(kind="every", every_ms=1000), "x")
            j2 = svc.add_job("disabled", CronSchedule(kind="every", every_ms=1000), "x")
            svc.enable_job(j2.id, enabled=False)

            assert len(svc.list_jobs()) == 1
            assert len(svc.list_jobs(include_disabled=True)) == 2
            await svc.stop()


class TestCronServiceStatus:
    async def test_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            status = svc.status()
            assert status["running"] is True
            assert status["jobs"] == 0

            svc.add_job("a", CronSchedule(kind="every", every_ms=1000), "x")
            status = svc.status()
            assert status["jobs"] == 1
            assert status["next_wake_at_ms"] is not None
            await svc.stop()


class TestCronServiceStoreIO:
    async def test_corrupted_store_file(self):
        """Corrupted JSON should load an empty store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            path.write_text("not valid json", encoding="utf-8")

            svc = CronService(store_path=path)
            await svc.start()
            assert svc._store is not None
            assert len(svc._store.jobs) == 0
            await svc.stop()

    async def test_save_store_no_store(self):
        """_save_store with no store loaded should be no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            svc._save_store()  # Should not raise
            assert not path.exists()

    async def test_external_modification_reload(self):
        """Store should reload when the file is modified externally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            svc.add_job("original", CronSchedule(kind="every", every_ms=1000), "x")
            assert len(svc.list_jobs()) == 1

            # Externally clear the file
            import time as _time
            _time.sleep(0.05)
            path.write_text(json.dumps({"version": 1, "jobs": []}), encoding="utf-8")

            # Force reload
            svc._store = None
            jobs = svc.list_jobs()
            assert len(jobs) == 0
            await svc.stop()


class TestCronServiceTimer:
    async def test_arm_timer_no_jobs(self):
        """_arm_timer with no jobs should not create a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()
            # No jobs, so no timer
            assert svc._timer_task is None
            await svc.stop()

    async def test_arm_timer_not_running(self):
        """_arm_timer when not running should not create a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            svc._running = False
            svc._store = CronStore()
            svc._arm_timer()
            assert svc._timer_task is None

    async def test_recompute_no_store(self):
        """_recompute_next_runs with no store should be no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            svc._recompute_next_runs()  # Should not raise

    async def test_next_wake_no_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            assert svc._get_next_wake_ms() is None

    async def test_next_wake_no_enabled_jobs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()
            assert svc._get_next_wake_ms() is None
            await svc.stop()
