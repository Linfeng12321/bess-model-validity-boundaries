"""Local, resumable campaign supervisor. No source-tree writes or shell execution."""
import argparse
import csv
import ctypes
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid

VERSION = 'run-health-v1.1-policy-only'
TERMINALS = {'TIA_FULL_PAPER_RESEARCH_READY',
             'TIA_FULL_PAPER_CONDITIONAL_GO_EXTERNAL_DEPENDENCY'}
MANIFEST_FIELDS = ['timestamp', 'batch_id', 'event', 'attempt', 'pid', 'exit_code',
                   'start_time', 'end_time', 'artifacts_json', 'QA_status']


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def age(timestamp):
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(timestamp)).total_seconds()


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        return default


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    data = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    try:
        with tmp.open('x', encoding='utf-8', newline='\n') as f:
            f.write(data + '\n')
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(20):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(.05)
    finally:
        if tmp.exists():
            tmp.unlink()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def identity(pid=None):
    pid = int(pid or os.getpid())
    if os.name != 'nt':
        try:
            return {'pid': pid, 'creation': Path(f'/proc/{pid}/stat').read_text().split()[21]}
        except (OSError, IndexError):
            return None
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k.OpenProcess.restype = ctypes.c_void_p
    k.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p] * 4
    k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = k.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        times = [ctypes.c_uint64() for _ in range(4)]
        code = ctypes.c_uint32()
        if not k.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return None
        if not k.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None
        return {'pid': pid, 'creation': str(times[0].value)}
    finally:
        k.CloseHandle(handle)


def alive(expected):
    return bool(expected and identity(expected['pid']) == expected)


