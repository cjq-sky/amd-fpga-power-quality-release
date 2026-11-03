"""Sample-aligned amplitude envelopes. Durations include both ramps."""
import math

def envelope(case, fs, n):
    result=[1.0]*n; annotations=[]; last_end=0
    mode=case.get('event_scale_mode','all_ac')
    if mode not in ('all_ac','fundamental_only'): raise ValueError('Unknown event_scale_mode')
    for event in case.get('events',[]):
        allowed={'kind','start_s','duration_s','level','ramp_in_s','ramp_out_s'}
        if set(event)-allowed: raise ValueError('Unknown event field')
        kind=event['kind'];level=event['level']
        if isinstance(level,bool) or not isinstance(level,(int,float)) or not math.isfinite(level): raise ValueError('Invalid event level')
        if kind not in ('sag','swell','interruption'): raise ValueError('Unknown event kind')
        if (kind=='swell' and level<=1) or (kind=='sag' and not 0<level<1) or (kind=='interruption' and level!=0):
            raise ValueError('sag requires 0<level<1; swell >1; interruption exactly 0 (digital setting, not label)')
        def ticks(key,default=None):
            v=event.get(key,default)
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0: raise ValueError('Invalid event time')
            raw=v*fs; q=round(raw)
            if abs(raw-q)>1e-8: raise ValueError('Event times must align with sample grid')
            return q
        start=ticks('start_s');length=ticks('duration_s');rin=ticks('ramp_in_s',0);rout=ticks('ramp_out_s',0);end=start+length
        if length<=0 or start<=0 or end>=n or start<last_end or rin+rout>=length:
            raise ValueError('Events must be ordered, nonoverlapping, interior, with a nonempty plateau')
        for i in range(start,end):
            if rin and i<start+rin: g=1+(level-1)*(i-start)/rin
            elif rout and i>=end-rout: g=level+(1-level)*(i-(end-rout))/rout
            else:g=level
            result[i]=g
        annotations.append(dict(kind=kind,level=level,start_index=start,end_index_exclusive=end,
            plateau_start_index=start+rin,plateau_end_index_exclusive=end-rout,
            start_s=start/fs,end_s=end/fs,ramp_in_samples=rin,ramp_out_samples=rout,
            meaning='digital envelope boundaries; NOT RMS detector crossing times'))
        last_end=end
    return result,annotations,mode
