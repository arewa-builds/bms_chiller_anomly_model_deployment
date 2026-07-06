---
name: troubleshoot-opcua-connection
description: Diagnose OPC UA connection failures, security policy errors, certificate issues, and reconnection problems for the chiller bridge. Use when asyncua Client fails to connect or disconnects in production.
paths: app/opcua_bridge.py,docker-compose.yml
---

# Troubleshoot OPC UA Connection

## Symptom → diagnosis

### Connection refused / timeout

- Verify `OPC_SERVER_URL` host, port, and firewall rules from bridge container
- Ping/TCP test: `opc.tcp://host:4840` must be reachable
- Check if server requires VPN or VLAN access

### Bad security policy / endpoint mismatch

- List server endpoints with UaExpert or asyncua `get_endpoints()`
- Match `SecurityPolicy` (e.g. `Basic256Sha256`) and `MessageSecurityMode` (Sign, SignAndEncrypt)
- Lab servers often expose `SecurityPolicy#None` — production rarely does

### Certificate errors

- Generate client certificate if server requires application authentication
- Install server cert in client trust store; install client cert on server
- Check certificate expiry and hostname/CN mismatch

### Bad node ID / namespace

- `BadNodeIdUnknown` → wrong `ns=` index or `i=`/`s=` identifier
- Namespace indexes can change after server restart — prefer stable string node IDs when available
- Browse server to confirm tag still exists

### Session lost / intermittent disconnects

- Wrap main loop with reconnection logic and exponential backoff
- Do not assume `async with Client` survives overnight network blips
- Log disconnect reason and reconnect attempts

### Stale or bad data

- Check `SourceTimestamp` vs `ServerTimestamp` on reads
- Reject reads older than 2× poll interval
- Validate numeric range before `preprocessor.update()`

## asyncua connection pattern (production)

```python
async def connect_with_retry(url: str, max_attempts: int = 5):
    for attempt in range(max_attempts):
        try:
            client = Client(url=url)
            await client.connect()
            return client
        except Exception as exc:
            wait = min(2 ** attempt, 60)
            log.warning(f"OPC UA connect failed (attempt {attempt+1}): {exc}; retry in {wait}s")
            await asyncio.sleep(wait)
    raise ConnectionError(f"Could not connect to {url} after {max_attempts} attempts")
```

## Verification

1. Single-node read succeeds for all 16 `NODE_MAP` entries
2. Values are physically plausible for current chiller state
3. Bridge survives intentional server restart without manual intervention
4. Logs show UTC timestamps aligned with BMS historian
