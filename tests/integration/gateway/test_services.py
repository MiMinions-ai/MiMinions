"""Unit tests for gateway.services module (CronService)."""
import json
import pytest
import time
import tempfile
from pathlib import Path

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
        assert s.kind == "at", f"expect CronSchedule kind for at-schedule input is 'at', got {s.kind}"
        assert s.at_ms == 1000000, f"expect CronSchedule at_ms for at-schedule input is 1000000, got {s.at_ms}"
        assert s.every_ms is None, f"expect CronSchedule every_ms remains None for at-schedule input, got {s.every_ms}"
        assert s.expr is None, f"expect CronSchedule expr remains None for at-schedule input, got {s.expr}"
        assert s.tz is None, f"expect CronSchedule timezone remains None for at-schedule input, got {s.tz}"

    def test_every_schedule(self):
        s = CronSchedule(kind="every", every_ms=60000)
        assert s.kind == "every", f"expect CronSchedule kind for every-schedule input is 'every', got {s.kind}"
        assert s.every_ms == 60000, f"expect CronSchedule every_ms for every-schedule input is 60000, got {s.every_ms}"

    def test_cron_schedule(self):
        s = CronSchedule(kind="cron", expr="0 9 * * *", tz="US/Eastern")
        assert s.kind == "cron", f"expect CronSchedule kind for cron expression input is 'cron', got {s.kind}"
        assert s.expr == "0 9 * * *", f"expect CronSchedule stores cron expression as '0 9 * * *', got {s.expr}"
        assert s.tz == "US/Eastern", f"expect CronSchedule stores timezone as 'US/Eastern', got {s.tz}"


class TestCronPayload:
    def test_defaults(self):
        p = CronPayload()
        assert p.kind == "agent_turn", f"expect CronPayload default kind is 'agent_turn', got {p.kind}"
        assert p.message == "", f"expect CronPayload default message is empty string '', got {p.message}"
        assert p.deliver is False, f"expect CronPayload default deliver flag is False, got {p.deliver}"
        assert p.channel is None, f"expect CronPayload default channel is None, got {p.channel}"
        assert p.to is None, f"expect CronPayload default recipient is None, got {p.to}"

    def test_custom(self):
        p = CronPayload(kind="system_event", message="hi", deliver=True, channel="tg", to="u1")
        assert p.kind == "system_event", f"expect CronPayload custom kind is stored as 'system_event', got {p.kind}"
        assert p.message == "hi", f"expect CronPayload custom message is stored as 'hi', got {p.message}"


class TestCronJobState:
    def test_defaults(self):
        s = CronJobState()
        assert s.next_run_at_ms is None, f"expect CronJobState default next_run_at_ms is None, got {s.next_run_at_ms}"
        assert s.last_run_at_ms is None, f"expect CronJobState default last_run_at_ms is None, got {s.last_run_at_ms}"
        assert s.last_status is None, f"expect CronJobState default last_status is None, got {s.last_status}"
        assert s.last_error is None, f"expect CronJobState default last_error is None, got {s.last_error}"


class TestCronJob:
    def test_creation(self):
        j = CronJob(id="abc", name="test")
        assert j.id == "abc", f"expect CronJob id is preserved from constructor as 'abc', got {j.id}"
        assert j.name == "test", f"expect CronJob name is preserved from constructor as 'test', got {j.name}"
        assert j.enabled is True, f"expect CronJob enabled defaults to True on creation, got {j.enabled}"
        assert j.delete_after_run is False, f"expect CronJob delete_after_run defaults to False on creation, got {j.delete_after_run}"

    def test_defaults(self):
        j = CronJob(id="x", name="y")
        assert j.schedule.kind == "every", f"expect CronJob default schedule kind is 'every', got {j.schedule.kind}"
        assert j.payload.kind == "agent_turn", f"expect CronJob default payload kind is 'agent_turn', got {j.payload.kind}"
        assert j.state.next_run_at_ms is None, f"expect CronJob default state next_run_at_ms is None before scheduling, got {j.state.next_run_at_ms}"
        assert j.created_at_ms == 0, f"expect new CronJob created_at_ms default is 0 before persistence, got {j.created_at_ms}"
        assert j.updated_at_ms == 0, f"expect new CronJob updated_at_ms default is 0 before persistence, got {j.updated_at_ms}"


