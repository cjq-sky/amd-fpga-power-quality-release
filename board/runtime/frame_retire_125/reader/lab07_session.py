"""Software epoch journal under the runner's cooperating-process read/reload lease."""
import json
import uuid
from lab07_raw_reader import ReaderLease
from lab07_registers import BIT_SHA256


class ManagedEpoch:
    def __init__(self, journal, boot_id):
        self.journal, self.boot_id = journal, boot_id
        self.session_id = str(uuid.uuid4())
        journal.seek(0)
        text = journal.read()
        previous = json.loads(text) if text.strip() else {}
        same_boot = previous.get("boot_id") == boot_id
        self.generation = previous.get("reload_generation", 0) if same_boot else 0
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("invalid managed reload generation")
        self.ready = same_boot and not previous.get("reload_pending", True) and previous.get("bit_sha256") == BIT_SHA256

    def token(self):
        return self.session_id, self.boot_id, self.generation

    def metadata(self):
        return dict(session_id=self.session_id, boot_id=self.boot_id, reload_generation=self.generation)

    def _persist(self, pending):
        self.journal.seek(0)
        self.journal.write(json.dumps(dict(self.metadata(), reload_pending=pending, bit_sha256=BIT_SHA256)))
        self.journal.truncate()
        self.journal.flush()

    def begin_reload(self):
        self.ready = False
        self.generation += 1
        self._persist(True)  # Invalidate old state before reconfiguration begins.

    def complete_reload(self):
        self._persist(False)
        self.ready = True

    def require_attach(self):
        if not self.ready:
            raise ValueError("no completed managed load in this boot; run --hardware without --attach")


class Session:
    """Reload invalidates all registered reader state; one shared raw lease per session."""
    def __init__(self,managed=None):
        self.managed=managed;self.identity=str(uuid.uuid4());self.generation=0
        self.callbacks=[];self.raw_lease=ReaderLease(self.token)
    def token(self):return self.managed.token() if self.managed else (self.identity,self.generation)
    def register(self,callback):self.callbacks.append(callback)
    def begin_new_epoch(self):
        if self.raw_lease.active:raise RuntimeError('reload excluded by active raw lease')
        self.generation+=1
        if self.managed:self.managed.begin_reload()
        for callback in self.callbacks:callback()
        return self.token()
