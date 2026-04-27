# SalesCatalyst — Full System Design Spec
**Date:** 2026-04-27  
**Stack:** Django 5 + DRF + PostgreSQL · React 19 + Vite + Tailwind · Django-Q2 · Gemini API  
**Scope:** Core platform (Phases 1–7). Adhoc tier (HubSpot, real-time AI analyst) is out of scope for this spec.

---

## 1. Purpose

SalesCatalyst is an internal B2B sales automation platform for chemical trading. It helps internal sales team members complete the full sales cycle: discovering buyer leads for a product, enriching contact data, sending templated emails with product brochures, following up automatically, managing negotiations with AI assistance, scheduling meetings, and closing deals.

---

## 2. Build Phases

Each phase is independently usable and feeds the next.

| Phase | Name | Deliverable |
|-------|------|-------------|
| 1 | Core Platform + Auth | Django project, PostgreSQL schema, JWT auth, admin |
| 2 | Lead Discovery Engine | Campaign form, Volza API, LUSHA enrichment |
| 3 | Customer Dashboard + Pipeline | Lead list, progress bar, contact cards, CSV export |
| 4 | Communication Engine | Email send (intro + pricing), call log, scheduled follow-ups |
| 5 | AI Email Assistant | Gemini draft generation, human approval gate |
| 6 | Meeting + Google Calendar | Meeting scheduling, calendar event creation |
| 7 | Deal Closure + Flow Visualization | Won/lost marking, journey timeline chart |

---

## 3. System Architecture

### 3.1 Local Ports

| Service | Port |
|---------|------|
| React + Vite (FE) | 5173 |
| Django DRF (BE) | 8000 |
| PostgreSQL | 5432 |
| Django-Q2 qcluster | (same process, separate terminal) |

### 3.2 Layer Overview

```
Browser (React 19 + Vite)
  │  JWT Bearer Token — REST API calls
  ▼
Django 5 + DRF (localhost:8000)
  │  6 apps: accounts · leads · campaigns · communications · ai_assistant · deals
  │  Django ORM
  ▼
PostgreSQL 16 (localhost:5432)
  │  Also used as Django-Q2 ORM broker
  ▼
Django-Q2 qcluster (background workers)
  │  HTTPS API calls
  ▼
External: Volza API · LUSHA API · Gmail SMTP · Gemini API · Google Calendar API
```

### 3.3 Frontend Stack

- **React 19 + Vite 8** — existing scaffolded project in `/FE`
- **React Router v6** — client-side routing
- **TanStack Query** — server state, caching, background refetch
- **Tailwind CSS v4 + shadcn/ui** — component library
- **Axios** — HTTP client with JWT interceptor

### 3.4 Backend Stack

- **Django 5 + DRF** — REST API only (no server-rendered templates except admin)
- **djangorestframework-simplejwt** — JWT auth (15 min access, 7 day refresh)
- **Django-Q2** — background task queue using PostgreSQL as broker (no Redis)
- **django-environ** — env var management
- **Pillow** — image handling for any future media
- **django-cors-headers** — CORS for FE dev server

---

## 4. Database Schema

All models inherit `TimestampedModel` (created_at, updated_at). All primary keys are UUID.

### 4.1 Product

```
Product
  id            UUID PK
  name          CharField(255)
  hsn_code      CharField(50)
  cas_number    CharField(50)
  description   TextField
  technical_specs  JSONField (default={})
  brochure_pdf  FileField (nullable) ← fixed PDF uploaded by team, one per product
  created_by    FK(User)
```

### 4.2 Campaign

```
Campaign
  id                    UUID PK
  title                 CharField(255)
  products              M2M(Product)  ← multiple products per search session
  country_filters       JSONField     ← e.g. ["IN", "US", "DE"]
  num_transactions_yr   IntegerField
  created_by            FK(User)
  status                ENUM: active | paused | completed
```

### 4.3 Lead

```
Lead
  id                UUID PK
  campaign          FK(Campaign)
  company_name      CharField(255)
  company_country   CharField(10)
  company_website   CharField(255, blank)
  stage             ENUM: discovered | intro_sent | pricing_sent | pricing_followup | meeting_set | closed_won | closed_lost
  auto_flow_paused  BooleanField (default=False) ← stops all automation for this lead
  assigned_to       FK(User, null)
  volza_data        JSONField (raw Volza API response)
  pricing_trend     JSONField (default={})
  purchase_history  JSONField (default={})
```

**Lead.stage state machine:**
```
discovered → intro_sent → pricing_sent → pricing_followup → meeting_set → closed_won
                                                                         ↘ closed_lost
auto_flow_paused = True can be set at any stage to freeze automation
```

### 4.4 Contact

```
Contact
  id            UUID PK
  lead          FK(Lead, related_name='contacts')
  first_name    CharField(100)
  last_name     CharField(100)
  designation   CharField(200)
  email         EmailField (null, blank)   ← nullable; missing = flag for CSV export
  phone         CharField(30, null, blank) ← nullable; missing = flag for CSV export
  linkedin_url  URLField (null, blank)
  source        ENUM: volza | lusha | manual
  is_primary    BooleanField (default=False)
  lusha_raw     JSONField (default={})
```

