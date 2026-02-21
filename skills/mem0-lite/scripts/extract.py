#!/usr/bin/env python3
"""
extract.py - Groq-powered memory extraction with security fixes.

Security features:
1. JWT token verification for namespace isolation
2. Category-based RBAC for wildcard queries
3. Audit logging for all operations
4. TTL-based memory expiration

Usage:
  export JWT_SECRET="your-secret"
  export OPENCLAW_TOKEN="eyJhbGc..."
  python3 extract.py --text "Facts to extract"
  python3 extract.py --search "query"
  python3 extract.py --delete <memory_id>
  python3 extract.py --prune --days 30
"""

import json
import os
import sys
import argparse
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# JWT support (optional, falls back to env var if not installed)
try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

# Configuration from environment
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "")

# Paths
DATA_DIR = Path(os.environ.get("MEM0_DATA", "/home/openclaw/.openclaw/workspace/skills/mem0-lite/data"))
MEMORIES_FILE = DATA_DIR / "memories.json"
AUDIT_LOG = DATA_DIR / "audit.log"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default TTL for memories (days)
DEFAULT_TTL_DAYS = int(os.environ.get("MEM0_TTL_DAYS", 90))

# Role permissions for RBAC
ROLE_PERMISSIONS = {
    "admin": {"categories": ["*"], "can_write": True, "can_delete": True},
    "producer": {"categories": ["project", "timeline", "team", "film", "default"], "can_write": True, "can_delete": False},
    "assistant": {"categories": ["project", "public", "default"], "can_write": True, "can_delete": False},
    "viewer": {"categories": ["public", "default"], "can_write": False, "can_delete": False}
}


class SecurityError(Exception):
    """Raised when security check fails."""
    pass


class MemoryError(Exception):
    """Raised when memory operation fails."""
    pass


# ============== AUDIT LOGGING ==============

def log_audit(action: str, user_id: str, agent_id: str, memory_id: str = None, details: str = None, 
              success: bool = True):
    """Log all memory operations for security auditing."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "agent_id": agent_id,
        "memory_id": memory_id,
        "success": success,
        "details": details
    }
    try:
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except IOError as e:
        print(f"Warning: Could not write audit log: {e}", file=sys.stderr)


# ============== IDENTITY VERIFICATION ==============

def verify_token(token: str) -> dict:
    """Verify JWT token and extract claims."""
    if not HAS_JWT:
        raise SecurityError("JWT library not installed. Install with: pip install pyjwt")
    
    if not JWT_SECRET:
        raise SecurityError("JWT_SECRET not configured")
    
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False
            }
        )
        return {
            "user_id": payload.get("sub", payload.get("user_id", "default")),
            "agent_id": payload.get("agent_id", "default"),
            "role": payload.get("role", "assistant")
        }
    except jwt.ExpiredSignatureError:
        raise SecurityError("Token expired")
    except jwt.InvalidTokenError as e:
        raise SecurityError(f"Invalid token: {e}")


def get_identity_from_env() -> dict:
    """Get identity from environment variables (less secure, for development only)."""
    return {
        "user_id": os.environ.get("OPENCLAW_USER_ID", "default"),
        "agent_id": os.environ.get("OPENCLAW_AGENT_ID", "default"),
        "role": os.environ.get("OPENCLAW_ROLE", "assistant")
    }


def get_verified_identity() -> dict:
    """Get verified identity from token or environment."""
    if OPENCLAW_TOKEN:
        return verify_token(OPENCLAW_TOKEN)
    
    # Fallback to environment (development mode)
    if os.environ.get("MEM0_DEV_MODE", "").lower() == "true":
        return get_identity_from_env()
    
    raise SecurityError("No authentication configured. Set OPENCLAW_TOKEN or enable MEM0_DEV_MODE=true")


def verify_access(user_id: str, agent_id: str = None, required_permission: str = "read") -> dict:
    """
    Verify access permissions.
    
    Args:
        user_id: Requested user_id
        agent_id: Requested agent_id (optional)
        required_permission: "read", "write", or "delete"
    
    Returns:
        Verified identity dict
    
    Raises:
        SecurityError if access denied
    """
    identity = get_verified_identity()
    verified_user = identity["user_id"]
    verified_agent = identity["agent_id"]
    role = identity["role"]
    
    # Check user_id match
    if user_id != verified_user:
        log_audit(f"{required_permission}_denied", user_id, agent_id or verified_agent,
                  details=f"User mismatch: token={verified_user}, request={user_id}", success=False)
        raise SecurityError(f"Cannot access user '{user_id}'. You are '{verified_user}'.")
    
    # Check agent_id match (namespace isolation)
    if agent_id and agent_id != verified_agent:
        log_audit(f"{required_permission}_denied", user_id, agent_id,
                  details=f"Namespace violation: token={verified_agent}, request={agent_id}", success=False)
        raise SecurityError(f"Agent '{verified_agent}' cannot access namespace '{agent_id}'.")
    
    # Check permission
    permissions = ROLE_PERMISSIONS.get(role, {})
    if required_permission == "write" and not permissions.get("can_write", False):
        log_audit(f"{required_permission}_denied", user_id, verified_agent,
                  details=f"Role '{role}' cannot write", success=False)
        raise SecurityError(f"Role '{role}' does not have write permission")
    
    if required_permission == "delete" and not permissions.get("can_delete", False):
        log_audit(f"{required_permission}_denied", user_id, verified_agent,
                  details=f"Role '{role}' cannot delete", success=False)
        raise SecurityError(f"Role '{role}' does not have delete permission")
    
    return identity


# ============== CATEGORY ACCESS ==============

def get_allowed_categories(role: str) -> List[str]:
    """Get list of allowed categories for role."""
    permissions = ROLE_PERMISSIONS.get(role, {"categories": ["public"]})
    return permissions["categories"]


def filter_by_category(memories: List[dict], role: str) -> List[dict]:
    """Filter memories by role's allowed categories."""
    allowed = get_allowed_categories(role)
    if "*" in allowed:
        return memories
    return [m for m in memories if m.get("category", "default") in allowed]


