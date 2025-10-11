# Checkpoint: Cluster/Local/Any Refactor - 2025-01-10

## What We're Doing

**Major architectural refactor of kstack-lib** to separate code into three contexts:

- **`cluster/`** - In-cluster only (Kubernetes pods)
- **`local/`** - Local dev machine only (CLI, tools)
- **`any/`** - Works in both (via protocols + DI)

## Why

1. **Safety**: Prevent vault code from running in production pods
2. **Clarity**: Make it obvious what runs where
3. **Testability**: Easy to mock adapters
4. **Elegance**: Clean dependency injection with `dependency-injector`

## Current Status: Phase 1 COMPLETE ✅

### What's Done

**Created new structure:**

```
kstack_lib/
├── any/
│   ├── __init__.py          ✅ Exports exceptions and context
│   ├── exceptions.py        ✅ All exceptions renamed to KStack* prefix
│   ├── context.py           ✅ is_in_cluster() - single source of truth
│   ├── config/              ✅ Created
│   ├── security/            ✅ Created
│   └── cal/                 ✅ Created
│
├── cluster/
│   ├── __init__.py          ✅ Created
│   ├── _guards.py           ✅ Import guard - raises KStackEnvironmentError
│   ├── config/              ✅ Created
│   └── security/            ✅ Created
│
└── local/
    ├── __init__.py          ✅ Created
    ├── _guards.py           ✅ Import guard - raises KStackEnvironmentError
    ├── config/              ✅ Created
    └── security/            ✅ Created
```

**Key Changes:**

1. **Exceptions renamed**:

   - `LayerAccessError` → `KStackLayerAccessError`
   - `ConfigurationError` → `KStackConfigurationError`
   - `RouteError` → `KStackRouteError`
   - `ServiceNotFoundError` → `KStackServiceNotFoundError`
   - NEW: `KStackEnvironmentError` (wrong context)

2. **Context detection**: `is_in_cluster()` checks for K8s service account token

3. **Import guards**: Importing `cluster/*` outside K8s or `local/*` inside K8s raises error

4. **Dependencies**: Added `dependency-injector>=4.41.0`

### Old Code Still In Place

**NOT YET DELETED** (still needed by existing code):

- `kstack_lib/exceptions.py` (old exception names)
- `kstack_lib/vault.py` (will move to `local/security/vault.py`)
- `kstack_lib/config/cluster.py` (will split into cluster/local)
- `kstack_lib/types.py` (will move to `any/types.py`)
- `kstack_lib/utils.py` (will move to `any/utils.py`)

**These will be deleted in Phase 5 after migration**

## Next Steps: Phases 2-5

### Phase 2: Protocols & Types

- Create `any/protocols.py` with all Protocol definitions
- Move `types.py` → `any/types.py`
- Move `utils.py` → `any/utils.py`

### Phase 3: Security Layer

- Create `any/security/protocols.py` (SecretsProvider protocol)
- Move `vault.py` → `local/security/vault.py` (with guard)
- Create `cluster/security/secrets.py` (K8s secrets adapter)
- Create `local/security/credentials.py` (vault adapter)

### Phase 4: Config Layer

- Create `any/config/protocols.py` (EnvironmentDetector protocol)
- Create `cluster/config/environment.py` (namespace-based)
- Create `local/config/environment.py` (.kstack.yaml-based)
- Split `config/cluster.py` logic into cluster/local

### Phase 5: DI Container & Migration

- Create `any/container.py` with dependency-injector
- Update all imports across codebase
- **DELETE old files** (exceptions.py, vault.py, config/cluster.py, etc.)
- Run tests and fix breakages

## How Code Will Work After Refactor

### Example 1: Using secrets (works anywhere)

```python
from kstack_lib.any.security import get_credentials

# Automatically uses K8s secrets in-cluster, vault outside
creds = get_credentials("s3", layer="layer3", environment="dev")
```

### Example 2: Direct vault access (local only)

```python
from kstack_lib.local.security import KStackVault

# Raises KStackEnvironmentError if in cluster
vault = KStackVault("dev")
vault.decrypt()
```

### Example 3: DI container

```python
from kstack_lib.any.container import KStackContainer

container = KStackContainer()
# Automatically wired based on context
secrets_provider = container.secrets_provider()
```

## Testing Strategy

1. **Unit tests**: Test each adapter separately
2. **Mock context**: Mock `is_in_cluster()` to test both paths
3. **Integration tests**: Should work unchanged (local context)
4. **Guard tests**: Verify import guards work

## Important Notes

⚠️ **Everything will break during migration** - This is intentional and expected

✅ **Old code still works** - Can run existing code until migration complete

🔥 **No backward compatibility** - Breaking changes are the goal

## Files Created This Session

New files (keep):

- `kstack_lib/any/__init__.py`
- `kstack_lib/any/exceptions.py`
- `kstack_lib/any/context.py`
- `kstack_lib/cluster/_guards.py`
- `kstack_lib/local/_guards.py`
- `docs/planning/cluster-local-any-refactor.md` (detailed plan)
- `pyproject.toml` (added dependency-injector)

## If You Need to Continue

**Start from Phase 2**: Create protocols and move types/utils

**Reference documents**:

- This checkpoint
- `docs/planning/cluster-local-any-refactor.md` (detailed plan)

**Test that foundation works**:

```python
from kstack_lib.any import is_in_cluster, KStackEnvironmentError
print(f"In cluster: {is_in_cluster()}")  # Should print False on dev machine

# This should raise error on dev machine:
try:
    from kstack_lib.cluster import _guards
except KStackEnvironmentError as e:
    print(f"Guard works: {e}")
```

---

**Status**: Foundation complete, ready for Phase 2
**Last updated**: 2025-01-10
**Next session**: Start Phase 2 - Protocols & Types