A Lead with no Contact where both email AND phone are null is flagged as "missing contact" and included in the CSV export.

### 4.5 LeadAction

```
LeadAction
  id            UUID PK
  lead          FK(Lead, related_name='actions')
  performed_by  FK(User, null) ← null = system/automated action
  action_type   ENUM: intro_email | follow_up_call | pricing_email | pricing_followup_email | meeting_scheduled | note | ai_draft_generated | ai_draft_approved | ai_draft_rejected | deal_closed | manual_takeover
  notes         TextField (blank)
  metadata      JSONField (default={}) ← email subject/body, call notes, API response snippets
```

This is the single source of truth for the journey timeline and flow visualization.

### 4.6 EmailThread + EmailMessage

```
EmailThread
  id              UUID PK
  lead            FK(Lead)
  contact         FK(Contact)
  subject         CharField(500)
  thread_type     ENUM: intro | pricing | followup | negotiation
  gmail_thread_id CharField(200) ← Gmail thread ID for reply-chaining

EmailMessage
  id              UUID PK
  thread          FK(EmailThread, related_name='messages')
  direction       ENUM: outbound | inbound
  body_html       TextField
  body_text       TextField
  sent_at         DateTimeField
  gmail_message_id  CharField(200)
```

### 4.7 AIDraft

```
AIDraft
  id               UUID PK
  lead             FK(Lead)
  thread           FK(EmailThread)
  draft_content    TextField      ← Gemini-generated reply
  context_summary  TextField      ← brief summary of what Gemini saw
  status           ENUM: pending_review | approved | rejected | sent
  reviewed_by      FK(User, null)
  reviewed_at      DateTimeField (null)
```

**Invariant:** AIDraft is NEVER sent automatically. status must be `approved` by a human before the send endpoint fires.

### 4.8 Meeting

```
Meeting
  id                UUID PK
  lead              FK(Lead)
  contact           FK(Contact)
  scheduled_by      FK(User)
  calendar_event_id CharField(200) ← Google Calendar event ID
  scheduled_at      DateTimeField
  meeting_link      CharField(500, blank)
  notes             TextField (blank)
  status            ENUM: proposed | confirmed | completed | cancelled
```

### 4.9 Deal

```
Deal
  id          UUID PK
  lead        OneToOneField(Lead) ← one final outcome per lead
  outcome     ENUM: won | lost
  closed_by   FK(User)
  closed_at   DateTimeField
  remarks     TextField
  deal_value  DecimalField(10, 2, null)
```

---

## 5. Django App Structure

```
BE/
  manage.py
  config/
    settings/
      base.py
      local.py
    urls.py
    wsgi.py
  common/
    models.py     ← TimestampedModel base
    utils.py
  accounts/       ← Auth + User
  campaigns/      ← Campaign + Product CRUD
  leads/          ← Lead + Contact + LeadAction
  communications/ ← EmailThread + EmailMessage + call logging + Gmail SMTP
  ai_assistant/   ← AIDraft + Gemini integration
  deals/          ← Deal + Meeting + Google Calendar
```

---

## 6. REST API Endpoints

All endpoints require `Authorization: Bearer <access_token>` unless marked public.

### accounts
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/auth/login/` | Email + password → JWT pair |
| POST | `/api/auth/refresh/` | Rotate access token |
| POST | `/api/auth/logout/` | Blacklist refresh token |
| GET | `/api/auth/me/` | Current user profile |

### campaigns + leads
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/campaigns/` | List with lead counts |
| POST | `/api/campaigns/` | Create + trigger Volza enrichment async |
| GET | `/api/campaigns/:id/` | Detail with stats |
| PATCH | `/api/campaigns/:id/` | Update status / pause |
| GET | `/api/campaigns/:id/leads/` | Lead list, filterable by stage |
| POST | `/api/campaigns/:id/export-missing/` | Return CSV of leads missing email+phone |
| GET | `/api/leads/:id/` | Lead detail (contacts, actions, threads) |
| PATCH | `/api/leads/:id/` | Update stage / toggle auto_flow_paused |
| POST | `/api/leads/:id/actions/` | Log manual action (call note, takeover) |
| GET | `/api/leads/:id/actions/` | Full action history for timeline |

### communications
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/leads/:id/send-intro/` | Send intro email + brochure PDF |
| POST | `/api/leads/:id/send-pricing/` | Send pricing email |
| POST | `/api/leads/bulk-send-intro/` | Bulk intro to checkbox-selected leads |
| GET | `/api/leads/:id/threads/` | All email threads for lead |
| GET | `/api/threads/:id/messages/` | All messages in thread |
| POST | `/api/leads/:id/log-call/` | Log call with notes + outcome |

### ai_assistant
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/leads/:id/generate-draft/` | Gemini draft → AIDraft(pending_review) |
| GET | `/api/ai-drafts/` | Pending draft queue |
| GET | `/api/ai-drafts/:id/` | Single draft with thread context |
| POST | `/api/ai-drafts/:id/approve/` | Send via Gmail, mark sent, log action |
| POST | `/api/ai-drafts/:id/reject/` | Reject with optional note |

