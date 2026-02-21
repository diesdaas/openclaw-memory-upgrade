#!/usr/bin/env python3
"""
extract.py - Groq-powered memory extraction with security fixes.

Security features:
1. JWT token verification for namespace isolation
2. Category-based RBAC for wildcard queries
3. Audit logging for all operations

Usage:
  export JWT_SECRET="your-secret"
  export OPENCLAW_TOKEN="eyJhbGc..."
  python3 extract.py --text "Facts to extract"
"""

import json
import os
import sys
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# JWT support (optional, falls back to env var if not installed)
try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
OPENCLAW_TOKEN = os.environ.get("OPENCLAW_TOKEN", "")

DATA_DIR = Path(os.environ.get("MEM0_DATA", "/home/openclaw/.openclaw/workspace/skills/mem0-lite/data"))
MEMORIES_FILE = DATA_DIR / "memories.json"
AUDIT_LOG = DATA_DIR / "audit.log"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Role permissions for RBAC
ROLE_PERMISSIONS = {
    "admin": {"categories": ["*"], "can_write": True},
    "producer": {"categories": ["project", "timeline", "team", "film"], "can_write": True},
    "assistant": {"categories": ["project", "public"], "can_write": True},
    "viewer": {"categories": ["public"], "can_write": False}
}