def check_category_access(category: str, role: str) -> bool:
    """Check if role can access this category."""
    allowed = get_allowed_categories(role)
    return "*" in allowed or category in allowed


# ============== MEMORY STORAGE ==============

def load_memories() -> List[dict]:
    """Load memories from file."""
    if not MEMORIES_FILE.exists():
        return []
    try:
        return json.loads(MEMORIES_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"Warning: Corrupt memories file: {e}", file=sys.stderr)
        return []


def save_memories(memories: List[dict]):
    """Save memories to file."""
    MEMORIES_FILE.write_text(json.dumps(memories, indent=2, ensure_ascii=False))


def is_memory_expired(memory: dict) -> bool:
    """Check if memory has expired based on TTL."""
    created_at = memory.get("created_at")
    ttl_days = memory.get("ttl_days", DEFAULT_TTL_DAYS)
    
    if not created_at:
        return False
    
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        expires = created + timedelta(days=ttl_days)
        return datetime.now(timezone.utc) > expires
    except (ValueError, TypeError):
        return False


def prune_expired_memories(memories: List[dict]) -> tuple:
    """Remove expired memories. Returns (pruned_list, removed_count)."""
    valid = []
    removed = 0
    for m in memories:
        if is_memory_expired(m):
            removed += 1
        else:
            valid.append(m)
    return valid, removed


# ============== GROQ EXTRACTION ==============

