"""One error vocabulary shared by feature/raw and future hardware runner."""
class Lab07Error(RuntimeError):
    def __init__(self,code,detail='',recovery=None):
        self.code,self.detail,self.recovery=code,detail,recovery
        super().__init__(code+(': '+detail if detail else ''))

class RawReadError(Lab07Error):
    def __init__(self,message,recovery=None):
        mappings=(('ACK','RAW_ACK_UNCERTAIN'),('SAMPLE_COUNT','RAW_SAMPLE_COUNT_MISMATCH'),
                  ('lease/epoch','EPOCH_CHANGED'),('lease busy','RAW_LEASE_BUSY'),
                  ('descriptor changed','RAW_DESCRIPTOR_INCOHERENT'),('descriptor RETRY','RAW_DESCRIPTOR_INCOHERENT'),
                  ('metadata/geometry','RAW_FRAME_INVALID'),('partial','RAW_PARTIAL_COPY'),
                  ('copy failed','RAW_PARTIAL_COPY'),('data response','MMIO_ERROR'))
        code=next((code for text,code in mappings if text in message),message.split(' ')[0])
        if not code.startswith(('RAW_','EPOCH_','MMIO_','ABI_')):code='MMIO_ERROR'
        super().__init__(code,message,recovery)

