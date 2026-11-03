"""Candidate-specific driver source for offline review. No import-time hardware access."""
import threading
import time
from offline_prepare import check_buffer

VLNV = "user.org:user:lab08_vdma_frame_retire:1.0"
SHA = '54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f'
PARAMETERS = {"C_INCLUDE_MM2S":1,"C_INCLUDE_S2MM":0,"C_INCLUDE_SG":0,
              "C_NUM_FSTORES":4,"C_INCLUDE_MM2S_DRE":0,
              "C_M_AXI_MM2S_ADDR_WIDTH":32,"C_M_AXI_MM2S_DATA_WIDTH":32,
              "C_M_AXIS_MM2S_TDATA_WIDTH":32,"C_S_AXI_LITE_ADDR_WIDTH":9,
              "C_S_AXI_LITE_DATA_WIDTH":32,"C_PRMRY_IS_ACLK_ASYNC":0}
BASES = {0x41230000,0x41800000,0x43000000,0x43c00000,0x43c10000,0x43c20000,0x43c30000,0x43c40000,0x43c60000,0x43c70000}


def validate_description(description):
    if description.get("type") != VLNV or description.get("fullpath") != "video/axi_vdma":
        raise ValueError("Wrong custom IP or HWH hierarchy")
    for name,value in PARAMETERS.items():
        if int(description["parameters"][name],0) != value:
            raise ValueError("Unsupported configuration: "+name)
    if description.get("phys_addr") != 0x43000000 or description.get("addr_range") != 65536:
        raise ValueError("Control window mismatch")


def check_candidate(package):
    from joint_adapter import validate_package
    return validate_package(package)


class MM2S:
    """One static buffer parked at slot0; four valid references, no dynamic recycling.
    Only accesses offsets/fields defined by the candidate register contract.
    Native PYNQ channel is intentionally not inherited: it has unbounded waits
    and different stop/error-clearing/stride semantics.
    """
    def __init__(self, mmio, attempts=100, interval=0.001):
        if type(attempts) is not int or attempts<1 or interval<0:
            raise ValueError("Invalid wait bound")
        self.mmio,self.attempts,self.interval=mmio,attempts,interval
        self.buffer=None
        self.owner="none"
        self.lock=threading.RLock()
        self.trace=[]

    def read(self,offset):
        if offset not in (0,4,0x2c):
            raise ValueError("Read not allowed")
        value=int(self.mmio.read(offset))
        self.trace.append(dict(op="read",offset=offset,value=value))
        return value

    def write(self,offset,value):
        allowed={0,4,0x28,0x50,0x54,0x58,0x5c,0x60,0x64,0x68}
        if offset not in allowed or type(value) is not int or not 0<=value<2**32:
            raise ValueError("Write not allowed")
        if offset==4 and value & ~0x7000:
            raise ValueError("Only explicit IRQ event W1C")
        if offset==0 and value not in (0x10000,0x10001,4):
            raise ValueError("CR keeps bits6:5, repeat and IRQ disabled")
        if offset==0x58 and value!=3840:
            raise ValueError("Initial frame delay zero; tight stride only")
        if offset==0x28 and value!=0:
            raise ValueError("Static slot0 only")
        if offset==0x28:
            return self.park(value)
        self.mmio.write(offset,value)
        self.trace.append(dict(op="write",offset=offset,value=value))

    def park(self,slot):
        with self.lock:
            if type(slot) is not int or slot not in range(4):
                raise ValueError("Read frame reference must be 0..3")
            current=int(self.mmio.read(0x28))
            value=(current&~0x1f)|slot
            self.mmio.write(0x28,value)
            self.trace.append(dict(op="write",offset=0x28,value=value))

    def restart_static(self,controller,frame):
        if controller.driver is not self:
            raise ValueError("Recovery controller/driver mismatch")
        return controller.recover(frame)

    def wait(self,predicate):
        for _ in range(self.attempts):
            if predicate(): return
            time.sleep(self.interval)
        raise TimeoutError("Bounded VDMA wait exhausted")

    def status(self):
        value=self.read(4)
        if value & 0xf0:  # Includes unexpected IntErr; never assumes it is W1C.
            raise RuntimeError("VDMA error: "+hex(value))
        return value

    def attach(self,buffer):
        with self.lock:
            if self.buffer is not None or self.owner=="dma":
                raise RuntimeError("Buffer already held")
            if tuple(buffer.shape)!=(720,1280,3) or tuple(buffer.strides)!=(3840,3,1) or buffer.dtype.name!="uint8":
                raise ValueError("Expected tight BGR uint8 buffer")
            check_buffer(int(buffer.physical_address),int(buffer.nbytes))
            self.buffer,self.owner=buffer,"cpu"

    def allocate(self,allocator=None):
        # Actual API is invoked only if explicitly called by future authorized code.
        if allocator is None:
            from pynq import allocate
            allocator=allocate
        buffer=allocator(shape=(720,1280,3),dtype="u1")
        try:
            self.attach(buffer)
        except Exception:
            buffer.freebuffer()
            raise
        return buffer

    def reset(self):
        with self.lock:
            if self.owner=="dma":
                raise RuntimeError("Stop successfully before reset")
            self.write(0,4)
            self.wait(lambda: not self.read(0)&4)
            self.wait(lambda: bool(self.status()&1))

    def start(self):
        with self.lock:
            if self.owner!="cpu" or self.buffer is None:
                raise RuntimeError("CPU-owned buffer required")
            if not self.status()&1 or self.read(0)&4:
                raise RuntimeError("Channel not reset/stopped")
            self.buffer.flush()
            # Ownership changes BEFORE first start write; errors retain reference.
            self.owner="dma"
            try:
                self.write(0x28,0)
                for o in (0x5c,0x60,0x64,0x68):
                    self.write(o,int(self.buffer.physical_address))
                self.write(0x54,3840)
                self.write(0x58,3840)
                self.write(0,0x10001)  # park, no genlock/framecount/IRQ enables
                self.write(0x50,720)  # VSIZE submits last
                self.wait(lambda: not self.status()&1)
                if not self.read(0)&1:
                    raise RuntimeError("Run bit cleared")
            except Exception:
                # Deliberately no automatic free/restart/reset.
                raise

    def stop(self):
        from joint_adapter import stop_video
        return stop_video(self)

    def release(self):
        if self.owner != "cpu" or self.buffer is None:
            raise RuntimeError("Cannot free DMA-owned buffer")
        self.buffer.freebuffer()
        self.buffer=None
        self.owner="none"


def register_driver(default_ip=None,bindings=None):
    """Define/register custom leaf; no constructor invocation or MMIO here."""
    if bindings is None:raise RuntimeError("Verified unified_2 programming bindings required")
    bindings.revalidate()
    if default_ip is None:
        from pynq import DefaultIP
        default_ip=DefaultIP

    class SnapshotVDMA(default_ip):
        bindto=[VLNV]
        def __init__(self,description):
            bindings.revalidate()
            validate_description(description)  # BEFORE DefaultIP maps anything
            super().__init__(description)
            self.channel=MM2S(bindings.ios["dma"])
    return SnapshotVDMA


if __name__=="__main__":
    raise SystemExit("Offline review only. Use unittest; no hardware entry point.")