def log_audit(action: str, user_id: str, agent_id: str, memory_id: str = None, details: str = None):
    """Log all memory operations for security auditing."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "agent_id": agent_id,
        "memory_id": memory_id,
        "details": details
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def verify_token(token: str) -> dict:
    """Verify JWT token and extract claims."""
    if not HAS_JWT:
        # Fallback: use environment variable for agent identity
        return {
            "user_id": os.environ.get("OPENCLAW_USER_ID", "default"),
            "agent_id": os.environ.get("OPENCLAW_AGENT_ID", "default"),
            "role": os.environ.get("OPENCLAW_ROLE", "assistant")
        }
    
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
        raise PermissionError("Token expired")
    except jwt.InvalidTokenError as e:
        raise PermissionError(f"Invalid token: {e}")


def get_verified_identity() -> dict:
    """Get verified identity from token or environment."""
    if OPENCLAW_TOKEN:
        return verify_token(OPENCLAW_TOKEN)
    return {
        "user_id": os.environ.get("OPENCLAW_USER_ID", "default"),
        "agent_id": os.environ.get("OPENCLAW_AGENT_ID", "default"),
        "role": os.environ.get("OPENCLAW_ROLE", "assistant")
    }


def check_category_access(category: str, role: str) -> bool:
    """Check if role can access this category."""
    permissions = ROLE_PERMISSIONS.get(role, {"categories": ["public"]})
    allowed = permissions["categories"]
    return "*" in allowed or category in allowed


def load_memories():
    if MEMORIES_FILE.exists():
        return json.loads(MEMORIES_FILE.read_text())
    return []


def save_memories(memories):
    MEMORIES_FILE.write_text(json.dumps(memories, indent=2, ensure_ascii=False))


def groq_extract(text: str) -> list[dict]:
    """Ruft Groq API auf, extrahiert strukturierte Fakten."""
    import urllib.request
    import ssl

    if not GROQ_API_KEY:
        print("FEHLER: GROQ_API_KEY nicht gesetzt", file=sys.stderr)
        return []

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
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        print(f"FEHLER bei Groq-Aufruf: {e}", file=sys.stderr)
        return []


def add_memory(text: str, user_id: str = "alex", source: str = "manual", agent_id: str = None):
    """Extrahiert Fakten und speichert sie mit Security-Checks."""
    
    # SECURITY: Get verified identity
    identity = get_verified_identity()
    verified_user = identity["user_id"]
    verified_agent = identity["agent_id"]
    role = identity["role"]
    
    # SECURITY: Verify user_id matches token
    if user_id != verified_user:
        log_audit("write_denied", user_id, agent_id or verified_agent, 
                  details=f"Token user mismatch: token={verified_user}, request={user_id}")
        raise PermissionError(f"Cannot write as user '{user_id}'. You are '{verified_user}'.")
    
    # SECURITY: Verify agent_id matches token (namespace isolation)
    if agent_id and agent_id != verified_agent:
        log_audit("write_denied", user_id, agent_id,
                  details=f"Namespace violation: token={verified_agent}, request={agent_id}")
        raise PermissionError(f"Agent '{verified_agent}' cannot write as '{agent_id}'")
    
    # SECURITY: Check write permission
    if not ROLE_PERMISSIONS.get(role, {}).get("can_write", False):
        log_audit("write_denied", user_id, verified_agent, details=f"Role {role} cannot write")
        raise PermissionError(f"Role '{role}' does not have write permission")

    facts = groq_extract(text)
    if not facts:
        print("Keine Fakten extrahiert.")
        return

    memories = load_memories()
    now = datetime.now(timezone.utc).isoformat()
    added = 0

    for fact in facts:
        if not isinstance(fact, dict) or "fact" not in fact:
            continue
        
        fact_text = fact.get("fact", "")
        category = fact.get("category", "default")
        
        # SECURITY: Check category access
        if not check_category_access(category, role):
            log_audit("category_denied", user_id, verified_agent, 
                      details=f"Category '{category}' not allowed for role '{role}'")
            continue

        # Deduplizierung via Hash
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
            "user_id": verified_user,
            "agent_id": verified_agent,
            "role": role,
            "source": source,
            "created_at": now
        })
        log_audit("write", verified_user, verified_agent, fact_id, fact_text[:50])
        print(f"  ✅ {fact_text}")
        added += 1

    save_memories(memories)
    print(f"\n{added} neue Fakten gespeichert ({len(memories)} gesamt).")


def search_memories(query: str, user_id: str = None, agent_id: str = None, role: str = None) -> list:
    """Sucht Memories mit Security-Filter."""
    memories = load_memories()
    
    # Get verified identity
    identity = get_verified_identity()
    verified_user = identity["user_id"]
    verified_role = role or identity["role"]
    
    # Filter by user
    if user_id:
        if user_id != verified_user:
            log_audit("search_denied", verified_user, identity["agent_id"],
                      details=f"Cannot search user {user_id}")
            raise PermissionError(f"Cannot search other user's memories")
        memories = [m for m in memories if m.get("user_id") == user_id]
    
    # SECURITY: Always apply category filter (prevents wildcard leak)
    permissions = ROLE_PERMISSIONS.get(verified_role, {"categories": ["public"]})
    allowed_categories = permissions["categories"]
    
    if "*" not in allowed_categories:
        memories = [m for m in memories
                   if m.get("category", "default") in allowed_categories]
    
    # Keyword search
    query_lower = query.lower()
    results = [
        m for m in memories
        if query_lower in m.get("fact", "").lower()
        or query_lower in m.get("entity", "").lower()
        or query_lower in m.get("target", "").lower()
    ]
    
    log_audit("search", verified_user, identity["agent_id"], details=f"Query: {query}")
    return results


def list_memories(user_id: str = None, limit: int = 20):
    """Zeigt alle gespeicherten Memories."""
    memories = load_memories()
    
    # Apply category filter based on role
    identity = get_verified_identity()
    verified_role = identity["role"]
    permissions = ROLE_PERMISSIONS.get(verified_role, {"categories": ["public"]})
    allowed = permissions["categories"]
    
    if "*" not in allowed:
        memories = [m for m in memories if m.get("category", "default") in allowed]
    
    if user_id:
        memories = [m for m in memories if m.get("user_id") == user_id]
    for m in memories[-limit:]:
        entity = f"[{m['entity']}]" if m.get("entity") else ""
        cat = f"({m.get('category', '?')})" if m.get("category") else ""
        print(f"  {entity} {m['fact']} {cat}")
    print(f"\n{len(memories)} Memories total.")


def main():
    parser = argparse.ArgumentParser(description="mem0-lite: Secure Groq Memory Extractor")
    parser.add_argument("--text", "-t", help="Text zum Analysieren")
    parser.add_argument("--user", "-u", default="alex", help="User ID")
    parser.add_argument("--agent", "-a", help="Agent ID (must match token)")
    parser.add_argument("--list", "-l", action="store_true", help="Memories anzeigen")
    parser.add_argument("--search", "-s", help="Memories suchen")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if args.list:
        list_memories(args.user, args.limit)
    elif args.search:
        results = search_memories(args.search, args.user)
        for r in results:
            cat = f"({r.get('category', '?')})" if r.get("category") else ""
            print(f"  [{r['entity']}] {r['fact']} {cat}")
        print(f"\n{len(results)} Treffer.")
    elif args.text:
        print(f"Extrahiere Fakten aus Text...\n")
        add_memory(args.text, args.user, agent_id=args.agent)
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            print(f"Extrahiere Fakten aus Stdin...\n")
            add_memory(text, args.user, agent_id=args.agent)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
