# plan.md — Technical Implementation Plan Template

<!--
USAGE: Derived from spec.md by Architect (Opus 4.5)
PURPOSE: Bridge between WHAT (spec) and HOW (tasks)
RULE: No implementation code, only signatures and structure
-->

# Implementation Plan: [Feature Name]

## Metadata
| Field | Value |
|-------|-------|
| Spec | [Link to spec.md] |
| Author | Architect (Opus 4.5) |
| Created | YYYY-MM-DD |
| Estimated Effort | [X days/hours] |

---

## 1. Overview

### Approach
<!-- 1-2 paragraphs describing the technical approach -->

[DESCRIPTION]

### Key Decisions
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| [Decision 1] | [Why] | [What else was considered] |

---

## 2. Architecture

### Component Diagram
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│    API      │────▶│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  External   │
                    │  Service    │
                    └─────────────┘
```

### Data Flow
```
1. User submits form
2. Frontend validates input
3. API receives request
4. Business logic processes
5. Database updated
6. Response returned
```

---

## 3. File Changes

### New Files
| Path | Purpose | Complexity |
|------|---------|------------|
| `src/modules/feature/index.ts` | Module entry | Low |
| `src/modules/feature/service.ts` | Business logic | Medium |
| `src/modules/feature/types.ts` | Type definitions | Low |
| `tests/feature/service.test.ts` | Unit tests | Medium |

### Modified Files
| Path | Changes | Risk |
|------|---------|------|
| `src/routes/index.ts` | Add new routes | Low |
| `src/database/schema.ts` | Add new table | Medium |

### Deleted Files
| Path | Reason |
|------|--------|
| [None] | — |

---

## 4. Interface Definitions

### Types
```typescript
// src/modules/feature/types.ts

interface CreateFeatureInput {
  name: string;
  config: FeatureConfig;
}

interface FeatureConfig {
  enabled: boolean;
  threshold: number;
}

interface Feature {
  id: string;
  name: string;
  config: FeatureConfig;
  createdAt: Date;
  updatedAt: Date;
}

type FeatureResult = 
  | { success: true; data: Feature }
  | { success: false; error: FeatureError };

enum FeatureError {
  INVALID_INPUT = 'INVALID_INPUT',
  NOT_FOUND = 'NOT_FOUND',
  DUPLICATE = 'DUPLICATE',
}
```

### Function Signatures
```typescript
// src/modules/feature/service.ts

/**
 * Creates a new feature.
 * @throws ValidationError if input invalid
 * @throws DuplicateError if name exists
 */
function createFeature(input: CreateFeatureInput): Promise<FeatureResult>;

/**
 * Retrieves feature by ID.
 * @returns null if not found
 */
function getFeature(id: string): Promise<Feature | null>;

/**
 * Updates feature configuration.
 * @throws NotFoundError if feature doesn't exist
 */
function updateFeature(id: string, config: Partial<FeatureConfig>): Promise<FeatureResult>;

/**
 * Deletes feature.
 * @returns true if deleted, false if not found
 */
function deleteFeature(id: string): Promise<boolean>;
```

### API Endpoints
```typescript
// src/routes/feature.ts

// POST /api/v1/features
// Request: CreateFeatureInput
// Response: Feature | ErrorResponse

// GET /api/v1/features/:id
// Response: Feature | 404

// PATCH /api/v1/features/:id
// Request: Partial<FeatureConfig>
// Response: Feature | ErrorResponse

// DELETE /api/v1/features/:id
// Response: 204 | 404
```

---

## 5. Database Changes

### Schema
```sql
-- migrations/YYYYMMDD_create_features.sql

CREATE TABLE features (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL UNIQUE,
  config JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_features_name ON features(name);
```

### Migration Strategy
1. Create table (backwards compatible)
2. Deploy code (reads/writes new table)
3. Backfill data (if needed)
4. Remove old code paths (if any)

### Rollback
```sql
-- rollback/YYYYMMDD_create_features.sql
DROP TABLE IF EXISTS features;
```

---

## 6. External Dependencies

### New Dependencies
| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| [none] | — | — | — |

### External Services
| Service | Usage | Fallback |
|---------|-------|----------|
| [none] | — | — |

---

## 7. Error Handling

### Error Types
| Error | HTTP Code | When | User Message |
|-------|-----------|------|--------------|
| ValidationError | 400 | Invalid input | "Please check your input" |
| NotFoundError | 404 | Resource missing | "Feature not found" |
| DuplicateError | 409 | Name exists | "Feature name already exists" |
| InternalError | 500 | Unexpected | "Something went wrong" |

### Error Flow
```
1. Catch at service layer
2. Log with context
3. Transform to API error
4. Return consistent format
```

---

## 8. Testing Plan

### Unit Tests
| Test File | Coverage Area | Priority |
|-----------|---------------|----------|
| `service.test.ts` | Business logic | P0 |
| `validation.test.ts` | Input validation | P0 |

### Integration Tests
| Test | What It Covers |
|------|----------------|
| Create flow | API → Service → DB |
| Update flow | API → Service → DB |
| Error handling | Various failure modes |

### Test Data
```typescript
const testFeature: CreateFeatureInput = {
  name: 'test-feature',
  config: { enabled: true, threshold: 10 }
};
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Day 1)
- [ ] Create type definitions
- [ ] Create database migration
- [ ] Set up module structure

### Phase 2: Core Logic (Day 2)
- [ ] Implement service functions
- [ ] Write unit tests
- [ ] Add validation

### Phase 3: API Layer (Day 3)
- [ ] Implement endpoints
- [ ] Add authentication/authorization
- [ ] Integration tests

### Phase 4: Polish (Day 4)
- [ ] Error handling review
- [ ] Logging
- [ ] Documentation

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema migration issues | Low | High | Test on staging first |
| Performance with large datasets | Medium | Medium | Add pagination |

---

## 11. Checklist Before Implementation

- [ ] Spec approved
- [ ] Plan reviewed
- [ ] Dependencies available
- [ ] Test environment ready
- [ ] Feature flag created (if needed)

---

## 12. Notes for Builder

### Patterns to Follow
- Use existing error handling in `src/utils/errors.ts`
- Follow validation pattern in `src/utils/validation.ts`
- Use repository pattern for DB access

### Gotchas
- Remember to update `src/routes/index.ts` to register new routes
- Feature config is JSONB — validate before storing

### References
- Similar implementation: `src/modules/users/`
- Validation example: `src/modules/auth/validation.ts`
