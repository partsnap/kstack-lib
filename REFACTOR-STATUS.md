# 🔥 MAJOR REFACTOR IN PROGRESS 🔥

**Active Work**: Cluster/Local/Any Architecture Separation

## Quick Status

**Phase 1: Foundation** ✅ COMPLETE (2025-01-10)

Created:

- `kstack_lib/any/` - Context-agnostic code
- `kstack_lib/cluster/` - Kubernetes-only code
- `kstack_lib/local/` - Dev machine-only code
- Import guards that enforce context separation
- New exception naming (all `KStack*Error`)

**Phase 2-5**: NOT STARTED

## ⚠️ Important

- **Old code still works** - No breaking changes yet
- **New structure exists** - But not wired up
- **Tests may fail** - Expected during refactor
- **DO NOT DELETE old files yet** - Migration incomplete

## For Developers

**Current checkpoint**: `CHECKPOINT-2025-01-10.md`

**Detailed plan**: `docs/planning/cluster-local-any-refactor.md`

**Planning overview**: `docs/planning/README.md`

**Next step**: Phase 2 - Create protocols and move types

## Quick Test

```python
# This should work on dev machine:
from kstack_lib.any import is_in_cluster
print(f"In cluster: {is_in_cluster()}")  # False

# This should raise KStackEnvironmentError on dev machine:
from kstack_lib.cluster import _guards  # ERROR!
```

---

**Last Updated**: 2025-01-10
**Contact**: See planning docs for details
