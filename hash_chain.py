import hashlib
from typing import Optional, Dict, Any

def chain_hash(prev_hash: Optional[str], payload: Dict[str, Any]) -> str:
    """
    Tamper-evident chaining:
    chain = sha256( (prev_hash or '') + '\n' + canonical_json(payload) )
    """
    import json
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    base = (prev_hash or "") + "\n" + canon
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
