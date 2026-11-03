"""Stage04 review source. No MMIO/Overlay creation or hardware entry point."""
import threading
import time

CANDIDATE_SHA = '54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f'
DRP=((8,0x41),(12,0x69a),(16,0),(20,0x20c4),(24,0xcfafa401),(28,0x00a300ff))
SOURCE=sum(1<<b for b in (*range(20,26),*range(13,19),*range(8,12)))
PREPARE=SOURCE|2
ENABLE=SOURCE|6
VTC_TIMING={0x60:0x02d00500,0x70:0x672,0x74:0x02ee02ee,
            0x78:0x0596056e,0x7c:0x05000500,0x80:0x02d902d4,0x84:0x05000500}

def check_control(value,enabled):
    required={**{b:1 for b in (*range(20,26),*range(13,19),*range(8,12))},1:1}
    required[2]=int(enabled)
    if type(value) is not int or not 0<=value<2**32:
        raise ValueError("Invalid control word")
    for bit in range(32):
        if (value>>bit)&1 != required.get(bit,0):
            raise ValueError("VTC CONTROL field mismatch bit "+str(bit))

def wait(io,offset,mask,value,attempts,interval):
    if type(attempts) is not int or attempts<1 or interval<0:
        raise ValueError("Positive bounded wait required")
    for _ in range(attempts):
        if io.read(offset)&mask==value: return
        time.sleep(interval)
    raise TimeoutError("Bounded attempts exhausted; individual MMIO latency is not bounded here")

def start_clock(io,attempts=100,interval=0.001):
    if type(attempts) is not int or attempts<1 or interval<0:
        raise ValueError("Invalid wait limit")
    started=time.monotonic()
    io.write(0,0)
    try:
        wait(io,4,1,0,attempts,interval)
        for offset,value in DRP: io.write(offset,value)
        io.write(0,1)
        wait(io,4,1,1,attempts,interval)
    except Exception as first:
        try: io.write(0,0)
        except Exception as cleanup:
            first.cleanup_error=repr(cleanup)  # Python 3.10 compatible; preserve first exception
        raise
    return dict(drp=[list(x) for x in DRP],ctrl_status_complete=True,
                started_monotonic=started,completed_monotonic=time.monotonic(),
                attempts=attempts,interval_seconds=interval)

class Session:
    """Source records must come from Stage05 authorized loader, never bool reset flags.
    This record identifies prerequisites; it does not prove internal reset/LOCKED.
    One session is one attempt; failure is sticky. All config users must share its lock.
    """
    def __init__(self,session_id,identity_sha,fresh_source,fclk_source):
        if identity_sha!=CANDIDATE_SHA or not all(type(x) is str and x.strip()
                for x in (session_id,fresh_source,fclk_source)):
            raise ValueError("Candidate/fresh-session/FCLK0/1 evidence sources required")
        self.lock=threading.Lock()
        self.io_lock=threading.RLock()
        self.used=False
        self.failed=False
        self.records=dict(session_id=session_id,candidate_sha=identity_sha,
                          fresh_source=fresh_source,fclk_source=fclk_source,
                          G1="NOT_RUN",G2="NOT_RUN",hardware_observation="NOT_RUN")

def probe_vtc(vtc,record):
    reads={}
    record["probe_reads"]=reads
    def read(offset):
        value=vtc.read(offset)
        reads[hex(offset)]=value
        return value
    version=read(0x10)
    if version>>24!=6 or (version>>16)&0xff!=1:
        raise ValueError("VTC VERSION must identify v6.1")
    for offset,value in VTC_TIMING.items():
        if read(offset)!=value:
            raise ValueError("Frozen timing mismatch at "+hex(offset))
    if read(0x68)&0x4f!=2:
        raise ValueError("GFENC must be RGB progressive")
    if read(0x6c)&0x1f!=0x1f:
        raise ValueError("GPOL necessary polarity mismatch")
    # This is access/configuration evidence, not direct internal reset observation.

def configure_vtc(vtc,record):
    if record.get("G2")!="ACCESS_CHECKS_COMPLETED":
        raise RuntimeError("G2 required before VTC writes")
    vtc.write(0x0c,0)
    write_control(vtc,False)

def write_control(vtc,enabled):
    value=ENABLE if enabled else PREPARE
    check_control(value,enabled)
    vtc.write(0,value)
    check_control(vtc.read(0),enabled)

def configure_colors(csc,unpack):
    unpack.write(0x10,0)
    for offset in range(0x10,0x69,8):
        csc.write(offset,256 if offset in (0x10,0x30,0x50) else 0)

def initialize(clock,csc,unpack,vtc,intc,gpio,dma,buffer,fill,session,
               attempts=100,interval=0.001,settle_seconds=0.001):
    if not isinstance(session,Session) or settle_seconds<0.001:
        raise ValueError("Session evidence and >=1ms engineering interval required")
    if not session.lock.acquire(blocking=False):
        raise RuntimeError("Concurrent configuration rejected")
    record=session.records
    try:
        if session.used or session.failed:
            raise RuntimeError("Unknown/used/failed session cannot be retried")
        session.used=True
        dma.lock=session.io_lock
        if dma.owner=="dma" or not dma.read(4)&1 or dma.read(0)&1:
            raise RuntimeError("Fresh stopped DMA required")
        # No VTC access whatsoever before this attempt's clock handshake + settle.
        session.io_lock.acquire()
        record["clock"]=start_clock(clock,attempts,interval)
        before=time.monotonic()
        time.sleep(settle_seconds)
        record["settle"]=dict(requested_seconds=settle_seconds,
                              elapsed_seconds=time.monotonic()-before)
        record["G1"]="CLOCK_SETTLED_FOR_PROBE"
        probe_vtc(vtc,record)  # read-only until all probes succeed
        record["G2"]="ACCESS_CHECKS_COMPLETED"
        intc.write(8,0)
        gpio.write(0x11c,0)
        gpio.write(0x128,0)
        configure_vtc(vtc,record)
        configure_colors(csc,unpack)
        dma.reset()
        dma.attach(buffer)
        fill(buffer)
        dma.start()
        write_control(vtc,True)
        return record
    except Exception as first:
        session.failed=True
        record["first_error"]=repr(first)
        raise
    finally:
        if session.used:
            try:session.io_lock.release()
            except RuntimeError:pass
        session.lock.release()

def stop(vtc,dma):
    # DMA lock spans ownership return and downstream disable/free, preventing restart.
    with dma.lock:
        dma.stop()
        write_control(vtc,False)
        dma.release()

if __name__=="__main__":
    raise SystemExit("Offline source review only; no hardware launcher.")