class TestCronStore:
    def test_defaults(self):
        s = CronStore()
        assert s.version == 1, f"expect CronStore default schema version is 1, got {s.version}"
        assert s.jobs == [], f"expect CronStore default jobs list is empty as [], got {s.jobs}"

    def test_with_jobs(self):
        jobs = [CronJob(id="1", name="a"), CronJob(id="2", name="b")]
        s = CronStore(jobs=jobs)
        job_count = len(s.jobs)
        assert job_count == 2, f"expect CronStore preserves two provided jobs in jobs list as 2, got {job_count}"


# ── Helper function tests ────────────────────────────────────────────


class TestNowMs:
    def test_returns_int(self):
        result = _now_ms()
        result_is_int = isinstance(result, int)
        result_type = type(result)
        assert result_is_int, f"expect _now_ms returns int timestamp as True, got {result_type}"
        assert result > 0, f"expect result > 0, got {result}"

    def test_close_to_current_time(self):
        now = int(time.time() * 1000)
        result = _now_ms()
        delta_ms = abs(result - now)
        assert delta_ms < 1000, f"expect abs(result - now) < 1000, got {delta_ms}"  # Within 1 second


class TestComputeNextRun:
    def test_at_future(self):
        future_ms = _now_ms() + 60000
        result = _compute_next_run(CronSchedule(kind="at", at_ms=future_ms), _now_ms())
        assert result == future_ms, f"expect future_ms as {future_ms}, got {result}"

    def test_at_past(self):
        past_ms = _now_ms() - 60000
        result = _compute_next_run(CronSchedule(kind="at", at_ms=past_ms), _now_ms())
        assert result is None, f"expect _compute_next_run returns None for one-shot at schedule in the past, got {result}"

    def test_at_none(self):
        result = _compute_next_run(CronSchedule(kind="at"), _now_ms())
        assert result is None, f"expect _compute_next_run returns None for at schedule missing at_ms, got {result}"

    def test_every(self):
        now = _now_ms()
        result = _compute_next_run(CronSchedule(kind="every", every_ms=5000), now)
        assert result == now + 5000, f"expect now + 5000, got {result}"

    def test_every_zero_interval(self):
        result = _compute_next_run(CronSchedule(kind="every", every_ms=0), _now_ms())
        assert result is None, f"expect _compute_next_run returns None for every schedule with zero interval, got {result}"

    def test_every_negative_interval(self):
        result = _compute_next_run(CronSchedule(kind="every", every_ms=-1), _now_ms())
        assert result is None, f"expect _compute_next_run returns None for every schedule with negative interval, got {result}"

    def test_every_none(self):
        result = _compute_next_run(CronSchedule(kind="every"), _now_ms())
        assert result is None, f"expect _compute_next_run returns None for every schedule missing every_ms, got {result}"

    def test_cron_expression(self):
        """Test cron expression computes a future time."""
        schedule = CronSchedule(kind="cron", expr="* * * * *")  # every minute
        result = _compute_next_run(schedule, _now_ms())
        if result is not None:  # croniter may not be installed
            assert result > _now_ms() - 1000, f"expect result > _now_ms() - 1000, got {result}"

    def test_cron_no_expr(self):
        result = _compute_next_run(CronSchedule(kind="cron"), _now_ms())
        assert result is None, f"expect _compute_next_run returns None for cron schedule missing expression, got {result}"

    def test_unknown_kind(self):
        result = _compute_next_run(CronSchedule(kind="unknown"), _now_ms())  # type: ignore
        assert result is None, f"expect _compute_next_run returns None for unknown schedule kind, got {result}"


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
            assert svc.store_path == path, f"expect path as {path}, got {svc.store_path}"
            assert svc.on_job is None, f"expect CronService default on_job callback is None, got {svc.on_job}"
            assert svc._running is False, f"expect CronService starts with running flag False before start, got {svc._running}"
            assert svc._store is None, f"expect CronService starts with unloaded store None before start, got {svc._store}"


