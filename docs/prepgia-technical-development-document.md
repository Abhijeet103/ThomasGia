# PrepGIA Technical Development Document

## 1. Purpose

This document translates the product requirements into a buildable technical plan for a web-based Thomas GIA practice platform with:

- 5 timed GIA sections
- Full mock exams
- Google login with OAuth
- Subscription paywall
- Auto-generated questions
- Attempt history and analytics

The goal is to choose a stack that is fast to build, stable in production, and easy to extend globally.

## 2. Recommended Stack

### Frontend

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Tailwind CSS

### Backend

- Django
- Django REST Framework
- Celery
- Redis

### Database and Platform

- Supabase Postgres
- Supabase Storage for optional static assets and exports

### Authentication

- Supabase Auth with Google OAuth

### Payments

- Stripe for subscriptions
- Optional phase-2 Razorpay support for India

### Infrastructure

- Frontend on Vercel
- Django API on Railway, Render, Fly.io, or AWS
- Redis via Upstash or managed Redis
- Background jobs for webhooks, analytics updates, and generator imports

## 3. Architecture Decision

### Recommended architecture

Use `React + Django API + Supabase Postgres + Supabase Auth + Stripe`.

This gives:

- Django as the rules engine for question generation, scoring, and paywall enforcement
- React as a fast SPA for timed test UX
- Postgres for relational data, reports, and analytics
- Supabase for managed Postgres and easy Google OAuth
- Stripe for reliable recurring billing globally

### Why not Better Auth as the main auth layer

Better Auth is strongest in JavaScript-first backend stacks. Since the core business logic is in Django, adding Better Auth introduces another auth authority and extra token-sync complexity. For this project, Supabase Auth or Django Allauth is a cleaner fit.

### Auth recommendation

Use Supabase Auth as the identity provider and let Django trust verified JWTs from Supabase.

Benefits:

- Fast Google OAuth setup
- Good free tier
- Easy user session handling in React
- Clean separation between identity and app logic

## 4. Database Choice: MongoDB vs Postgres

### Recommendation

Choose `Postgres on Supabase`.

### Why Postgres fits better

The platform is not just storing questions. It needs:

- users
- subscriptions
- attempts
- sections
- answers
- score breakdowns
- question exposure tracking
- analytics
- webhook event logs

These are relational, query-heavy, and reporting-heavy workflows. Postgres is a better default for this shape of product.

### Postgres pros

- Strong relational modeling for attempts, answers, subscriptions, and analytics
- ACID transactions for billing and entitlement updates
- Strong filtering and aggregation for score history and percentiles
- Easier admin reporting
- JSONB support for flexible question payloads
- Supabase gives hosted Postgres, auth integrations, dashboard, backups, and a generous free tier

### Postgres cons

- More schema discipline required up front
- Slightly more work if you want fully schema-less content iteration

### MongoDB pros

- Flexible document model for question payloads
- Fast iteration for loosely structured content
- Natural fit for nested generator payloads

### MongoDB cons

- Harder reporting joins across users, attempts, billing, and entitlements
- Weaker fit for payment state consistency
- More application-side logic for analytics and relational constraints
- No native Supabase path if Supabase is preferred

### Final decision

Use Postgres, and store dynamic question payloads in `JSONB` where flexibility is needed.

This gets the best of both worlds:

- relational integrity for platform data
- flexible storage for generated question content

## 5. System Overview

### High-level flow

1. User logs in with Google via Supabase Auth.
2. React stores the session and sends the Supabase access token to Django.
3. Django verifies the token and creates or syncs the local user record.
4. User starts a section or mock exam.
5. Django creates an attempt session and generates seeded questions server-side.
6. React fetches one question at a time and submits answers.
7. Django scores answers in real time or at section end.
8. Paywall checks are enforced before starting premium flows.
9. Stripe webhooks update subscription state asynchronously.
10. Dashboard reads attempt history, progress, and weak-section analytics from Django.

## 6. Core Services

### 6.1 Auth service

Responsibilities:

- Google OAuth login
- session validation
- JWT verification in Django
- local user profile sync

Recommended approach:

- Supabase handles OAuth
- Django middleware validates Supabase JWT
- Django stores local `User`, `UserProfile`, and entitlement records

### 6.2 Subscription service

Responsibilities:

