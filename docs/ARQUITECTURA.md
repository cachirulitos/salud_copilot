# ARQUITECTURA.md — SaludCopilot

## Module map — who owns what

| Module | Path | Responsibility | Owns |
|---|---|---|---|
| API | `apps/api/` | Business logic, DB access, orchestration | All database reads/writes |
| Bot | `apps/bot/` | Patient-facing WhatsApp communication | Conversation state in Redis |
| Dashboard | `apps/dashboard/` | Operational staff real-time interface | UI only — reads from API |
| CV Worker | `apps/cv/` | People counting via camera | Camera feed, count publishing |
| Rules Engine | `packages/rules_engine/` | Study sequencing logic | No external dependencies |
| ML | `ml/` | Wait time prediction model | Model training and inference |

**Hard rule:** only the API writes to PostgreSQL. No other module touches the database directly.

---

## Complete data flow — end to end

### Flow 1 — Patient arrives (walk-in)

```
Reception captures phone number
  → POST /api/v1/visits/check-in
  → API creates Patient (if new) + Visit in PostgreSQL
  → API calls rules_engine.calculate_sequence(studies)
  → Rules engine returns ordered StudySequence
  → API stores sequence steps in PostgreSQL
  → API publishes visit to Redis queue for the first area
  → API triggers bot: POST /bot/internal/notify {type: "welcome"}
  → Bot sends WhatsApp: name, ordered studies, total estimated time
```

### Flow 2 — Turn notification during wait

```
Staff marks patient as called (or system auto-advances)
  → POST /api/v1/visits/{visit_id}/advance-step
  → API updates current step in PostgreSQL
  → API triggers bot: POST /bot/internal/notify {type: "turn_ready"}
  → Bot sends WhatsApp: area name + estimated wait
  → Dashboard updates via WebSocket
```

### Flow 3 — CV worker updates occupancy

```
Camera captures frame every N seconds
  → YOLOv8 detects people in full frame
  → CV worker filters: only counts people whose center is inside
    configured ROI (Region of Interest) for that camera
    ROI defined in .env as CAMERA_ROI_0=x1,y1,x2,y2
    Eliminates counting people from adjacent areas sharing the same camera
  → POST /api/v1/areas/{area_id}/occupancy {count, timestamp}
  → API stores count in Redis: occupancy:{area_id} TTL 30s
  → API calls ML model with people_count as real-time feature:
    model.predict(hour_of_day, day_of_week, study_type,
                  clinic_id, capacity, people_count, has_appointment)
    people_count from CV = live signal that adjusts the historical baseline
  → API upserts WaitTimeEstimate in PostgreSQL
  → WebSocket broadcast to dashboard: wait_time_updated
  → If delta > 5 min vs previous estimate: trigger bot notification
```

### Flow 4 — Patient sends WhatsApp message

```
Patient sends message
  → Meta webhook POST to /bot/webhook
  → Bot identifies patient by phone number
  → Bot retrieves active visit from Redis: session:{phone_number}
  → Bot calls GET /api/v1/visits/{visit_id}/context
  → Bot sends context + message to Claude API
  → Claude responds (no medical interpretation — enforced in system prompt)
  → Bot sends response to patient
```

### Flow 5 — Results delivery

```
Results processed externally
  → POST /api/v1/visits/{visit_id}/results
  → API generates PostVisitRecommendation (generic only)
  → API triggers bot: POST /bot/internal/notify {type: "results_ready"}
  → Bot sends WhatsApp: results link + generic recommendation
```

---

## Contracts between modules

These signatures are fixed. Both sides implement exactly this.
No unilateral changes — write NEEDS APPROVAL if a change is required.

### API → Bot (internal notifications)

