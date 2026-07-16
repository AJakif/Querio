# spec.md — Feature Specification Template

<!--
USAGE: Copy this template for each new feature.
MODEL: Use Opus 4.5 to fill this out.
RULE: Complete this BEFORE any implementation.
-->

# Specification: [Feature Name]

## Metadata
| Field | Value |
|-------|-------|
| Status | 🟡 Draft / 🟢 Approved / 🔵 In Progress / ✅ Complete |
| Owner | [Name] |
| Created | YYYY-MM-DD |
| Updated | YYYY-MM-DD |
| Related | [Links to tickets, docs, etc.] |

---

## 1. Executive Summary

<!-- 2-3 sentences max. What and why. -->

[DESCRIPTION]

---

## 2. Problem Statement

### Current State
<!-- What exists today? What's the pain? -->

[DESCRIPTION]

### Desired State
<!-- What should exist? What's the benefit? -->

[DESCRIPTION]

### Success Metrics
<!-- How do we know this worked? -->

- [ ] Metric 1: [TARGET]
- [ ] Metric 2: [TARGET]

---

## 3. User Stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-1 | [Role] | [Action] | [Benefit] |
| US-2 | [Role] | [Action] | [Benefit] |

---

## 4. Acceptance Criteria

### US-1: [Title]
```gherkin
GIVEN [precondition]
WHEN [action]
THEN [expected result]
AND [additional result]
```

### US-2: [Title]
```gherkin
GIVEN [precondition]
WHEN [action]
THEN [expected result]
```

---

## 5. Functional Requirements

### 5.1 [Requirement Area]

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-1 | [Description] | Must/Should/Could | [Notes] |
| FR-2 | [Description] | Must/Should/Could | [Notes] |

---

## 6. Non-Functional Requirements

### Performance
- Response time: [TARGET]
- Throughput: [TARGET]
- Concurrent users: [TARGET]

### Security
- Authentication: [REQUIRED/NOT REQUIRED]
- Authorization: [RULES]
- Data sensitivity: [LEVEL]

### Availability
- Uptime target: [PERCENTAGE]
- Degradation strategy: [DESCRIPTION]

---

## 7. Data Model

### New Entities
```
[Entity Name]
├── id: UUID (PK)
├── field_1: string (required)
├── field_2: int (optional)
├── created_at: timestamp
└── updated_at: timestamp
```

### Schema Changes
```sql
-- Migration description
ALTER TABLE [table] ADD COLUMN [column] [type];
```

### Data Flow
```
[Source] → [Process] → [Destination]
```

---

## 8. API Contract

### Endpoints

#### `POST /api/v1/[resource]`

**Request**
```json
{
  "field": "string"
}
```

**Response (200)**
```json
{
  "id": "uuid",
  "field": "string",
  "created_at": "ISO8601"
}
```

**Errors**
| Code | Condition | Response |
|------|-----------|----------|
| 400 | Invalid input | `{"error": "validation_error", "details": [...]}` |
| 401 | Unauthorized | `{"error": "unauthorized"}` |
| 404 | Not found | `{"error": "not_found"}` |

---

## 9. UI/UX Requirements

<!-- If applicable -->

### Wireframes
[Link or description]

### User Flow
```
[Screen 1] → [Action] → [Screen 2] → [Action] → [Result]
```

### Accessibility
- [ ] Keyboard navigation
- [ ] Screen reader support
- [ ] Color contrast compliance

---

## 10. Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| [Edge case 1] | [How to handle] |
| [Edge case 2] | [How to handle] |
| [Error condition] | [Recovery/message] |

---

## 11. Security Considerations

### Threat Model
| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| [Threat 1] | H/M/L | H/M/L | [Control] |

### Security Requirements
- [ ] Input validation on all endpoints
- [ ] Rate limiting: [LIMIT]
- [ ] Audit logging for: [OPERATIONS]

---

## 12. Testing Strategy

### Unit Tests
- [ ] [Test area 1]
- [ ] [Test area 2]

### Integration Tests
- [ ] [Test scenario 1]
- [ ] [Test scenario 2]

### E2E Tests
- [ ] [User flow 1]
- [ ] [User flow 2]

---

## 13. Rollout Plan

### Feature Flags
- Flag name: `[FLAG_NAME]`
- Default: OFF
- Rollout: [PERCENTAGE OR CRITERIA]

### Rollback Procedure
1. [Step 1]
2. [Step 2]

---

## 14. Dependencies

### External
- [ ] [Service/API]: [What we need from it]

### Internal
- [ ] [Team/Module]: [What we need from them]

### Blockers
- [ ] [Blocker 1]: [Status]

---

## 15. Open Questions

<!-- Remove when resolved -->

| Question | Owner | Status |
|----------|-------|--------|
| [Question 1] | [Name] | 🔴 Open / 🟢 Resolved |

---

## 16. Assumptions

<!-- Document assumptions that, if wrong, invalidate the spec -->

> ⚠️ ASSUMPTION: [Assumption 1]

> ⚠️ ASSUMPTION: [Assumption 2]

---

## Appendix

### Glossary
| Term | Definition |
|------|------------|
| [Term] | [Definition] |

### References
- [Link 1]
- [Link 2]
