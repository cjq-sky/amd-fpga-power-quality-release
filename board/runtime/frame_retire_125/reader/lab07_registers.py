"""Sole register/bit/format authority, checked against the 07-B ledger (ABI 2.0 historical + 2.1 unified)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Register:
    offset: int
    bits: int
    encoding: str
    scale: int
    unit: str
    region: str

REGISTERS = {
    'MAGIC': Register(0x000, 32, 'U32', 1, 'integer', 'identification'),
    'CORE_ID': Register(0x004, 32, 'U32', 1, 'integer', 'identification'),
    'REGMAP_VERSION': Register(0x008, 32, 'major[31:16],minor[15:0]', 1, 'integer', 'identification'),
    'FEATURE_CAPABILITY': Register(0x00c, 32, 'bitmask', 1, 'integer', 'identification'),
    'RAW_CAPABILITY': Register(0x010, 32, 'bitmask', 1, 'integer', 'identification'),
    'BASELINE_ID': Register(0x014, 32, 'U32', 1, 'integer', 'identification'),
    'FRAME_SAMPLES': Register(0x018, 32, 'U32', 1, 'integer', 'identification'),
    'SAMPLE_RATE_NOMINAL_HZ': Register(0x01c, 32, 'U32 Hz', 1, 'integer', 'identification'),
    'SNAPSHOT_SEQ': Register(0x040, 32, 'U32 modulo', 1, 'integer', 'snapshot'),
    'SNAPSHOT_VALID': Register(0x044, 1, 'bit0', 1, 'integer', 'snapshot'),
    'FRAME_ID': Register(0x048, 32, 'U32 source fid', 1, 'integer', 'snapshot'),
    'FEATURE_VALID_MASK': Register(0x04c, 9, 'bits8:0', 1, 'integer', 'snapshot'),
    'FEATURE_ACQUISITION_VALID': Register(0x050, 1, 'bit0', 1, 'integer', 'snapshot'),
    'TIME_STATUS': Register(0x054, 8, 'U8', 1, 'integer', 'snapshot'),
    'SPECTRAL_STATUS': Register(0x058, 32, 'CH2[31:16],CH1[15:0]', 1, 'integer', 'snapshot'),
    'SPECTRAL_NUMERIC_STATUS': Register(0x05c, 32, 'CH2[31:16],CH1[15:0]', 1, 'integer', 'snapshot'),
    'FORMAL_IDENTITY': Register(0x060, 4, 'CH1[1:0],CH2[3:2]；upper28=0', 1, 'integer', 'snapshot'),
    'CH1_RMS': Register(0x080, 16, 'unsigned ADC code', 1, 'ADC code', 'snapshot'),
    'CH1_PEAK': Register(0x084, 16, 'unsigned absolute ADC code', 1, 'ADC code', 'snapshot'),
    'CH1_CREST': Register(0x088, 16, 'UQ6.10', 1024, 'ratio', 'snapshot'),
    'CH1_FREQUENCY_MHZ': Register(0x08c, 32, 'unsigned mHz', 1000, 'Hz', 'snapshot'),
    'CH1_H1': Register(0x090, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH1_H3': Register(0x094, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH1_H5': Register(0x098, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH1_H7': Register(0x09c, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH1_H9': Register(0x0a0, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH1_THD_ODD_3_5_7_9': Register(0x0a4, 32, 'unsigned F16 ratio', 65536, 'ratio', 'snapshot'),
    'CH2_RMS': Register(0x0c0, 16, 'unsigned ADC code', 1, 'ADC code', 'snapshot'),
    'CH2_PEAK': Register(0x0c4, 16, 'unsigned absolute ADC code', 1, 'ADC code', 'snapshot'),
    'CH2_CREST': Register(0x0c8, 16, 'UQ6.10', 1024, 'ratio', 'snapshot'),
    'CH2_H1': Register(0x0cc, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH2_H3': Register(0x0d0, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH2_H5': Register(0x0d4, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH2_H7': Register(0x0d8, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH2_H9': Register(0x0dc, 32, 'unsigned F16 amplitude', 65536, 'ADC-code amplitude', 'snapshot'),
    'CH2_THD_ODD_3_5_7_9': Register(0x0e0, 32, 'unsigned F16 ratio', 65536, 'ratio', 'snapshot'),
    'ACQUISITION_FAULT': Register(0x100, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'ACQUISITION_FAULT_CODE': Register(0x104, 8, 'U8 low / upper24=0', 1, 'integer', 'live'),
    'BRANCH_MISMATCH_STICKY': Register(0x108, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'ORDER_UNKNOWN_STICKY': Register(0x10c, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAST_MISMATCH_TIME_ID': Register(0x110, 32, 'U32', 1, 'integer', 'live'),
    'LAST_MISMATCH_SPECTRAL_ID': Register(0x114, 32, 'U32', 1, 'integer', 'live'),
    'TIME_WAITING_FOR_SPECTRAL': Register(0x118, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'SPECTRAL_WAITING_FOR_TIME': Register(0x11c, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'TIME_OUTPUT_HELD': Register(0x120, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'SPECTRAL_OUTPUT_HELD': Register(0x124, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAB05_SUMMARY_OVERRUN': Register(0x128, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAB05_RESULT_OVERRUN': Register(0x12c, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAB06_BANK_OVERRUN_STICKY': Register(0x130, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAB06_FRAME_ERROR_STICKY': Register(0x134, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAB06_PROTOCOL_ERROR_STICKY': Register(0x138, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'LAST_SUCCESSFUL_FEATURE_FRAME_ID': Register(0x13c, 32, 'U32', 1, 'integer', 'live'),
    'SNAPSHOT_UPDATE_COUNTER': Register(0x140, 32, 'U32', 1, 'integer', 'live'),
    'RAW_DROP_STICKY': Register(0x144, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'RAW_DROP_COUNT': Register(0x148, 32, 'U32', 1, 'integer', 'live'),
    'RAW_PROTOCOL_STICKY': Register(0x14c, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'RAW_ACK_ERROR_STICKY': Register(0x150, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'RAW_TOKEN_EXHAUSTED_STICKY': Register(0x154, 1, 'bit0 / upper31=0', 1, 'integer', 'live'),
    'RAW_DESCRIPTOR_VALID': Register(0x200, 32, 'bit0', 1, 'integer', 'reserve'),
    'RAW_BANK_ID': Register(0x204, 32, 'bit0', 1, 'integer', 'reserve'),
    'RAW_FRAME_ID': Register(0x208, 32, 'U32', 1, 'integer', 'reserve'),
    'RAW_OWNER_TOKEN': Register(0x20c, 32, 'U32', 1, 'integer', 'reserve'),
    'RAW_FRAME_STATUS': Register(0x210, 32, 'U8', 1, 'integer', 'reserve'),
    'RAW_BANK_STATES': Register(0x214, 32, 'two nibbles', 1, 'integer', 'reserve'),
    'RAW_COMPLETE_PENDING_MASK': Register(0x218, 32, 'bits1:0', 1, 'integer', 'reserve'),
    'RAW_SAMPLE_COUNT': Register(0x21c, 32, 'U32=2048', 1, 'integer', 'reserve'),
    'RAW_CHANNEL_MASK': Register(0x220, 32, 'bits1:0=3', 1, 'integer', 'reserve'),
    'RAW_FRAME_BYTES': Register(0x224, 32, 'U32=8192', 1, 'integer', 'reserve'),
    'RAW_WINDOW_OFFSET': Register(0x228, 32, 'U32=0', 1, 'integer', 'reserve'),
    'RAW_WINDOW_SIZE_BYTES': Register(0x22c, 32, 'U32=8192', 1, 'integer', 'reserve'),
    'RAW_FORMAT': Register(0x230, 32, 'U32=0x00010001', 1, 'integer', 'reserve'),
    'RAW_ACK_BANK': Register(0x240, 32, 'bit0', 1, 'integer', 'reserve'),
    'RAW_ACK_TOKEN': Register(0x244, 32, 'U32', 1, 'integer', 'reserve'),
    'RAW_ACK': Register(0x248, 32, 'U32 command', 1, 'integer', 'reserve'),
    'RAW_ACK_RESULT': Register(0x24c, 32, 'busy[31],code[7:0]', 1, 'integer', 'reserve'),
    'RAW_ACK_COMPLETED_TOKEN': Register(0x250, 32, 'U32', 1, 'integer', 'reserve'),
}

RAW_REGISTER_SEMANTICS = {'RAW_DESCRIPTOR_VALID': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:owner_valid', 'width_encoding': '1 meaningful/U32; bit0'}, 'RAW_BANK_ID': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:valid ? owner_bank : 0', 'width_encoding': '1 meaningful/U32; bit0'}, 'RAW_FRAME_ID': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:valid ? owner_fid : 0', 'width_encoding': '32 meaningful/U32; U32'}, 'RAW_OWNER_TOKEN': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:valid ? owner_token : 0', 'width_encoding': '32 meaningful/U32; U32'}, 'RAW_FRAME_STATUS': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:valid ? owner_status : 0', 'width_encoding': '8 meaningful/U32; U8'}, 'RAW_BANK_STATES': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:bank_states', 'width_encoding': '8 meaningful/U32; two nibbles'}, 'RAW_COMPLETE_PENDING_MASK': {'rw': 'RO', 'reset': 'M=0;A=retain source', 'side_effect': 'none', 'source': 'lab07_raw_control:local bank states == 2', 'width_encoding': '2 meaningful/U32; bits1:0'}, 'RAW_SAMPLE_COUNT': {'rw': 'RO', 'reset': 'static geometry constant', 'side_effect': 'none', 'source': 'lab07_raw_control:2048', 'width_encoding': '32 meaningful/U32; U32=2048'}, 'RAW_CHANNEL_MASK': {'rw': 'RO', 'reset': 'static geometry constant', 'side_effect': 'none', 'source': 'lab07_raw_control:3 (accepted pair contract)', 'width_encoding': '2 meaningful/U32; bits1:0=3'}, 'RAW_FRAME_BYTES': {'rw': 'RO', 'reset': 'static geometry constant', 'side_effect': 'none', 'source': 'lab07_raw_control:8192', 'width_encoding': '32 meaningful/U32; U32=8192'}, 'RAW_WINDOW_OFFSET': {'rw': 'RO', 'reset': 'static geometry constant', 'side_effect': 'none', 'source': 'lab07_raw_control:0', 'width_encoding': '32 meaningful/U32; U32=0'}, 'RAW_WINDOW_SIZE_BYTES': {'rw': 'RO', 'reset': 'static geometry constant', 'side_effect': 'none', 'source': 'lab07_raw_control:8192', 'width_encoding': '32 meaningful/U32; U32=8192'}, 'RAW_FORMAT': {'rw': 'RO', 'reset': 'static geometry constant', 'side_effect': 'none', 'source': 'lab07_raw_control:0x00010001', 'width_encoding': '32 meaningful/U32; U32=0x00010001'}, 'RAW_ACK_BANK': {'rw': 'RW staging', 'reset': 'M/A local clear0', 'side_effect': 'fresh valid full-word staging; invalid/partial clears corresponding written flag', 'source': 'lab07_raw_control:bank_staging', 'width_encoding': '1 meaningful/U32; bit0'}, 'RAW_ACK_TOKEN': {'rw': 'RW staging', 'reset': 'M/A local clear0', 'side_effect': 'fresh valid full-word staging; invalid/partial clears corresponding written flag', 'source': 'lab07_raw_control:token_staging', 'width_encoding': '32 meaningful/U32; U32'}, 'RAW_ACK': {'rw': 'WO/read0', 'reset': 'M/A local clear0', 'side_effect': '1:consume fresh args/fence/reserve one ACK edge;0:no-op;invalid:error', 'source': 'lab07_raw_control:read0 / command FSM', 'width_encoding': '32 meaningful/U32; U32 command'}, 'RAW_ACK_RESULT': {'rw': 'RO', 'reset': 'M/A local clear0', 'side_effect': 'none', 'source': 'lab07_raw_control:ack_reservation bit31 / result_code low8', 'width_encoding': '32 meaningful/U32; busy[31],code[7:0]'}, 'RAW_ACK_COMPLETED_TOKEN': {'rw': 'RO', 'reset': 'M/A local clear0', 'side_effect': 'none', 'source': 'lab07_raw_control:completed_token', 'width_encoding': '32 meaningful/U32; U32'}}
from dataclasses import replace
RAW_REGISTERS = {}
REGISTERS['RAW_DESCRIPTOR_VALID']=replace(REGISTERS['RAW_DESCRIPTOR_VALID'],bits=1,region="raw_control")
RAW_REGISTERS['RAW_DESCRIPTOR_VALID']=REGISTERS['RAW_DESCRIPTOR_VALID']
REGISTERS['RAW_BANK_ID']=replace(REGISTERS['RAW_BANK_ID'],bits=1,region="raw_control")
RAW_REGISTERS['RAW_BANK_ID']=REGISTERS['RAW_BANK_ID']
REGISTERS['RAW_FRAME_ID']=replace(REGISTERS['RAW_FRAME_ID'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_FRAME_ID']=REGISTERS['RAW_FRAME_ID']
REGISTERS['RAW_OWNER_TOKEN']=replace(REGISTERS['RAW_OWNER_TOKEN'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_OWNER_TOKEN']=REGISTERS['RAW_OWNER_TOKEN']
REGISTERS['RAW_FRAME_STATUS']=replace(REGISTERS['RAW_FRAME_STATUS'],bits=8,region="raw_control")
RAW_REGISTERS['RAW_FRAME_STATUS']=REGISTERS['RAW_FRAME_STATUS']
REGISTERS['RAW_BANK_STATES']=replace(REGISTERS['RAW_BANK_STATES'],bits=8,region="raw_control")
RAW_REGISTERS['RAW_BANK_STATES']=REGISTERS['RAW_BANK_STATES']
REGISTERS['RAW_COMPLETE_PENDING_MASK']=replace(REGISTERS['RAW_COMPLETE_PENDING_MASK'],bits=2,region="raw_control")
RAW_REGISTERS['RAW_COMPLETE_PENDING_MASK']=REGISTERS['RAW_COMPLETE_PENDING_MASK']
REGISTERS['RAW_SAMPLE_COUNT']=replace(REGISTERS['RAW_SAMPLE_COUNT'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_SAMPLE_COUNT']=REGISTERS['RAW_SAMPLE_COUNT']
REGISTERS['RAW_CHANNEL_MASK']=replace(REGISTERS['RAW_CHANNEL_MASK'],bits=2,region="raw_control")
RAW_REGISTERS['RAW_CHANNEL_MASK']=REGISTERS['RAW_CHANNEL_MASK']
REGISTERS['RAW_FRAME_BYTES']=replace(REGISTERS['RAW_FRAME_BYTES'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_FRAME_BYTES']=REGISTERS['RAW_FRAME_BYTES']
REGISTERS['RAW_WINDOW_OFFSET']=replace(REGISTERS['RAW_WINDOW_OFFSET'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_WINDOW_OFFSET']=REGISTERS['RAW_WINDOW_OFFSET']
REGISTERS['RAW_WINDOW_SIZE_BYTES']=replace(REGISTERS['RAW_WINDOW_SIZE_BYTES'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_WINDOW_SIZE_BYTES']=REGISTERS['RAW_WINDOW_SIZE_BYTES']
REGISTERS['RAW_FORMAT']=replace(REGISTERS['RAW_FORMAT'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_FORMAT']=REGISTERS['RAW_FORMAT']
REGISTERS['RAW_ACK_BANK']=replace(REGISTERS['RAW_ACK_BANK'],bits=1,region="raw_control")
RAW_REGISTERS['RAW_ACK_BANK']=REGISTERS['RAW_ACK_BANK']
REGISTERS['RAW_ACK_TOKEN']=replace(REGISTERS['RAW_ACK_TOKEN'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_ACK_TOKEN']=REGISTERS['RAW_ACK_TOKEN']
REGISTERS['RAW_ACK']=replace(REGISTERS['RAW_ACK'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_ACK']=REGISTERS['RAW_ACK']
REGISTERS['RAW_ACK_RESULT']=replace(REGISTERS['RAW_ACK_RESULT'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_ACK_RESULT']=REGISTERS['RAW_ACK_RESULT']
REGISTERS['RAW_ACK_COMPLETED_TOKEN']=replace(REGISTERS['RAW_ACK_COMPLETED_TOKEN'],bits=32,region="raw_control")
RAW_REGISTERS['RAW_ACK_COMPLETED_TOKEN']=REGISTERS['RAW_ACK_COMPLETED_TOKEN']
IDENTIFICATION = {'MAGIC': 1347505463, 'CORE_ID': 458753, 'REGMAP_VERSION': 131073, 'FEATURE_CAPABILITY': 383, 'RAW_CAPABILITY': 15, 'BASELINE_ID': 422965948, 'FRAME_SAMPLES': 2048, 'SAMPLE_RATE_NOMINAL_HZ': 10000}
BASE_ADDRESS = 0x43C00000
APERTURE = 0x1000
INSTANCE_NAME = "lab07_mmio"
BIT_SHA256 = "085da4540128571075c287cf96e1265982d7180a219928d5995219b41e52971a"
HWH_SHA256 = "e39c46c086b76020e44ce680104aa45dfc2ef747efbcb2de93dea910853cf291"
RELEASE_STEM = "pq_lab07_feature_raw_mmio_v1"
DCP_SHA256 = "1ed1564f0d49aed4140c9ece4fee0efa0f6b2ef84038005235199bd4691173fa"
FEATURE_CAPABILITY_BITS = {"BASIC_RMS_PEAK":0, "CREST":1, "CH1_FREQUENCY":2, "NUMERIC_SPECTRAL_FEATURES":3, "SPECTRAL_NUMERIC_VALIDITY":4, "LIVE_DIAGNOSTICS":5, "ATOMIC_SNAPSHOT_SEQ":6, "PRODUCTION_IDENTITY_CLASSIFIER":7, "FORMAL_DIAGNOSTICS":8, "SAG_SWELL_INTERRUPTION":16}
RAW_CAPABILITY_BITS = {"CONTROL":0, "BULK_READ":1, "TOKEN":2, "DUAL_BANKS":3}
VALID_BITS = {"CH1_RMS":0, "CH2_RMS":1, "CH1_PEAK":2, "CH2_PEAK":3, "CH1_CREST":4, "CH2_CREST":5, "CH1_FREQUENCY_MHZ":6, "CH1_SPECTRAL":7, "CH2_SPECTRAL":8}
NUMERIC_BITS = {"VALID":0, "FFT_FAILURE":1, "LOW_FUNDAMENTAL":2, "FREQUENCY_GUARD_FAILURE":3, "RANGE_BOUNDARY_GUARD_USED":4, "GEOMETRY_FAILURE":5, "CLIP_SUSPECTED":6, "NUMERIC_OR_OVERFLOW_FAILURE":7}
NUMERIC_FATAL_MASK = sum(1 << b for n,b in NUMERIC_BITS.items() if n not in ("VALID", "RANGE_BOUNDARY_GUARD_USED"))
NUMERIC_DEFINED_MASK = sum(1 << b for b in NUMERIC_BITS.values())
FORMAL_BITS = {"ACCEPTANCE":0, "LOW_FUNDAMENTAL":2, "NONPOSITIVE_OR_NOT_FOUND":3, "UNKNOWN_OR_AMBIGUOUS":4, "FREQUENCY_FAILURE":5, "BOUNDARY_WARNING":6, "GEOMETRY_FAILURE":7, "CLIP_SUSPECTED":8, "NUMERIC_OR_OVERFLOW_FAILURE":9, "FFT_FAILURE":10}
FORMAL_DEFINED_MASK = sum(1 << b for b in FORMAL_BITS.values())
TIME_BITS = {"PUBLISHED":0, "FRAME_ERROR_STICKY":1, "ABORT_STICKY":2, "SUMMARY_OVERRUN_STICKY":3, "RESULT_OVERRUN_STICKY":4, "FREQUENCY_ANOMALY":5}
IDENTITY_NAMES = {0:"UNKNOWN", 1:"ACCEPTED", 2:"AMBIGUOUS", 3:"NOT_FOUND"}
CHANNEL_STATUS_SHIFT = {"CH1":0, "CH2":16}
CHANNEL_IDENTITY_SHIFT = {"CH1":0, "CH2":2}
BASIC_FIELDS = tuple(n for n in REGISTERS if n in VALID_BITS)
BASIC_VALID_MASK = sum(1 << VALID_BITS[n] for n in BASIC_FIELDS)
SPECTRAL_FIELDS = {c:tuple(n for n in REGISTERS if n.startswith(c+"_") and (n.rsplit("_",1)[-1] in ("H1","H3","H5","H7","H9") or "_THD_ODD_" in n)) for c in ("CH1","CH2")}
SNAPSHOT_BODY = ("SNAPSHOT_VALID", "FRAME_ID", "FEATURE_VALID_MASK", "FEATURE_ACQUISITION_VALID", "TIME_STATUS") + BASIC_FIELDS + ("SPECTRAL_NUMERIC_STATUS",) + SPECTRAL_FIELDS["CH1"] + SPECTRAL_FIELDS["CH2"] + ("FORMAL_IDENTITY", "SPECTRAL_STATUS")
ACTIVE_REGISTERS = {n:s for n,s in REGISTERS.items() if s.region != "raw_control"}
SEQ_MODULUS = 1 << 32
SEQ_HALF_SPACE = 1 << 31
MAX_SAFE_WINDOW = SEQ_MODULUS / 125000000.0
assert len(ACTIVE_REGISTERS) == 58 and len(REGISTERS) == 76
assert len(SNAPSHOT_BODY) == 27 and len(set(SNAPSHOT_BODY)) == 27

FEATURE_BASE=BASE_ADDRESS
FEATURE_RANGE=APERTURE
RAW_BASE=0x43C10000
RAW_RANGE=0x2000
ABI_SUPPORTED=(2,1)
ABI_LEGACY=(2,0)
FEATURE_CAP=IDENTIFICATION['FEATURE_CAPABILITY']
RAW_CAP=IDENTIFICATION['RAW_CAPABILITY']
SAMPLES=IDENTIFICATION['FRAME_SAMPLES']
FRAME_BYTES=RAW_RANGE
FORMAT=0x00010001
RAW_FIELDS=('RAW_DESCRIPTOR_VALID','RAW_BANK_ID','RAW_FRAME_ID','RAW_SAMPLE_COUNT','RAW_CHANNEL_MASK','RAW_FRAME_STATUS','RAW_FRAME_BYTES','RAW_WINDOW_OFFSET','RAW_WINDOW_SIZE_BYTES','RAW_FORMAT')
ACK_RESULTS={0:'IDLE',1:'ACCEPTED',2:'BANK_TOKEN_MISMATCH',3:'NO_OWNER',4:'EPOCH_INVALIDATED',5:'BAD_COMMAND_OR_STAGING',6:'READS_NOT_DRAINED'}
ACK_BUSY=1<<31
def offset(name):return REGISTERS[name].offset