class TestCronServiceLifecycle:
    async def test_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            assert svc._running is True, f"expect CronService running flag is True after start, got {svc._running}"
            assert svc._store is not None, f"expect value is not None, got {svc._store}"
            store_file_exists = path.exists()
            assert store_file_exists, f"expect start creates cron store file when missing as True, got {store_file_exists}"

            await svc.stop()
            assert svc._running is False, f"expect CronService running flag is False after stop, got {svc._running}"
            assert svc._timer_task is None, f"expect CronService clears timer task after stop as None, got {svc._timer_task}"

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

            listed_jobs = svc.list_jobs()
            listed_jobs_count = len(listed_jobs)
            assert listed_jobs_count == 1, f"expect start loads one existing persisted cron job as 1, got {listed_jobs_count}"
            listed_job_name = listed_jobs[0].name
            assert listed_job_name == "preloaded", f"expect start loads existing persisted cron job name as 'preloaded', got {listed_job_name}"
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

            assert job.id, f"expect add_job returns job with non-empty id as {True}, got {bool(job.id)} with id {job.id}"
            assert job.name == "my-job", f"expect add_job stores cron job name as 'my-job', got {job.name}"
            assert job.enabled is True, f"expect add_job creates enabled cron job by default as True, got {job.enabled}"
            assert job.payload.message == "ping", f"expect add_job stores cron payload message as 'ping', got {job.payload.message}"
            assert job.state.next_run_at_ms is not None, f"expect value is not None, got {job.state.next_run_at_ms}"
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
            job_has_id = bool(job.id)
            assert job_has_id, f"expect add_job returns job with non-empty id as {True}, got {job_has_id} with id {job.id}"

            assert job.payload.deliver is True, f"expect add_job stores delivery enabled option as True, got {job.payload.deliver}"
            assert job.payload.channel == "telegram", f"expect add_job stores delivery channel option as 'telegram', got {job.payload.channel}"
            assert job.payload.to == "user1", f"expect add_job stores delivery recipient option as 'user1', got {job.payload.to}"
            assert job.delete_after_run is True, f"expect add_job stores delete_after_run option as True, got {job.delete_after_run}"
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
            saved_jobs_count = len(data["jobs"])
            assert saved_jobs_count == 1, f"expect add_job persistence writes exactly one job record as 1, got {saved_jobs_count}"
            assert data["jobs"][0]["name"] == "persistent", f"expect add_job persistence writes job name as 'persistent' to jobs.json, got {data['jobs'][0]['name']}"

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

            removed = svc.remove_job(job.id)
            assert removed is True, f"expect remove_job returns True when existing job id is removed, got {removed}"
            remaining_enabled_jobs = len(svc.list_jobs())
            assert remaining_enabled_jobs == 0, f"expect remove_job deletes job from enabled listing as 0, got count {remaining_enabled_jobs}"
            await svc.stop()

    async def test_remove_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            removed = svc.remove_job("nonexistent")
            assert removed is False, f"expect remove_job returns False when job id does not exist, got {removed}"
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
            assert result is not None, f"expect value is not None, got {result}"
            assert result.enabled is False, f"expect enable_job(enabled=False) marks job enabled flag as False, got {result.enabled}"
            assert result.state.next_run_at_ms is None, f"expect disabled job clears next_run_at_ms as None, got {result.state.next_run_at_ms}"

            # Should not appear in default listing
            enabled_jobs_count = len(svc.list_jobs())
            assert enabled_jobs_count == 0, f"expect disabled job excluded from default list_jobs as 0, got count {enabled_jobs_count}"
            all_jobs_count = len(svc.list_jobs(include_disabled=True))
            assert all_jobs_count == 1, f"expect list_jobs(include_disabled=True) includes disabled job as 1, got {all_jobs_count}"
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
            assert result is not None, f"expect value is not None, got {result}"
            assert result.enabled is True, f"expect enable_job(enabled=True) restores job enabled flag as True, got {result.enabled}"
            assert result.state.next_run_at_ms is not None, f"expect value is not None, got {result.state.next_run_at_ms}"
            await svc.stop()

    async def test_enable_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            missing_job_result = svc.enable_job("nope")
            assert missing_job_result is None, f"expect enable_job returns None when job id does not exist, got {missing_job_result}"
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
            assert ok is True, f"expect run_job(force=True) returns True for existing enabled job, got {ok}"
            assert results == ["manual"], f"expect manual run callback appends executed job name list as ['manual'], got {results}"
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
            assert ok is False, f"expect run_job(force=False) returns False for disabled job, got {ok}"
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
            assert ok is True, f"expect run_job(force=True) returns True for disabled job when forced, got {ok}"
            expected_ran = [job.id]
            assert ran == expected_ran, f"expect forced run callback captures executed job id list as {expected_ran}, got {ran}"
            await svc.stop()

    async def test_run_nonexistent_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            ok = await svc.run_job("nope")
            assert ok is False, f"expect run_job returns False when job id does not exist, got {ok}"
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
            assert ok is True, f"expect run_job returns True even when callback error is captured, got {ok}"

            # Verify error was recorded
            store = svc._load_store()
            executed = [j for j in store.jobs if j.id == job.id][0]
            assert executed.state.last_status == "error", f"expect run_job records callback failure status as 'error', got {executed.state.last_status}"
            assert "handler error" in executed.state.last_error, f"expect contains 'handler error', got {executed.state.last_error}"
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
            assert ok is True, f"expect run_job returns True for existing job when no callback is configured, got {ok}"

            store = svc._load_store()
            executed = [j for j in store.jobs if j.id == job.id][0]
            assert executed.state.last_status == "ok", f"expect run_job without callback records successful status as 'ok', got {executed.state.last_status}"
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
            assert ok is True, f"expect one-shot delete_after_run job executes successfully as True, got {ok}"
            all_jobs_after_run = len(svc.list_jobs(include_disabled=True))
            assert all_jobs_after_run == 0, f"expect one-shot delete_after_run job removed after execution as 0, got count {all_jobs_after_run}"
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
            assert ok is True, f"expect one-shot keep-history job executes successfully as True, got {ok}"

            jobs = svc.list_jobs(include_disabled=True)
            jobs_count = len(jobs)
            assert jobs_count == 1, f"expect one-shot keep-history job remains stored after execution as 1, got {jobs_count}"
            assert jobs[0].enabled is False, f"expect one-shot keep-history job is disabled after execution as False, got {jobs[0].enabled}"
            assert jobs[0].state.next_run_at_ms is None, f"expect one-shot keep-history job clears next_run_at_ms after execution as None, got {jobs[0].state.next_run_at_ms}"
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
            assert ok is True, f"expect recurring job executes successfully when run manually as True, got {ok}"

            store = svc._load_store()
            updated = [j for j in store.jobs if j.id == job.id][0]
            assert updated.state.next_run_at_ms is not None, f"expect value is not None, got {updated.state.next_run_at_ms}"
            assert updated.state.next_run_at_ms >= original_next, f"expect updated.state.next_run_at_ms >= original_next as {original_next}, got {updated.state.next_run_at_ms}"
            assert updated.state.last_run_at_ms is not None, f"expect value is not None, got {updated.state.last_run_at_ms}"
            assert updated.state.last_status == "ok", f"expect recurring run updates last execution status as 'ok', got {updated.state.last_status}"
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
            assert jobs[0].name == "near", f"expect list_jobs sorting returns nearest next-run job first as 'near', got {jobs[0].name}"
            assert jobs[1].name == "far", f"expect list_jobs sorting returns later next-run job second as 'far', got {jobs[1].name}"
            await svc.stop()

    async def test_list_jobs_excludes_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            svc.add_job("enabled", CronSchedule(kind="every", every_ms=1000), "x")
            j2 = svc.add_job("disabled", CronSchedule(kind="every", every_ms=1000), "x")
            svc.enable_job(j2.id, enabled=False)

            enabled_jobs_count = len(svc.list_jobs())
            assert enabled_jobs_count == 1, f"expect default list_jobs returns only the one enabled job as 1, got {enabled_jobs_count}"
            all_jobs_count = len(svc.list_jobs(include_disabled=True))
            assert all_jobs_count == 2, f"expect list_jobs(include_disabled=True) returns enabled and disabled jobs as 2, got {all_jobs_count}"
            await svc.stop()