def groq_extract(text: str) -> List[dict]:
    """Ruft Groq API auf, extrahiert strukturierte Fakten."""
    import urllib.request
    import ssl

    if not GROQ_API_KEY:
        raise MemoryError("GROQ_API_KEY nicht gesetzt")

    SSL_CTX = ssl.create_default_context()

    prompt = f"""Analysiere folgenden Text und extrahiere alle relevanten Fakten über Personen, Projekte, Präferenzen, Deadlines und Entscheidungen.

Antworte NUR mit einem JSON-Array. Jedes Objekt hat:
- "fact": der extrahierte Fakt (kurz, präzise, auf Deutsch)
- "entity": Hauptentität (Person/Projekt/Tool/etc.)
- "relation": Beziehungstyp (z.B. "arbeitet_an", "mag", "hat_deadline", "lernt", "entschieden")
- "target": Zielobjekt wenn vorhanden
- "category": Kategorie (z.B. "project", "person", "deadline", "preference", "financial")

Text:
{text}

JSON-Array:"""

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1024
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.88.1"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"].strip()
            
            # Extract JSON from markdown code blocks if present
            if "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
            
            # Parse JSON with error handling
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse Groq response: {e}", file=sys.stderr)
                print(f"Response was: {content[:200]}...", file=sys.stderr)
                return []
                
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        raise MemoryError(f"Groq API error {e.code}: {body}")
    except urllib.error.URLError as e:
        raise MemoryError(f"Network error: {e}")
    except Exception as e:
        raise MemoryError(f"Unexpected error: {e}")


# ============== MEMORY OPERATIONS ==============

def add_memory(text: str, user_id: str, source: str = "manual", agent_id: str = None, 
               ttl_days: int = None) -> int:
    """
    Extract and store facts from text.
    
    Returns:
        Number of facts added
    """
    # Verify access
    identity = verify_access(user_id, agent_id, "write")
    role = identity["role"]
    verified_agent = identity["agent_id"]
    
    # Extract facts
    facts = groq_extract(text)
    if not facts:
        print("Keine Fakten extrahiert.")
        return 0

    memories = load_memories()
    now = datetime.now(timezone.utc).isoformat()
    added = 0

    for fact in facts:
        if not isinstance(fact, dict) or "fact" not in fact:
            continue
        
        fact_text = fact.get("fact", "")
        if not fact_text:
            continue
            
        category = fact.get("category", "default")
        
        # Check category access
        if not check_category_access(category, role):
            log_audit("category_denied", user_id, verified_agent, 
                      details=f"Category '{category}' not allowed for role '{role}'", success=False)
            continue

        # Deduplication via hash
        fact_id = hashlib.md5(fact_text.encode()).hexdigest()[:8]
        if any(m.get("id") == fact_id for m in memories):
            continue

        memories.append({
            "id": fact_id,
            "fact": fact_text,
            "entity": fact.get("entity", ""),
            "relation": fact.get("relation", ""),
            "target": fact.get("target", ""),
            "category": category,
            "user_id": user_id,
            "agent_id": verified_agent,
            "role": role,
            "source": source,
            "created_at": now,
            "ttl_days": ttl_days or DEFAULT_TTL_DAYS
        })
        log_audit("write", user_id, verified_agent, fact_id, fact_text[:50])
        print(f"  ✅ {fact_text}")
        added += 1

    save_memories(memories)
    print(f"\n{added} neue Fakten gespeichert ({len(memories)} gesamt).")
    return added


def search_memories(query: str, user_id: str) -> List[dict]:
    """Search memories by keyword with security filtering."""
    # Verify read access
    identity = verify_access(user_id, required_permission="read")
    role = identity["role"]
    agent_id = identity["agent_id"]
    
    memories = load_memories()
    
    # Filter by user
    memories = [m for m in memories if m.get("user_id") == user_id]
    
    # Filter by category (security)
    memories = filter_by_category(memories, role)
    
    # Filter expired
    memories, _ = prune_expired_memories(memories)
    
    # Keyword search
    query_lower = query.lower()
    results = [
        m for m in memories
        if query_lower in m.get("fact", "").lower()
        or query_lower in m.get("entity", "").lower()
        or query_lower in m.get("target", "").lower()
    ]
    
    log_audit("search", user_id, agent_id, details=f"Query: {query}")
    return results