- plan catalog
- checkout session creation
- webhook handling
- entitlement updates
- billing history

Recommended approach:

- Stripe Checkout for purchase
- Stripe Billing Portal for cancel and plan management
- Django persists canonical subscription state after webhook confirmation

### 6.3 Assessment engine

Responsibilities:

- section orchestration
- timers
- seeded question generation
- answer scoring
- result compilation

Core design rule:

Question answers must never be shipped to the client before submission.

### 6.4 Generator import service

Responsibilities:

- load word bank data
- validate structured generator inputs
- bulk import seed data into Postgres
- version content packs

### 6.5 Analytics service

Responsibilities:

- attempt summaries
- trend lines
- section weakness detection
- estimated percentile banding

## 7. Suggested Domain Model

### Main tables

- `users`
- `user_profiles`
- `subscriptions`
- `payment_customers`
- `payment_events`
- `plans`
- `attempts`
- `attempt_sections`
- `attempt_answers`
- `question_exposure`
- `word_meaning_items`
- `generator_configs`
- `percentile_bands`

### Key entities

#### users

- `id`
- `email`
- `full_name`
- `auth_provider_user_id`
- `created_at`

#### subscriptions

- `id`
- `user_id`
- `provider`
- `provider_customer_id`
- `provider_subscription_id`
- `plan_code`
- `status`
- `current_period_start`
- `current_period_end`
- `cancel_at_period_end`

#### attempts

- `id`
- `user_id`
- `mode` (`section`, `full_mock`, `diagnostic`)
- `status` (`not_started`, `in_progress`, `completed`, `expired`)
- `started_at`
- `completed_at`
- `overall_adjusted_score`
- `overall_percentile_band`

#### attempt_sections

- `id`
- `attempt_id`
- `section_type`
- `seed`
- `difficulty_profile`
- `time_limit_seconds`
- `started_at`
- `ended_at`
- `adjusted_score`
- `percentile_band`

#### attempt_answers

- `id`
- `attempt_section_id`
- `question_index`
- `question_type`
- `question_payload_json`
- `user_answer_json`
- `correct_answer_hash`
- `is_correct`
- `penalty_applied`
- `response_time_ms`

#### word_meaning_items

- `id`
- `pair_word_1`
- `pair_word_2`
- `relationship_type`
- `odd_word`
- `difficulty`
- `tags_json`
- `is_active`

### Why store `question_payload_json`

It preserves exactly what the user saw, supports debugging, and allows result review without storing hardcoded content banks for every generated question.

## 8. API Design

### Auth

- `POST /api/auth/sync`
- `GET /api/me`

### Plans and billing

- `GET /api/plans`
- `POST /api/billing/create-checkout-session`
- `POST /api/billing/webhooks/stripe`
- `GET /api/billing/subscription`

### Assessment

- `POST /api/attempts/start`
- `GET /api/attempts/{id}`
- `POST /api/attempts/{id}/sections/{sectionId}/next-question`
- `POST /api/attempts/{id}/sections/{sectionId}/submit-answer`
- `POST /api/attempts/{id}/complete`

### Results and dashboard

- `GET /api/results/history`
- `GET /api/results/{attemptId}`
- `GET /api/dashboard/summary`

### Admin and content

- `POST /api/admin/import/word-meaning`
- `GET /api/admin/generator-health`

## 9. Frontend Application Structure

### Public pages

- Landing page
- Pricing page
- Login page

### Authenticated pages

- Dashboard
- Section selection
- Full mock flow
- Results page
- Account and billing

### Important UX rules

- Timer must be highly visible and smooth
- Section transitions must match the real exam rhythm
- Full screen mode should be encouraged
- Question rendering must be lightweight and fast
- Answer submission must tolerate intermittent network issues

### Suggested frontend folders

- `src/pages`
- `src/features/auth`
- `src/features/assessment`
- `src/features/billing`
- `src/features/results`
- `src/lib/api`
- `src/lib/supabase`

## 10. Django Application Structure

Suggested apps:

- `accounts`
- `billing`
- `assessments`
- `generators`
- `analytics`
- `core`

### Responsibility split

- `accounts`: user sync, auth guards, profiles
- `billing`: Stripe integration, entitlements, plans, webhook processing
- `assessments`: attempts, sections, answers, result endpoints
- `generators`: procedural generator implementations and validation
- `analytics`: percentile bands, summaries, trend calculations
- `core`: shared utilities, settings, health checks

