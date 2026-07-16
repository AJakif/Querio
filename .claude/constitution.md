# constitution.md — Project Immutable Rules

<!--
PURPOSE: Define rules that NEVER change without explicit human approval.
SCOPE: All agents (Architect, Builder, Critic) must obey these rules.
OVERRIDE: Only human can modify this file.
-->

# Constitution: [Project Name]

> These rules are IMMUTABLE. Agents must follow them regardless of task instructions.
> Violation of these rules requires human review before proceeding.

---

## 1. Absolute Prohibitions

### Never Do These (No Exceptions)

```
❌ NEVER commit secrets, API keys, or credentials to the repository
❌ NEVER delete or modify production data without explicit approval
❌ NEVER bypass authentication or authorization checks
❌ NEVER disable security features, even for testing
❌ NEVER execute arbitrary user input (eval, exec, etc.)
❌ NEVER log sensitive user data (passwords, tokens, PII)
❌ NEVER modify these files without human review:
   - constitution.md
   - .github/workflows/*
   - scripts/deploy-*
   - database/migrations/* (existing)
   - config/production.*
```

---

## 2. Architectural Invariants

### These Patterns Must Be Maintained

```
✅ All external I/O must go through defined service boundaries
✅ All database access must use the repository pattern
✅ All API endpoints must have authentication (except explicitly public ones)
✅ All user input must be validated at service boundary
✅ All errors must be logged with correlation IDs
✅ All async operations must have timeout handling
```

### These Patterns Are Forbidden

```
❌ No direct database queries outside repositories
❌ No HTTP calls without timeout configuration
❌ No synchronous file I/O in request handlers
❌ No global mutable state
❌ No circular dependencies between modules
```

---

## 3. Code Quality Gates

### All Code Must Pass

```
✅ Type checking (strict mode)
✅ Linting (no warnings)
✅ Unit tests for all business logic
✅ Integration tests for all API endpoints
✅ No decrease in test coverage
```

### Review Required For

```
⚠️ Changes to public API contracts
⚠️ Database schema modifications
⚠️ New external dependencies
⚠️ Security-sensitive code (auth, crypto, PII)
⚠️ Performance-critical paths
```

---

## 4. Dependency Rules

### Allowed
```
✅ Dependencies from approved list (see CLAUDE.md)
✅ Dev dependencies for testing/tooling
✅ Peer dependencies of approved packages
```

### Requires Approval
```
⚠️ Any new runtime dependency
⚠️ Dependencies with native bindings
⚠️ Dependencies with GPL/AGPL licenses
```

### Forbidden
```
❌ Dependencies with known vulnerabilities
❌ Abandoned packages (no updates in 2+ years)
❌ Packages with <1000 weekly downloads (except internal)
```

---

## 5. Data Handling Rules

### Sensitive Data
```
✅ Must be encrypted at rest
✅ Must be encrypted in transit
✅ Must have access logging
✅ Must have retention policy
```

### User Data
```
✅ Collect minimum necessary
✅ Provide deletion mechanism
✅ Document in privacy policy
❌ Never share with third parties without consent
```

### Logging
```
✅ Log: Request IDs, timestamps, user IDs (hashed), error codes
❌ Never log: Passwords, tokens, full credit card numbers, SSNs
```

---

## 6. Deployment Rules

### Pre-Deployment
```
✅ All tests passing
✅ No critical/high security vulnerabilities
✅ Database migrations tested on staging
✅ Rollback procedure documented
```

### Deployment
```
✅ Blue-green or canary deployment
✅ Health checks enabled
✅ Monitoring dashboards updated
```

### Post-Deployment
```
✅ Verify health checks passing
✅ Monitor error rates for 15 minutes
✅ Rollback if error rate > 1%
```

---

## 7. Error Handling Rules

### All Errors Must
```
✅ Be caught at appropriate boundary
✅ Be logged with stack trace (internal)
✅ Return safe message to user (no internals)
✅ Include correlation ID for debugging
```

### Never
```
❌ Swallow errors silently
❌ Expose stack traces to users
❌ Expose internal paths or configs
❌ Retry indefinitely without backoff
```

---

## 8. Testing Rules

### Coverage Requirements
```
✅ Unit tests: >80% line coverage
✅ Critical paths: 100% branch coverage
✅ API endpoints: Integration test required
✅ User flows: E2E test for happy path
```

### Test Data
```
✅ Use factories/fixtures, not production data
✅ Clean up after tests (no orphan data)
❌ Never use real user data in tests
❌ Never hardcode credentials in tests
```

---

## 9. Documentation Rules

### Required Documentation
```
✅ README with setup instructions
✅ API documentation (OpenAPI/Swagger)
✅ Architecture decision records (ADRs)
✅ Runbooks for common operations
```

### Code Documentation
```
✅ Public APIs must have docstrings
✅ Complex logic must have inline comments
✅ Non-obvious decisions must reference ADR
```

---

## 10. Agent-Specific Rules

### Architect (Opus)
```
✅ Must produce spec.md before plan.md
✅ Must check constitution.md before proposing changes
✅ Must flag assumptions explicitly
❌ Must not write implementation code
```

### Builder (Sonnet/Haiku)
```
✅ Must follow TDD (test first)
✅ Must follow plan.md structure
✅ Must flag deviations from plan
❌ Must not modify constitution.md
❌ Must not skip tests for "simple" changes
```

### Critic (Gemini/Claude)
```
✅ Must check against constitution.md
✅ Must verify spec compliance
✅ Must flag security issues as blocking
❌ Must not approve code that violates constitution
```

---

## 11. Escalation Rules

### Escalate to Human When
```
⚠️ Constitution violation detected
⚠️ Security vulnerability found
⚠️ Ambiguous requirement interpretation
⚠️ Multiple valid architectural approaches
⚠️ Breaking change to public API
⚠️ Data migration affecting production
⚠️ Uncertainty about business logic
```

### Do Not Proceed Without Human Approval
```
🛑 Deleting user data
🛑 Modifying authentication flow
🛑 Changing encryption implementation
🛑 Modifying payment processing
🛑 Changing data retention policies
```

---

## 12. Version Control Rules

### Commits
```
✅ Conventional commit format (type(scope): message)
✅ Atomic commits (one logical change)
✅ Descriptive messages (what and why)
❌ Never commit directly to main/master
❌ Never force push to shared branches
```

### Branches
```
✅ Feature branches from main
✅ Delete after merge
✅ Keep up to date with main
```

### Pull Requests
```
✅ Must have description
✅ Must pass CI checks
✅ Must have at least one review
✅ Must be squash merged (clean history)
```

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| YYYY-MM-DD | Initial version | [Name] |

---

> **Remember**: These rules exist to protect the project, the team, and the users.
> When in doubt, ask a human.
