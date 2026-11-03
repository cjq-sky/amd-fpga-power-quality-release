"""Pure coordinate routing only. Does not open USB, MMIO or DMA buffers."""
PAGES=("overview","waveform","events","harmonics")
def hit_test(x,y):
    if not (0<=x<1280 and 624<=y<704): return None
    return PAGES[int(x)//320]
def scale_point(x,y,x_range,y_range):
    xmin,xmax=x_range;ymin,ymax=y_range
    if xmax<=xmin or ymax<=ymin or not (xmin<=x<=xmax and ymin<=y<=ymax):
        raise ValueError("Invalid touch range/point")
    return round((x-xmin)*1279/(xmax-xmin)),round((y-ymin)*719/(ymax-ymin))
class TouchPages:
    def __init__(self):
        self.displayed_page="overview"
    def request(self,x,y):
        page=hit_test(x,y)
        return dict(requested_page=page,displayed_page=self.displayed_page,
                    presentation="NO_NAVIGATION" if page is None or page==self.displayed_page
                    else "BLOCKED_PENDING_SAFE_BUFFER_SWITCH")