class TestCronServiceStatus:
    async def test_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            status = svc.status()
            assert status["running"] is True, f"expect status reports running True after service start, got {status['running']}"
            assert status["jobs"] == 0, f"expect status reports 0 jobs before adding any, got {status['jobs']}"

            svc.add_job("a", CronSchedule(kind="every", every_ms=1000), "x")
            status = svc.status()
            assert status["jobs"] == 1, f"expect status reports one job after adding a cron job as 1, got {status['jobs']}"
            assert status["next_wake_at_ms"] is not None, f"expect value is not None, got {status['next_wake_at_ms']}"
            await svc.stop()


class TestCronServiceStoreIO:
    async def test_corrupted_store_file(self):
        """Corrupted JSON should load an empty store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            path.write_text("not valid json", encoding="utf-8")

            svc = CronService(store_path=path)
            await svc.start()
            assert svc._store is not None, f"expect value is not None, got {svc._store}"
            loaded_jobs_count = len(svc._store.jobs)
            assert loaded_jobs_count == 0, f"expect corrupted store fallback loads empty job list as 0, got {loaded_jobs_count}"
            await svc.stop()

    async def test_save_store_no_store(self):
        """_save_store with no store loaded should be no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            svc._save_store()  # Should not raise
            store_file_exists = path.exists()
            assert not store_file_exists, f"expect _save_store no-op when store is None, got file exists={store_file_exists}"

    async def test_external_modification_reload(self):
        """Store should reload when the file is modified externally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()

            svc.add_job("original", CronSchedule(kind="every", every_ms=1000), "x")
            initial_jobs_count = len(svc.list_jobs())
            assert initial_jobs_count == 1, f"expect precondition before external clear has one listed job as 1, got {initial_jobs_count}"

            # Externally clear the file
            import time as _time
            _time.sleep(0.05)
            path.write_text(json.dumps({"version": 1, "jobs": []}), encoding="utf-8")

            # Force reload
            svc._store = None
            jobs = svc.list_jobs()
            jobs_count = len(jobs)
            assert jobs_count == 0, f"expect external store clear is reflected after reload as 0, got {jobs_count} jobs"
            await svc.stop()


class TestCronServiceTimer:
    async def test_arm_timer_no_jobs(self):
        """_arm_timer with no jobs should not create a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()
            # No jobs, so no timer
            assert svc._timer_task is None, f"expect _arm_timer leaves timer task None when service has no jobs, got {svc._timer_task}"
            await svc.stop()

    async def test_arm_timer_not_running(self):
        """_arm_timer when not running should not create a task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            svc._running = False
            svc._store = CronStore()
            svc._arm_timer()
            assert svc._timer_task is None, f"expect _arm_timer leaves timer task None when service is not running, got {svc._timer_task}"

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
            next_wake = svc._get_next_wake_ms()
            assert next_wake is None, f"expect _get_next_wake_ms returns None when store is not loaded, got {next_wake}"

    async def test_next_wake_no_enabled_jobs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "jobs.json"
            svc = CronService(store_path=path)
            await svc.start()
            next_wake = svc._get_next_wake_ms()
            assert next_wake is None, f"expect _get_next_wake_ms returns None when no enabled jobs exist, got {next_wake}"
            await svc.stop()