### deals + meetings + products
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/leads/:id/close/` | Create Deal (won/lost + remarks) |
| POST | `/api/leads/:id/schedule-meeting/` | Create Google Calendar event + Meeting |
| GET | `/api/products/` | List products |
| POST | `/api/products/` | Create product |
| PATCH | `/api/products/:id/` | Update + upload brochure PDF |
| DELETE | `/api/products/:id/` | Delete product |

---

## 7. Background Tasks (Django-Q2)

| Task | Trigger | Behaviour |
|------|---------|-----------|
| `enrich_leads_from_volza` | Campaign created | Call Volza API → create Lead + Contact records |
| `enrich_contacts_from_lusha` | Lead has no email+phone after Volza | Call LUSHA → fill Contact fields |
| `schedule_pricing_email` | Intro email sent (T+0) | Create scheduled task for T+4 days |
| `send_pricing_email` | T+4 days, no inbound EmailMessage detected | Send pricing email via Gmail, log LeadAction |
| `schedule_pricing_followup` | Pricing email sent | Schedule follow-up task for T+4 days if no reply |

Reply detection: check `EmailMessage.direction = inbound` on the lead's thread since the last outbound send. If none exists, fire the scheduled email.

### 7.1 Inbound Email Polling

Gmail SMTP is send-only. To detect customer replies, a Django-Q2 periodic task (`poll_gmail_inbox`) runs every 15 minutes using the **Gmail API** (read scope via OAuth2). It:
1. Fetches all threads that match known `gmail_thread_id` values stored in EmailThread
2. For each thread, checks for messages newer than the last stored EmailMessage
3. Creates `EmailMessage(direction=inbound)` records for any new customer replies
4. This is what the follow-up schedulers check before firing automated emails

**Additional env var required:**
```
GMAIL_OAUTH_CREDENTIALS_JSON=  # path to OAuth2 credentials JSON (read scope)
```

---

## 8. External Integration Contracts

### 8.1 Volza API
- **Input:** product_name, hsn_code, country filters, min_transactions
- **Output stored:** Lead.company_name, country, volza_data (raw JSON), purchase_history; Contact.first_name, designation, email (if present)

### 8.2 LUSHA API
- **Input:** first_name, last_name, company_name (from Volza contact data)
- **Output stored:** Contact.email, phone, linkedin_url, lusha_raw (raw JSON); Contact.source = "lusha"

### 8.3 Gmail SMTP
- **Settings:** smtp.gmail.com:587, TLS, app password via env var
- **On intro send:** attach `product.brochure_pdf` as file attachment
- **Always:** store gmail_message_id + gmail_thread_id on EmailMessage for thread chaining

### 8.4 Gemini API (Free Tier)
- **Model:** gemini-2.0-flash
- **Prompt inputs:** product name, lead company name, pricing trend, full email thread history
- **Output:** AIDraft.draft_content (plain text email body)
- **Hard rule:** draft_content is NEVER sent without human approval (AIDraft.status = approved)

### 8.5 Google Calendar API
- **Auth:** OAuth2 service account credentials via env var
- **On meeting schedule:** create event with attendees (contact email + internal user), store calendar_event_id on Meeting

---

## 9. Frontend Pages

| Route | Page | Key components |
|-------|------|----------------|
| `/login` | Login | Email + password form, JWT storage |
| `/dashboard` | Overview | Stat cards, pipeline funnel, attention queue |
| `/campaigns/new` | New campaign | Product multi-select, country checklist, search trigger |
| `/campaigns/:id/leads` | Lead list | Filterable table, checkboxes, bulk send, CSV export |
| `/leads/:id` | Lead detail | Progress bar (7 stages), Email/Call/Timeline tabs, pause toggle, close deal |
| `/products` | Products | CRUD list, brochure PDF upload per product |
| `/ai-drafts` | AI draft queue | Pending cards, inline edit, approve/reject |

---

## 10. Environment Variables

```
# Django
SECRET_KEY=
DEBUG=True
DATABASE_URL=postgresql://localhost:5432/salescatalyst

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Gmail SMTP
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=   # Gmail app password

# External APIs
VOLZA_API_KEY=
LUSHA_API_KEY=
GEMINI_API_KEY=

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS_JSON=  # path to service account JSON
```

---

## 11. Out of Scope (This Spec)

- HubSpot integration
- Real-time Sales AI analyst (Gong/Sybill)
- LinkedIn direct integration (LUSHA covers this)
- Multi-tenant / role-based permissions (single internal team)
- Mobile app
- Deployment / production infrastructure

---

## 12. Key Invariants

1. `AIDraft` is never sent without `status = approved` set by a human user.
2. `auto_flow_paused = True` on any Lead stops ALL automated tasks for that lead — schedulers must check this flag before firing.
3. Every automated system action creates a `LeadAction(performed_by=None)` for the audit trail.
4. `Deal` is OneToOne with `Lead` — a lead can only be closed once.
5. Brochure PDFs are static uploads per Product — no dynamic generation.
6. All secrets are env vars — never committed to git.
