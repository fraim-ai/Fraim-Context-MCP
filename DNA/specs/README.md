# Specifications (READ-ONLY)

> ⚠️ **DO NOT MODIFY** these files during development.

These documents define the architectural decisions for Fraim Context MCP v5.1. They are locked to ensure consistency throughout the build.

## Files

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | System design, data flow, component responsibilities |
| `CONTRACTS.md` | API schemas, database models, MCP tool definitions |
| `DEPENDENCIES.md` | Pinned versions with upgrade rationale |
| `MCP_STATUS.md` | MCP server availability and integration guide |

## Why Read-Only?

1. **Consistency**: Changing specs mid-build creates conflicting implementations
2. **TDD alignment**: Tests are written against these specs
3. **Traceability**: All decisions are documented before coding begins

## Found an Issue?

If you believe a specification is incorrect:

1. **DO NOT** modify the spec file
2. **DO** create `docs/SPEC_ISSUES.md` in the project
3. Document the issue with:
   - Which spec file
   - What section
   - What's wrong
   - Proposed fix

Example:

```markdown
# Specification Issues

## CONTRACTS.md - SearchRequest model

**Issue**: `top_k` max is 50 but MCP tool schema says 20
**Proposed**: Align both to 20 for consistency
```

After the build is complete, spec issues can be reviewed and incorporated into the next version.