## 11. Question Generator Design

### Shared interface

Each section generator should implement:

```python
class BaseQuestionGenerator:
    section_type: str

    def generate(self, difficulty: str, seed: str) -> dict:
        ...

    def evaluate(self, question_payload: dict, user_answer: dict) -> dict:
        ...
```

### Design rules

- Generators must be deterministic by seed
- Generation must be pure and testable
- Evaluation must happen on the server
- Output format must be normalized across all sections

### Output contract

```json
{
  "question_id": "uuid-or-seeded-key",
  "section_type": "reasoning",
  "prompt": {},
  "options": [],
  "metadata": {
    "difficulty": "medium"
  }
}
```

### Section-specific implementation

#### Reasoning

- Generate relation graphs
- Validate acyclic ordering
- Derive correct answer from resolved graph

#### Perceptual Speed

- Generate letter-pair rows procedurally
- Count exact same-letter case pairs

#### Number Speed and Accuracy

- Generate three integers
- reject equal-distance cases
- compute furthest-from-middle answer

#### Word Meaning

- Use a curated seed bank
- Support controlled odd-word remixing
- Track exposure to reduce repeats

#### Spatial Visualization

- Generate SVG polygon shapes
- Apply rotation or mirror transforms
- Return SVG payload for client rendering

## 12. Question Generation Script

The platform needs a script to seed all non-procedural data and config into the database.

### What should be imported

- Word Meaning bank
- section penalty configuration
- difficulty configuration
- percentile band configuration
- plan catalog

### Recommended format

Use versioned JSON or CSV files committed in the repo:

- `seed/word_meaning_bank.json`
- `seed/penalty_config.json`
- `seed/percentile_bands.json`
- `seed/plans.json`

### Recommended command

```bash
python manage.py import_seed_data --source seed/
```

### Import rules

- idempotent
- validates schema before write
- supports dry-run mode
- logs row counts and failures
- content version tracked in a table

## 13. Paywall and Entitlement Logic

### Free tier

- 1 lifetime diagnostic
- daily capped practice by section

### Paid tier

- unlimited section practice
- unlimited full mocks
- full history and analytics

### Enforcement point

Enforce paywall in Django before attempt creation, not only in the frontend.

### Recommended checks

- active subscription status
- diagnostic already used
- daily question cap per section

## 14. Security and Anti-Abuse

### Required controls

- server-side scoring only
- signed auth tokens only
- webhook signature verification
- rate limiting on auth and billing endpoints
- audit logs for subscription changes
- attempt expiration and replay protection

### Nice-to-have later

- basic device fingerprinting
- suspicious pattern detection
- answer-speed anomaly flags

## 15. Performance Considerations

### Backend

- cache config and percentile bands in Redis
- queue Stripe webhook processing with Celery
- keep generators CPU-light and deterministic

### Frontend

- prefetch next question shell without answer data
- minimize re-renders during timed sessions
- handle reconnect/resume for unstable networks

## 16. Testing Strategy

### Unit tests

- generator determinism
- generator correctness
- scoring rules
- entitlement rules
- webhook processing

### Integration tests

- Google login flow
- start attempt to finish
- payment success to entitlement activation
- free-tier cap enforcement

### End-to-end tests

- sign in
- buy plan
- take mock
- view results

## 17. Delivery Plan

### Phase 1: Foundation

- set up Django, DRF, React, Supabase project, Stripe project
- implement auth sync
- define schema and migrations

### Phase 2: Assessment engine

- build attempts and sections
- implement all 5 generators
- implement scoring engine
- render timed test UI

### Phase 3: Results and dashboard

- attempt history
- weak-section analytics
- percentile band display

### Phase 4: Billing and paywall

- Stripe checkout
- Stripe webhooks
- entitlement enforcement
- pricing and upgrade flows

### Phase 5: Seed data and launch prep

- import word bank and configs
- admin tooling
- QA, observability, and launch polish

## 18. Recommended v1 Decisions

Use these unless a business constraint changes:

- Backend: Django + DRF
- Frontend: React + TypeScript
- Auth: Supabase Auth with Google OAuth
- Database: Supabase Postgres
- Cache and jobs: Redis + Celery
- Payments: Stripe first, Razorpay later if India conversion demands it
- Deployment: Vercel for frontend, managed Python host for backend