```
POST /bot/internal/notify
Authorization: Bearer {INTERNAL_BOT_TOKEN}

Request:
{
  "visit_id": "uuid",
  "notification_type": "welcome" | "turn_ready" | "turn_approaching"
                      | "results_ready" | "wait_time_updated",
  "payload": {}
}

welcome payload:
{
  "patient_name": "string",
  "sequence": [
    {
      "order": 1,
      "area_name": "string",
      "estimated_wait_minutes": int,
      "rule_applied": "R-01" | null
    }
  ],
  "total_estimated_minutes": int
}

turn_ready payload:
{
  "area_name": "string",
  "estimated_wait_minutes": int,
  "position_in_queue": int
}

results_ready payload:
{
  "study_name": "string",
  "result_url": "string",
  "recommendation": "string"
}

Response 200: {"status": "sent"}
Response 4xx: {"error": "description", "code": "ERROR_CODE"}
```

### Bot → API (check-in)

```
POST /api/v1/visits/check-in
Authorization: Bearer {INTERNAL_API_TOKEN}

Request:
{
  "phone_number": "string",   // E.164 format: +521234567890
  "clinic_id": "uuid",
  "study_ids": ["uuid"],
  "has_appointment": bool,
  "is_urgent": bool
}

Response 201:
{
  "visit_id": "uuid",
  "patient_id": "uuid",
  "sequence": [
    {
      "order": int,
      "area_name": "string",
      "estimated_wait_minutes": int,
      "rule_applied": "string" | null
    }
  ],
  "total_estimated_minutes": int
}
```

### Bot → API (visit context)

```
GET /api/v1/visits/{visit_id}/context
Authorization: Bearer {INTERNAL_API_TOKEN}

Response 200:
{
  "visit_id": "uuid",
  "patient_name": "string",
  "current_step": {
    "order": int,
    "area_name": "string",
    "status": "pending" | "in_progress" | "completed",
    "estimated_wait_minutes": int
  },
  "remaining_steps": [...],
  "total_estimated_minutes": int
}

Response 404: {"error": "Visit not found", "code": "VISIT_NOT_FOUND"}
```

### CV Worker → API (occupancy)

```
POST /api/v1/areas/{area_id}/occupancy
Authorization: Bearer {INTERNAL_CV_TOKEN}

Request:
{
  "people_count": int,
  "timestamp": "ISO8601 string"
}

Response 200: {"wait_time_estimate_minutes": int}
Response 404: {"error": "Area not found", "code": "AREA_NOT_FOUND"}
```

### Dashboard → API (real-time feed)

```
WebSocket: ws://api:8000/ws/dashboard/{clinic_id}
Authorization: Bearer {DASHBOARD_TOKEN}

Server pushes on change:
{
  "event": "visit_updated" | "queue_changed" | "wait_time_updated" | "alert",
  "area_id": "uuid",
  "data": {}
}
```

---

## Database schema — reference overview

Full DDL lives in `apps/api/migrations/`. This is the working reference.

### patients
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| phone_number | VARCHAR UNIQUE | E.164 format |
| full_name | VARCHAR | |
| created_at | TIMESTAMPTZ | |

### clinics
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR | |
| address | TEXT | |
| latitude | NUMERIC(10,7) | |
| longitude | NUMERIC(10,7) | |
| active | BOOLEAN | |

### clinical_areas
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| clinic_id | UUID FK → clinics | |
| name | VARCHAR | "laboratorio", "ultrasonido", etc. |
| study_type | VARCHAR | matches rules engine type identifiers |
| simultaneous_capacity | INTEGER | from Excel: CantidadConsultorios |
| active | BOOLEAN | |

### visits
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| patient_id | UUID FK → patients | |
| clinic_id | UUID FK → clinics | |
| status | ENUM | pending, in_progress, completed, cancelled |
| has_appointment | BOOLEAN | drives proactive vs reactive bot mode |
| is_urgent | BOOLEAN | |
| created_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | nullable |

