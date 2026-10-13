"""Shared acknowledgement and event rendering for execution commands."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import errno

import click

from miminions.execution import ExecutionRequest, ExecutionService


def attachment_options(func):
    func = click.option("--detach", is_flag=True, help="Return after accepting work; follow with task tail.")(func)
    return click.option("--attach", is_flag=True, help="Stream task events until completion (default).")(func)


def validate_attachment(attach, detach):
    if attach and detach:
        raise click.UsageError("--attach and --detach are mutually exclusive.")


def is_interactive():
    return sys.stdin.isatty() and sys.stderr.isatty()


def _echo(*args, **kwargs):
    try:
        click.echo(*args, **kwargs)
    except OSError as exc:
        # Windows CRT can report a closed anonymous pipe as EINVAL instead of EPIPE.
        if not isinstance(exc, BrokenPipeError) and not (os.name == "nt" and exc.errno == errno.EINVAL):
            raise
        # Otherwise interpreter shutdown can turn the requested exit 130 into exit 120.
        stream = sys.stderr if kwargs.get("err") else sys.stdout
        try:
            descriptor = stream.fileno()
            null = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(null, descriptor)
            finally:
                os.close(null)
        except (OSError, ValueError, AttributeError):
            pass
        raise BrokenPipeError(str(exc)) from exc


def follow_task(service, task_id, *, after=0, as_json=False):
    interactive = not as_json and is_interactive()
    prompted = set()

    def approvals():
        for request in service.store.approvals(task_id):
            request_id = request["id"]
            if request_id in prompted:
                continue
            prompted.add(request_id)
            if interactive:
                allow = click.confirm(request["prompt"], default=False, err=True)
                try:
                    service.approve(task_id, request_id, allow)
                except ValueError:
                    # Another attached terminal may have answered or cancelled first.
                    pass
            elif not as_json:
                _echo(f"Approval needed: {request['prompt']}\n"
                           f"Answer with miminions task approve {task_id} {request_id} --allow or --deny", err=True)

    try:
        task = service.get(task_id)
        verbose = task.request.params.get("verbose", False)
        if not as_json:
            approvals()
        for event in service.follow(task_id, after):
            if as_json:
                _echo(json.dumps(event.to_dict(), ensure_ascii=False))
                continue
            data = event.data
            if event.type in {"stdout", "text_delta"}:
                _echo(data["text"], nl=False)
            elif event.type == "stderr":
                _echo(data["text"], nl=False, err=True)
            elif event.type == "started":
                _echo(f"Task {task_id} started.", err=True)
            elif event.type in {"phase", "retry", "heartbeat"}:
                _echo(data["message"], err=True)
            elif event.type == "tool_call":
                arguments = f" {json.dumps(data.get('arguments', {}), ensure_ascii=False)}" if verbose else ""
                _echo(f"Tool: {data['name']}{arguments}", err=True)
            elif event.type == "turn_end" and verbose:
                _echo(f"Turn: {data.get('input_tokens') or 0} in / {data.get('output_tokens') or 0} out tokens, "
                           f"{data.get('tool_calls') or 0} tool call(s), {data['latency']:.1f}s", err=True)
            elif event.type == "approval_requested":
                approvals()
            elif event.type in {"completed", "failed", "cancelled"}:
                message = f"Task {task_id} {event.type}."
                if data.get("error"):
                    message += f" {data['error']}"
                _echo(message, err=True)
        status = service.get(task_id).status
        return {"completed": 0, "failed": 1, "cancelled": 130}[status]
    except (KeyboardInterrupt, click.Abort, BrokenPipeError):
        try:
            _echo(f"Detached; task {task_id} continues. Follow with miminions task tail {task_id}", err=True)
        except BrokenPipeError:
            pass
        return 130
    except (ValueError, OSError, sqlite3.Error) as exc:
        raise click.ClickException(str(exc)) from exc


def submit_task(kind, params, *, attach=False, detach=False, session_key=None, home=None):
    validate_attachment(attach, detach)
    try:
        service = ExecutionService(home)
        handle = service.submit(ExecutionRequest(kind, params, os.getcwd(), session_key), defer_start=True,
                                on_start=lambda message: click.echo(message, err=True))
        try:
            click.echo(f"Task {handle.id} accepted; follow with miminions task tail {handle.id}", err=True)
        finally:
            # Even an interrupted acknowledgement must not strand accepted work.
            handle.release()
        if not detach:
            code = follow_task(service, handle.id)
            if code:
                raise click.exceptions.Exit(code)
        return handle
    except (ValueError, OSError, sqlite3.Error) as exc:
        raise click.ClickException(str(exc)) from exc
