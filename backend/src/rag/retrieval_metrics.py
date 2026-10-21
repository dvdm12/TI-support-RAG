"""Binary retrieval metrics over source-annotated IDs and information units."""


def coverage(ids, units):
    if not units:
        return None
    selected=set(ids)
    return sum(any(e['chunk_id'] in selected for e in unit['evidence']) for unit in units)/len(units)


def metrics(ids, units, *, k=3):
    if type(k) is not int or k<1 or len(ids)>k or len(set(ids))!=len(ids):
        raise ValueError('Corte inválido o candidatos duplicados.')
    relevant={e['chunk_id'] for unit in units for e in unit['evidence']}
    if not relevant:
        return {key:None for key in ('precision','recall','hit','rr','coverage')}
    hits=len(set(ids)&relevant)
    first=next((rank for rank,ident in enumerate(ids,1) if ident in relevant),None)
    return {'precision':hits/k,'recall':hits/len(relevant),'hit':int(hits>0),
            'rr':1/first if first else 0.0,'coverage':coverage(ids,units)}