def list_memories(user_id: str, limit: int = 20) -> List[dict]:
    """List all accessible memories."""
    identity = verify_access(user_id, required_permission="read")
    role = identity["role"]
    
    memories = load_memories()
    
    # Filter by user
    memories = [m for m in memories if m.get("user_id") == user_id]
    
    # Filter by category
    memories = filter_by_category(memories, role)
    
    # Filter expired
    memories, _ = prune_expired_memories(memories)
    
    # Display
    for m in memories[-limit:]:
        entity = f"[{m.get('entity', '?')}]" if m.get("entity") else ""
        cat = f"({m.get('category', '?')})" if m.get("category") else ""
        fact = m.get("fact", "?")
        print(f"  {entity} {fact} {cat}")
    
    print(f"\n{len(memories)} Memories total.")
    return memories


def delete_memory(memory_id: str, user_id: str) -> bool:
    """Delete a memory by ID."""
    identity = verify_access(user_id, required_permission="delete")
    agent_id = identity["agent_id"]
    
    memories = load_memories()
    
    # Find and remove
    for i, m in enumerate(memories):
        if m.get("id") == memory_id and m.get("user_id") == user_id:
            deleted = memories.pop(i)
            save_memories(memories)
            log_audit("delete", user_id, agent_id, memory_id, deleted.get("fact", "")[:50])
            print(f"✅ Deleted: {deleted.get('fact', '')}")
            return True
    
    print(f"Memory {memory_id} not found or access denied.")
    return False


def prune_memories(user_id: str, days: int = 30, min_access: int = 0) -> int:
    """Remove old memories based on age and access count."""
    identity = verify_access(user_id, required_permission="delete")
    agent_id = identity["agent_id"]
    
    memories = load_memories()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    kept = []
    removed = 0
    
    for m in memories:
        if m.get("user_id") != user_id:
            kept.append(m)
            continue
        
        # Check age and access
        is_old = m.get("created_at", "") < cutoff
        is_low_access = m.get("access_count", 1) < min_access
        
        if is_old and is_low_access:
            removed += 1
            log_audit("prune", user_id, agent_id, m.get("id"), m.get("fact", "")[:50])
        else:
            kept.append(m)
    
    save_memories(kept)
    print(f"Removed {removed} memories (older than {days} days, access < {min_access}).")
    return removed


# ============== CLI ==============

def main():
    parser = argparse.ArgumentParser(description="mem0-lite: Secure Groq Memory Extractor")
    parser.add_argument("--text", "-t", help="Text to analyze")
    parser.add_argument("--user", "-u", default=os.environ.get("OPENCLAW_USER_ID", "default"), help="User ID")
    parser.add_argument("--agent", "-a", help="Agent ID (must match token)")
    parser.add_argument("--list", "-l", action="store_true", help="List memories")
    parser.add_argument("--search", "-s", help="Search memories")
    parser.add_argument("--delete", "-d", help="Delete memory by ID")
    parser.add_argument("--prune", action="store_true", help="Prune old memories")
    parser.add_argument("--days", type=int, default=30, help="Days threshold for prune")
    parser.add_argument("--limit", type=int, default=20, help="Limit for list")
    parser.add_argument("--ttl", type=int, help="TTL in days for new memories")
    args = parser.parse_args()

    try:
        if args.list:
            list_memories(args.user, args.limit)
        elif args.search:
            results = search_memories(args.search, args.user)
            for r in results:
                cat = f"({r.get('category', '?')})" if r.get("category") else ""
                print(f"  [{r.get('entity', '?')}] {r.get('fact', '?')} {cat}")
            print(f"\n{len(results)} Treffer.")
        elif args.delete:
            delete_memory(args.delete, args.user)
        elif args.prune:
            prune_memories(args.user, args.days)
        elif args.text:
            print(f"Extrahiere Fakten aus Text...\n")
            add_memory(args.text, args.user, agent_id=args.agent, ttl_days=args.ttl)
        elif not sys.stdin.isatty():
            text = sys.stdin.read().strip()
            if text:
                print(f"Extrahiere Fakten aus Stdin...\n")
                add_memory(text, args.user, agent_id=args.agent, ttl_days=args.ttl)
        else:
            parser.print_help()
    except SecurityError as e:
        print(f"Security Error: {e}", file=sys.stderr)
        sys.exit(1)
    except MemoryError as e:
        print(f"Memory Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
