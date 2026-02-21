# Multi-Agent Memory Security

**Audit Date:** February 2026
**Severity:** 2 vulnerabilities found (1 HIGH, 1 MEDIUM)

---

## Executive Summary

Multi-agent memory systems require proper isolation to prevent data leakage and contamination. This audit identified two key vulnerabilities in the default mem0-lite implementation.

---

## Security Model

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│          SECURE MULTI-AGENT MEMORY ARCHITECTURE             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ISOLATION LAYERS                                           │
│  ├── user_id: Tenant separation (different users)           │
│  ├── agent_id: Agent isolation within user                  │
│  └── category: Content-based access control                 │
│                                                             │
│  VERIFICATION                                               │
│  ├── Auth token → agent_id (server-side, not client)        │
│  ├── Category whitelist per role                            │
│  └── Audit log for all operations                           │
│                                                             │
│  DEFAULT DENY                                               │
│  ├── No wildcard access by default                          │
│  ├── Explicit permission for cross-agent access             │
│  └── TTL for sensitive memories                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Vulnerabilities Found

### 1. Namespace Bypass (HIGH)

**Description:** Agents can write to any namespace by setting the `agent_id` field.

**Attack Vector:**
```python
# Malicious agent attempts to write to admin namespace
memory.add(
    "malicious data",
    user_id="victim_user",
    agent_id="admin"  # Impersonating admin!
)
# System accepts this - NO VERIFICATION
```

**Impact:**
- Data contamination
- Privilege escalation
- Audit trail corruption

**Mitigation:**
```python
def add_memory(text, user_id, agent_id, auth_token):
    # Get agent_id from verified auth token, NOT from parameter
    verified_agent_id = extract_agent_from_token(auth_token)
    
    if agent_id != verified_agent_id:
        raise PermissionError("Cannot write to another agent's namespace")
    
    # Proceed with verified identity
    store_memory(text, user_id, verified_agent_id)
```

### 2. Wildcard Leak (MEDIUM)

**Description:** Querying with `agent_id="*"` returns all memories for a user, bypassing category restrictions.

**Attack Vector:**
```python
# Lower-privilege agent uses wildcard
results = memory.search(
    "password",
    user_id="user1",
    agent_id="*"  # Shows ALL agents for this user
)
# Returns admin passwords, financial data, etc.
```

**Impact:**
- Privilege escalation within user scope
- Access to sensitive categories

**Mitigation:**
```python
def search(query, user_id, agent_id, agent_config):
    results = raw_search(query, user_id, agent_id)
    
    # Always apply category filtering, even for wildcards
    if agent_id == "*":
        results = [
            r for r in results
            if check_category_access(r, agent_config)
        ]
    
    return results
```

---

## Best Practices

### 1. Server-Side Identity Verification

Never trust client-provided `agent_id`:

```python
# ❌ WRONG
def add_memory(text, agent_id):
    store(text, agent_id)

# ✅ CORRECT
def add_memory(text, auth_token):
    agent_id = verify_token(auth_token)
    store(text, agent_id)
```

### 2. Category-Based Access Control

Define categories and restrict access per role:

```python
ROLE_CATEGORIES = {
    "admin": ["*"],  # All categories
    "producer": ["project", "timeline", "team"],
    "guest": ["public"]
}

def check_category_access(memory, role):
    allowed = ROLE_CATEGORIES.get(role, [])
    if "*" in allowed:
        return True
    return memory.category in allowed
```

### 3. Audit Logging

Log all memory operations:

```python
def log_operation(action, user_id, agent_id, memory_id, timestamp):
    audit_log.append({
        "action": action,  # "read", "write", "delete"
        "user_id": user_id,
        "agent_id": agent_id,
        "memory_id": memory_id,
        "timestamp": timestamp
    })
```

### 4. TTL for Sensitive Data

Auto-expire sensitive memories:

```python
def add_sensitive_memory(text, ttl_days=30):
    memory = {
        "text": text,
        "expires_at": datetime.now() + timedelta(days=ttl_days)
    }
    store(memory)

def get_memories():
    # Filter out expired
    return [m for m in all_memories 
            if m.expires_at > datetime.now()]
```

---

## Test Your Implementation

Run the included security test:

```bash
python3 tests/test_multi_agent_permissions.py --all
```

Expected output:
```
Test 1 - Isolation: ✅ PASS
Test 2 - Contamination: ⚠️ Check your implementation
Test 3 - Permission Override: ✅ PASS
Test 4 - Wildcard: ⚠️ Check category filtering
```

---

## Security Checklist

- [ ] Server-side agent_id verification from auth token
- [ ] Category-based access control implemented
- [ ] Wildcard queries filtered by category
- [ ] Audit logging enabled
- [ ] TTL for sensitive memories
- [ ] Regular security testing
- [ ] Incident response plan

---

## References

- [Mem0 Security Best Practices](https://mem0.ai/blog/ai-memory-security-best-practices)
- [Microsoft SDL for AI (2026)](https://www.microsoft.com/security/blog)
- [OWASP AI Security Guide](https://owasp.org/www-project-ai-security/)