### visit_steps
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| visit_id | UUID FK → visits | |
| clinical_area_id | UUID FK → clinical_areas | |
| step_order | INTEGER | calculated by rules engine |
| status | ENUM | pending, in_progress, completed |
| rule_applied | VARCHAR | R-01... or null |
| estimated_wait_minutes | INTEGER | updated by ML model |
| actual_wait_minutes | INTEGER | nullable, filled on completion |
| started_at | TIMESTAMPTZ | nullable |
| completed_at | TIMESTAMPTZ | nullable |

### notifications
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| visit_id | UUID FK → visits | |
| notification_type | ENUM | welcome, turn_ready, etc. |
| content | TEXT | actual message sent |
| status | ENUM | sent, delivered, failed |
| sent_at | TIMESTAMPTZ | |

### clinical_rules
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| code | VARCHAR UNIQUE | R-01, R-02... |
| description | TEXT | |
| rule_type | ENUM | order, priority, restriction |
| condition | JSONB | what triggers this rule |
| effect | JSONB | what the rule enforces |
| active | BOOLEAN | |

### wait_time_estimates
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| clinical_area_id | UUID FK → clinical_areas | |
| estimated_minutes | INTEGER | current ML prediction |
| people_in_area | INTEGER | latest CV count |
| updated_at | TIMESTAMPTZ | |

### patient_events (append-only)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| visit_id | UUID FK → visits | |
| event_type | VARCHAR | arrival, step_started, step_completed, etc. |
| metadata | JSONB | event-specific context |
| occurred_at | TIMESTAMPTZ | never updated after insert |

### Redis keys (not PostgreSQL)

```
session:{phone_number}          → active visit context, TTL 4h
queue:{clinical_area_id}        → sorted set of visit_ids waiting
active_turn:{clinical_area_id}  → current visit_id being attended
occupancy:{clinical_area_id}    → latest CV people count, TTL 30s
```

---

## ML model — inputs and target

**Target:** `waiting_time_minutes`
Source: Excel → Promedios de Espera → Promedio column

**Features:**

| Feature | Source | Notes |
|---|---|---|
| hour_of_day | FechaServicio (has time) | Strongest predictor |
| day_of_week | FechaServicio | 0=Monday, 6=Sunday |
| study_type_id | idEstudio | Label encoded |
| clinic_id | idSucursal | Label encoded |
| simultaneous_capacity | Excel: CantidadConsultorios | Area capacity |
| current_queue_length | CV worker via Redis at inference time | People counted inside area ROI right now. Adjusts historical baseline to present reality. CV and check-in are independent — CV counts anonymous people, check-in knows who they are. |
| has_appointment | idReservacion not null | Appointment vs walk-in |

## CV and check-in independence

CV worker and check-in system are deliberately independent.

CV: counts how many anonymous people are in each area ROI.
    Does not know who they are or what studies they have.

Check-in: knows exactly which patient has which studies in which order.
          Does not use camera data.

They connect only through the ML model at inference time:
CV provides people_count → model uses it as one feature among several.

This design avoids biometric data concerns (no individual tracking),
works with existing cameras (no new hardware),
and degrades gracefully if CV fails (model falls back to historical baseline).

**Served via:** `GET /api/v1/areas/{area_id}/wait-time-estimate`

---

## Key design decisions with rationale

**Rules engine isolated as package**
Wrong sequencing causes invalid studies that must be repeated — active patient
harm. The module must be testable with zero external dependencies.

**Append-only patient_events**
Every state change is an immutable record. Full auditability: if something goes
wrong, we can reconstruct exactly what the system decided and why.

**Redis for queue state**
Queue position changes on every patient movement. PostgreSQL is for durable
relational data, not high-frequency state. Redis handles it natively and the
data only matters right now.

**Two bot modes**
Proactive (appointment): patient planned ahead, deserves preparation info early.
Reactive (walk-in): patient is already there — unsolicited messages are noise.
Mode is set at check-in from `has_appointment`, stored in Redis session.

**No medical interpretation**
Enforced in Claude API system prompt and as a validation layer before any
recommendation is sent. The system checks for diagnostic language and blocks it.