## 19. Known Tradeoffs

- Supabase Auth plus Django is cleaner than building OAuth directly in Django, but it adds one external identity dependency.
- Postgres is the better system of record, but Word Meaning still needs curated content work.
- Stripe-first reduces launch complexity, but UPI-native conversion in India may later justify Razorpay.

## 20. Next Build Artifacts

After this document, the next engineering artifacts should be:

1. Product-ready database schema
2. Django app skeleton
3. React app skeleton
4. API contract document
5. Generator interface and test spec
6. Seed data format for Word Meaning

## 21. Development Sections

Split the build into these implementation sections so development can happen in a clean order.

### Section 1: Product foundation

Scope:

- initialize Django backend
- initialize React frontend
- configure environments
- set up Supabase project
- set up Stripe project
- define local and production deployment strategy

Deliverables:

- running frontend and backend apps
- environment variable templates
- CI basics
- health check endpoints

### Section 2: Authentication and user accounts

Scope:

- Supabase Auth integration
- Google OAuth login
- Django JWT verification
- user sync and profile creation
- protected routes in React

Deliverables:

- sign in with Google
- authenticated API requests
- user profile and session persistence

### Section 3: Database schema and core models

Scope:

- create relational schema
- add migrations
- model users, subscriptions, attempts, sections, answers, plans
- define JSONB storage shape for generated questions

Deliverables:

- database schema finalized
- Django models and migrations
- seed config tables

### Section 4: Assessment engine

Scope:

- attempt lifecycle
- timed section engine
- full mock flow
- section sequencing
- server-side scoring rules

Deliverables:

- section attempt creation
- answer submission flow
- score calculation engine
- section and mock completion logic

### Section 5: Question generators

Scope:

- Reasoning generator
- Perceptual Speed generator
- Number Speed and Accuracy generator
- Word Meaning generator
- Spatial Visualization generator

Deliverables:

- shared generator interface
- deterministic generation by seed
- evaluation functions for each section
- generator unit tests

### Section 6: Seed data and content pipeline

Scope:

- build Word Meaning seed bank format
- create import commands
- add config imports for plans, penalties, percentile bands
- add versioning for seed data

Deliverables:

- importable seed files
- management commands
- validation and dry-run support

### Section 7: Frontend test-taking experience

Scope:

- section selection UI
- full mock flow UI
- timer UI
- question renderer for all 5 sections
- instruction and transition screens

Deliverables:

- working test interface
- responsive layout
- stable question rendering

### Section 8: Results, analytics, and dashboard

Scope:

- attempt history
- per-section results
- weak-section insights
- percentile band display
- progress trends

Deliverables:

- user dashboard
- result detail page
- history and analytics endpoints

### Section 9: Paywall and subscriptions

Scope:

- pricing plans
- Stripe checkout
- Stripe billing portal
- webhook processing
- entitlement enforcement

Deliverables:

- subscription purchase flow
- webhook-driven activation
- free-tier caps and paid access checks

### Section 10: Admin and internal tooling

Scope:

- admin management for seed data
- generator health tools
- payment event logs
- support visibility for users and subscriptions

Deliverables:

- Django admin setup
- internal operational tools
- import audit logs

### Section 11: Quality, security, and launch readiness

Scope:

- automated tests
- rate limiting
- observability
- error tracking
- launch QA

Deliverables:

- test suite
- monitoring and alerts
- production readiness checklist

## 22. Suggested Build Order

Recommended order:

1. Section 1: Product foundation
2. Section 2: Authentication and user accounts
3. Section 3: Database schema and core models
4. Section 4: Assessment engine
5. Section 5: Question generators
6. Section 6: Seed data and content pipeline
7. Section 7: Frontend test-taking experience
8. Section 8: Results, analytics, and dashboard
9. Section 9: Paywall and subscriptions
10. Section 10: Admin and internal tooling
11. Section 11: Quality, security, and launch readiness

## 23. Final Recommendation

Build v1 on `Django + React + Supabase Postgres + Supabase Auth + Stripe`.

This is the best balance of:

- speed to launch
- correctness for scoring and billing
- global readiness
- developer productivity
- future extensibility for analytics, additional tests, and B2B expansion
