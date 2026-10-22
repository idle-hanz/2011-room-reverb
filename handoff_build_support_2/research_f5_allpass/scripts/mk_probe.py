import render_pipeline as _RPm
_o=_RPm.ir_rms_makeup_from_inject
def _w(*a,**k):
    r=_o(*a,**k); print('MK render', [round(float(sum(x*x for x in v)),4) if hasattr(v,'__len__') else v for v in a], '->', r, file=sys.stderr); return r
_RPm.ir_rms_makeup_from_inject=_w