class OwnerLock:
    """Lifetime OS lock; Windows allows readers but denies a second writer."""
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            import msvcrt
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                      ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
            k.CreateFileW.restype = ctypes.c_void_p
            handle = k.CreateFileW(str(self.path), 0xC0000000, 1, None, 4, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                raise RuntimeError('LOCK_OWNED_OR_UNAVAILABLE: ' + str(self.path))
            self.file = os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY), 'r+b')
        else:
            import fcntl
            self.file = self.path.open('a+b')
            try:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self.file.close()
                raise RuntimeError('LOCK_OWNED_OR_UNAVAILABLE: ' + str(self.path))
        self.write({'owner': identity(), 'acquired': now(), 'status': 'OWNED'})
        return self

    def write(self, value):
        self.file.seek(0)
        self.file.write((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
        self.file.truncate()
        self.file.flush()
        os.fsync(self.file.fileno())

    def __exit__(self, *args):
        if self.file:
            try:
                self.write({'owner': identity(), 'released': now(), 'status': 'RELEASED'})
            finally:
                self.file.close()


def append_json(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


@contextlib.contextmanager
def append_lock(path):
    guard = OwnerLock(path)
    for attempt in range(500):
        try:
            guard.__enter__()
            break
        except RuntimeError:
            if attempt == 499:
                raise
            time.sleep(.02)
    try:
        yield
    finally:
        guard.__exit__(None, None, None)


def event(root, name, state, result='', qa='NOT_APPLICABLE', **extra):
    record = {'timestamp': now(), 'event': name, 'gate': state.get('current_gate'),
              'experiment_batch': state.get('current_experiment'), 'result': result,
              'QA_status': qa, 'next_action': state.get('next_action'), **extra}
    with append_lock(root / 'RUN_CONTROL/runtime/progress.append.lock'):
        append_json(root / 'RUN_PROGRESS.log', record)


def manifest(root, **values):
    path = root / 'RUN_MANIFEST.csv'
    with append_lock(root / 'RUN_CONTROL/runtime/manifest.append.lock'):
        existed = path.exists() and path.stat().st_size > 0
        with path.open('a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
            if not existed:
                writer.writeheader()
            writer.writerow({k: values.get(k, '') for k in MANIFEST_FIELDS})
            f.flush()
            os.fsync(f.fileno())


def completed(root):
    path = root / 'RUN_MANIFEST.csv'
    result = {}
    if path.exists():
        with path.open(encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                if row['event'] == 'VERIFIED':
                    result[row['batch_id']] = row
    for row in result.values():
        for artifact in json.loads(row['artifacts_json']):
            p = root / artifact['path']
            if not p.is_file() or sha(p) != artifact['sha256']:
                raise RuntimeError('VERIFIED_ARTIFACT_CONFLICT: ' + str(p))
    return result


def set_state(root, state, **updates):
    state.update(updates)
    state['timestamp'] = now()
    atomic(root / 'CURRENT_STATE.json', state)
    atomic(root / 'NEXT_ACTION.md', '# Next executable action\n\n' + state['next_action'])
    atomic(root / 'CURRENT_GATE.md', '# Current gate\n\n' + state['current_gate'] +
           '\n\nResearch gate decision: ' + state.get('research_gate_decision', 'NOT_EVALUATED'))
    event(root, 'STATE_CHANGED', state, state_snapshot=state.copy())


def heartbeat(root, state, status, watchdog=None, worker=None, alert=None):
    h = {key: state.get(key) for key in ['current_gate', 'current_task', 'current_experiment',
         'last_completed_batch', 'next_action', 'code_commit', 'protocol_version']}
    h.update(timestamp=now(), status=status, process_id=(worker or {}).get('pid'),
             watchdog_process_id=(watchdog or {}).get('pid'), worker_identity=worker,
             watchdog_identity=watchdog, terminal_state=state.get('terminal_state'),
             health_detail=alert, supervisor_status='RUNNING' if watchdog else 'ABSENT',
             recovery_count=state.get('recovery_count', 0), code_sha256=state.get('code_sha256'))
    h['research_campaign'] = state.get('research_campaign', 'ACTIVE')
    h['inventory_gate'] = state.get('inventory_gate', 'GO')
    h['execution_mode'] = 'OWNED_WORKER' if worker else 'AGENT_RESEARCH_LEASE' if status == 'RUNNING' else 'NO_ACTIVE_WORKER'
    h['agent_activity_expires'] = state.get('agent_activity_expires')
    atomic(root / 'RUN_HEARTBEAT.json', h)
    atomic(root / 'RUN_STATUS.md', '# Run status\n\n' +
           '\n'.join(f'- {k}: {v}' for k, v in h.items()) +
           '\n\nRUNNING means a live owned worker or a bounded AGENT_RESEARCH_LEASE. Lease expiry without new agent evidence changes status to IDLE; watchdog liveness alone is not research activity.' +
           '\nState files are current snapshots. RUN_PROGRESS.log and RUN_MANIFEST.csv are append-only history.')
    event(root, 'HEARTBEAT', state, status, heartbeat=h)
    return h


def assess(worker, worker_hb, config, progress_time=None):
    if not alive(worker):
        return 'PROCESS_EXITED'
    if not worker_hb:
        return 'STARTING'
    elapsed = age(worker_hb['timestamp'])
    if elapsed <= config['stale_threshold_seconds']:
        return 'HEALTHY'
    # Silence alone is not death. The known compute window and output activity matter.
    quiet_until = worker_hb.get('expected_quiet_until')
    if quiet_until and dt.datetime.fromisoformat(quiet_until) > dt.datetime.now(dt.timezone.utc):
        return 'EXPECTED_LONG_COMPUTE'
    if progress_time and age(progress_time) <= config['stale_threshold_seconds']:
        return 'HEARTBEAT_STALE_OUTPUT_ACTIVE'
    return 'STALE_HEARTBEAT'


def local_path(root, relative):
    p = (root / relative).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('Path outside new workspace: ' + str(p))
    return p


def worker(root):
    config = read(root / 'RUN_CONTROL/config.json')
    with OwnerLock(root / 'RUN_CONTROL/runtime/worker.lock'):
        state = read(root / 'CURRENT_STATE.json')
        me = identity()
        worker_hb = root / 'RUN_CONTROL/runtime/WORKER_HEARTBEAT.json'
        stop = threading.Event()
        active = {'batch_id': None, 'child_identity': None}
        def pulse():
            while not stop.is_set():
                atomic(worker_hb, {'timestamp': now(), 'worker': me, **active})
                stop.wait(config['heartbeat_interval_seconds'])
        ticker = threading.Thread(target=pulse, daemon=True)
        ticker.start()
        try:
            done = completed(root)
            for task in read(root / 'RUN_CONTROL/execution_plan.json')['tasks']:
                if task['batch_id'] in done:
                    event(root, 'SKIP_VERIFIED_BATCH', state, task['batch_id'], 'PASS')
                    continue
                if not task.get('resume_safe'):
                    raise RuntimeError('UNREGISTERED_RESUME_CONTRACT')
                script = local_path(root, task['script'])
                if sha(script) != task['script_sha256']:
                    raise RuntimeError('REGISTERED_CODE_HASH_CONFLICT')
                batch = task['batch_id']
                active['batch_id'] = batch
                attempt = str(time.time_ns())
                logdir = root / 'RUN_CONTROL/logs'
                logdir.mkdir(exist_ok=True)
                started = now()
                set_state(root, state, status='RUNNING', current_gate=task['gate'],
                          current_task=task['task'], current_experiment=batch,
                          next_action='Run registered batch, validate receipt, append VERIFIED manifest record.',
                          worker_identity=me)
                heartbeat(root, state, 'RUNNING', read(root / 'RUN_CONTROL/runtime/WATCHDOG_IDENTITY.json'), me)
                event(root, 'BATCH_STARTED', state, attempt=attempt)
                argv = [sys.executable, '-B', str(script), '--root', str(root)] + task.get('args', [])
                with (logdir / f'{batch}.{attempt}.stdout.log').open('ab') as stdout, \
                     (logdir / f'{batch}.{attempt}.stderr.log').open('ab') as stderr:
                    child = subprocess.Popen(argv, cwd=root, stdout=stdout, stderr=stderr,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    child_id = identity(child.pid)
                    active['child_identity'] = child_id
                    atomic(root / 'RUN_CONTROL/runtime/CHILD_PROCESS.json',
                           {'identity': child_id, 'batch_id': batch, 'start_time': started,
                            'attempt': attempt, 'command': argv})
                    atomic(worker_hb, {'timestamp': now(), 'worker': me, **active})
                    code = child.wait()
                ended = now()
                atomic(root / f'RUN_CONTROL/runtime/EXIT_{batch}_{attempt}.json',
                       {'batch_id': batch, 'pid': child.pid, 'exit_code': code,
                        'start_time': started, 'end_time': ended})
                manifest(root, timestamp=ended, batch_id=batch, event='PROCESS_EXIT', attempt=attempt,
                         pid=child.pid, exit_code=code, start_time=started, end_time=ended)
                if code != 0:
                    raise RuntimeError(f'BATCH_EXIT_NONZERO:{batch}:{code}')
                artifacts = []
                for output in task['outputs']:
                    p = local_path(root, output)
                    if not p.is_file():
                        raise RuntimeError('MISSING_EXPECTED_OUTPUT: ' + output)
                    artifacts.append({'path': output, 'sha256': sha(p), 'bytes': p.stat().st_size})
                receipt = read(local_path(root, task['receipt']))
                if receipt.get('execution_qa') != 'PASS':
                    raise RuntimeError('BATCH_RECEIPT_QA_NOT_PASS')
                manifest(root, timestamp=now(), batch_id=batch, event='VERIFIED', attempt=attempt,
                         pid=child.pid, exit_code=code, start_time=started, end_time=ended,
                         artifacts_json=json.dumps(artifacts), QA_status='PASS')
                active['child_identity'] = None
                set_state(root, state, last_completed_batch=batch, last_completed_run=batch,
                          next_action=receipt['next_action'], current_experiment=None,
                          research_gate_decision=receipt.get('research_gate_decision', 'NOT_EVALUATED'))
                atomic(worker_hb, {'timestamp': now(), 'worker': me, **active})
                event(root, 'BATCH_PASS', state, batch, 'PASS')
                heartbeat(root, state, 'RUNNING', read(root / 'RUN_CONTROL/runtime/WATCHDOG_IDENTITY.json'), me)
            set_state(root, state, status='IDLE', worker_identity=None,
                      current_task='NO_REGISTERED_EXECUTABLE_BATCH_PENDING')
            event(root, 'QUEUE_DRAINED', state, 'Not a campaign terminal state')
            heartbeat(root, state, 'IDLE', read(root / 'RUN_CONTROL/runtime/WATCHDOG_IDENTITY.json'))
        except BaseException:
            trace = traceback.format_exc()
            event(root, 'WORKER_EXCEPTION', state, trace, 'FAIL')
            append_json(root / 'RUN_CONTROL/logs/FAILURES.jsonl',
                        {'timestamp': now(), 'identity': me, 'trace': trace})
            raise
        finally:
            stop.set()
            ticker.join(timeout=5)


def watchdog(root):
    config = read(root / 'RUN_CONTROL/config.json')
    with OwnerLock(root / 'RUNNING.lock') as lock:
        me = identity()
        atomic(root / 'RUN_CONTROL/runtime/WATCHDOG_IDENTITY.json', me)
        state = read(root / 'CURRENT_STATE.json')
        event(root, 'WATCHDOG_STARTED', state, watchdog_identity=me)
        proc = None
        tracked = read(root / 'RUN_CONTROL/runtime/WORKER_PROCESS.json', {}).get('identity')
        last_publish = 0
        last_signature = None
        last_outputs = None
        output_activity = None
        recorded_exits = set()
        try:
            while not (root / 'RUN_CONTROL/STOP_WATCHDOG').exists():
                state = read(root / 'CURRENT_STATE.json')
                # Always consult all recovery authorities, even if the next action is textual.
                next_text = (root / 'NEXT_ACTION.md').read_text(encoding='utf-8')
                done = completed(root)
                tasks = read(root / 'RUN_CONTROL/execution_plan.json')['tasks']
                pending = [t for t in tasks if t['batch_id'] not in done]
                terminal = state.get('terminal_state')
                if terminal and terminal not in TERMINALS:
                    raise RuntimeError('INVALID_CAMPAIGN_TERMINAL')
                if terminal:
                    if alive(tracked):
                        raise RuntimeError('TERMINAL_WITH_LIVE_WORKER_CONFLICT')
                    set_state(root, state, status='COMPLETE')
                    heartbeat(root, state, 'COMPLETE', me)
                    break
                alert = None
                wh = read(root / 'RUN_CONTROL/runtime/WORKER_HEARTBEAT.json', {})
                child = read(root / 'RUN_CONTROL/runtime/CHILD_PROCESS.json', {}).get('identity')
                if tracked and not alive(tracked) and str(tracked) not in recorded_exits:
                    receipt = read(root / 'RUN_CONTROL/runtime/WORKER_PROCESS.json', {})
                    receipt.update(end_time=now(), exit_code=proc.poll() if proc else None,
                                   exit_code_known=proc is not None)
                    atomic(root / ('RUN_CONTROL/runtime/WORKER_EXIT_' + str(tracked['pid']) + '_' + tracked['creation'] + '.json'), receipt)
                    event(root, 'WORKER_PROCESS_EXIT', state, receipt=receipt)
                    recorded_exits.add(str(tracked))
                if tracked and not alive(tracked) and alive(child):
                    # An orphaned owned computation must finish before a replacement is launched.
                    alert = 'ORPHAN_CHILD_ALIVE_NO_DUPLICATE_RESTART'
                    status = 'RUNNING'
                elif alive(tracked):
                    logs = list((root / 'RUN_CONTROL/logs').glob('*.log'))
                    sizes = [(str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in logs]
                    if sizes != last_outputs:
                        output_activity = now()
                        last_outputs = sizes
                    alert = assess(tracked, wh, config, output_activity)
                    status = 'RUNNING'
                elif state.get('status') in ['FAILED', 'BLOCKED']:
                    status = state['status']
                    alert = state.get('health_detail')
                elif pending:
                    if tracked:
                        exit_code = proc.poll() if proc else None
                        event(root, 'UNEXPECTED_PROCESS_EXIT', state, exit_code=exit_code,
                              process_identity=tracked, next_action_snapshot=next_text)
                        count = state.get('recovery_count', 0)
                        if count >= config['max_auto_restarts']:
                            set_state(root, state, status='FAILED', health_detail='FAILED_NEEDS_DIAGNOSIS',
                                      next_action='Diagnose persisted failure trace; automatic restart limit reached.')
                            heartbeat(root, state, 'FAILED', me, alert='FAILED_NEEDS_DIAGNOSIS')
                            tracked = None
                            continue
                        set_state(root, state, recovery_count=count + 1)
                        event(root, 'AUTO_RECOVERY', state, f'Restart {count + 1}; skip VERIFIED batches')
                    if shutil.disk_usage(root).free < config['min_free_bytes']:
                        raise OSError('INSUFFICIENT_FREE_DISK')
                    attempt = str(time.time_ns())
                    with (root / f'RUN_CONTROL/logs/worker.{attempt}.stdout.log').open('ab') as stdout, \
                         (root / f'RUN_CONTROL/logs/worker.{attempt}.stderr.log').open('ab') as stderr:
                        proc = subprocess.Popen([sys.executable, '-B', __file__, 'worker', '--root', str(root)],
                               cwd=root, stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    tracked = identity(proc.pid)
                    atomic(root / 'RUN_CONTROL/runtime/WORKER_PROCESS.json',
                           {'identity': tracked, 'start_time': now(), 'attempt': attempt})
                    event(root, 'WORKER_LAUNCHED', state, process_identity=tracked)
                    status = 'RUNNING'
                else:
                    lease = state.get('agent_activity_expires')
                    status = 'RUNNING' if lease and age(lease) < 0 else 'IDLE'
                    tracked = None
                signature = (status, alert, state.get('timestamp'))
                if time.monotonic() - last_publish >= config['heartbeat_interval_seconds'] or signature != last_signature:
                    h = heartbeat(root, state, status, me, tracked if alive(tracked) else child if alive(child) else None, alert)
                    lock.write({'owner': me, 'status': 'OWNED', 'timestamp': h['timestamp'],
                                'worker': h['worker_identity']})
                    last_publish = time.monotonic()
                    last_signature = signature
                # Atomic state writes plus a flushed append log are also real write-health probes.
                time.sleep(config['watchdog_poll_seconds'])
        except BaseException:
            trace = traceback.format_exc()
            event(root, 'WATCHDOG_EXCEPTION', state, trace, 'FAIL')
            append_json(root / 'RUN_CONTROL/logs/FAILURES.jsonl', {'timestamp': now(), 'trace': trace})
            set_state(root, state, status='FAILED', health_detail='FAILED_NEEDS_DIAGNOSIS', next_action='Diagnose watchdog failure trace.')
            heartbeat(root, state, 'FAILED', me, tracked, 'FAILED_NEEDS_DIAGNOSIS')
            raise
        finally:
            event(root, 'WATCHDOG_EXIT', state, 'Worker is not killed on watchdog exit.')
            if (root / 'RUN_CONTROL/STOP_WATCHDOG').exists():
                state = read(root / 'CURRENT_STATE.json')
                heartbeat(root, state, 'RUNNING' if alive(tracked) else state['status'], worker=tracked if alive(tracked) else None)


def initialize(root):
    (root / 'RUN_CONTROL/runtime').mkdir(parents=True, exist_ok=True)
    (root / 'RUN_CONTROL/logs').mkdir(parents=True, exist_ok=True)
    if (root / 'CURRENT_STATE.json').exists():
        raise RuntimeError('State exists; use watchdog to resume, never reinitialize')
    state = {'status': 'IDLE', 'project_stage': 'PREPARATORY_RESEARCH_CAMPAIGN',
             'current_gate': 'GATE_A_PROBLEM_EXISTENCE', 'current_task': 'READ_SCIENTIFIC_AUTHORITIES',
             'current_experiment': None, 'last_completed_batch': None, 'last_completed_run': None,
             'next_action': 'Read SETA manuscript, supplement, TIA digest and official TIA/TPSO requirements.',
             'code_commit': None, 'code_sha256': sha(Path(__file__)),
             'protocol_version': 'UNFROZEN', 'runtime_version': VERSION,
             'terminal_state': None, 'recovery_count': 0,
             'research_gate_decision': 'GATE_A_NOT_YET_EVALUATED', 'inventory_gate': 'GO',
             'filesystem_metadata_variation': 'NON_FATAL_FILESYSTEM_METADATA_VARIATION',
             'research_campaign': 'ACTIVE'}
    set_state(root, state)
    manifest(root, timestamp=now(), event='MANIFEST_INITIALIZED', QA_status='NOT_APPLICABLE')
    heartbeat(root, state, 'IDLE')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['init', 'watchdog', 'worker', 'status'])
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    if args.mode == 'init':
        initialize(root)
    elif args.mode == 'watchdog':
        receipt = {'identity': identity(), 'start_time': now(), 'end_time': None, 'exit_code': None}
        path = root / ('RUN_CONTROL/runtime/WATCHDOG_PROCESS_' + str(os.getpid()) + '_' + str(time.time_ns()) + '.json')
        atomic(path, receipt)
        try:
            watchdog(root)
            receipt['exit_code'] = 0
        except BaseException:
            receipt['exit_code'] = 1
            raise
        finally:
            receipt['end_time'] = now()
            atomic(path, receipt)
    elif args.mode == 'worker':
        worker(root)
    else:
        h = read(root / 'RUN_HEARTBEAT.json', {})
        h['observed_at'] = now()
        h['watchdog_alive_now'] = alive(h.get('watchdog_identity'))
        h['worker_alive_now'] = alive(h.get('worker_identity'))
        h['heartbeat_age_seconds'] = age(h['timestamp']) if h.get('timestamp') else None
        print(json.dumps(h, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
