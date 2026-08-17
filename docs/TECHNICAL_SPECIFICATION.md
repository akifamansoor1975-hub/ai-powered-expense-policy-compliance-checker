# Expense Policy Compliance Checker — Technical Specification

This document defines **how** the system described in `docs/PRD.md` and `docs/ARCHITECTURE.md` will be technically built. It is more detailed than the Architecture document but does not contain full application code — that belongs to the implementation stage.

---

## 1. Required Technical Stack

| Technology | Used For | Responsibility |
|---|---|---|
| **Python** | Core implementation language | Runs the entire service. |
| **FastAPI** | API layer | Exposes the four required endpoints and validates incoming requests. |
| **OpenAI Agents SDK** | AI agent framework | Defines and runs the AI Compliance Agent, its structured output, and its output guardrail. |
| **LLM** | Reasoning engine | Used by the agent to compare an expense against retrieved policy text and produce a verdict. |
| **LangChain** | Document processing pipeline | Loads uploaded policy documents, splits them into chunks, and generates embeddings. |
| **Pinecone** | Vector database | Stores policy chunk embeddings and performs similarity search during retrieval. |
| **Pydantic** | Data modeling and validation | Defines all request, response, and internal data structures, including the agent's structured output. |
| **PDF loader (via LangChain)** | Document parsing | Extracts text from uploaded policy PDF files. |
| **Embedding model/service** | Vector generation | Converts policy text chunks (and retrieval queries) into embeddings for Pinecone. |

No other frameworks, databases, or agent libraries are introduced. Pinecone remains the vector store, LangChain remains the document-processing framework, and the OpenAI Agents SDK remains the agent framework, consistent with `docs/ARCHITECTURE.md`.

---

## 2. Project Structure

```
app/
  api/
    policy_routes.py        # POST /policy/upload, GET /policy/versions
    compliance_routes.py    # POST /compliance/check, GET /compliance/{id}/clause
  agent/
    compliance_agent.py     # AI Compliance Agent definition and instructions
    output_guardrail.py     # Citation-enforcement output guardrail
  ingestion/
    document_loader.py      # Loads and extracts text from uploaded PDFs
    chunker.py               # Splits extracted text into chunks
    embedder.py               # Generates embeddings for chunks and queries
    ingestion_service.py    # Coordinates the upload -> chunk -> embed -> store flow
  retrieval/
    retriever.py              # Queries Pinecone for relevant policy chunks
    version_selector.py     # Determines the applicable policy version
  models/
    expense.py                # ExpenseClaim model
    compliance.py            # ComplianceResult, ReviewInfo models
    policy.py                  # PolicyVersion, PolicyChunkMetadata models
    citation.py                # PolicyCitation model
  services/
    pinecone_client.py       # Pinecone index connection and query/upsert helpers
    policy_store.py            # Lightweight store for policy version metadata
    result_store.py            # Lightweight store for past compliance results (for clause lookup)
  config/
    settings.py                # Loads environment variables / configuration
  utils/
    errors.py                  # Shared error types and error-response helpers
    logging.py                 # Logging setup
tests/
  test_ingestion.py
  test_versioning.py
  test_retrieval.py
  test_compliance.py
  test_guardrail.py
  test_api.py
docs/
  PRD.md
  ARCHITECTURE.md
  TECHNICAL_SPECIFICATION.md
main.py                          # FastAPI app entry point
.env.example
```

**Notes on structure:**
- `api/` contains only routing and request/response handling — no business logic.
- `agent/` isolates everything related to the AI Compliance Agent and its guardrail.
- `ingestion/` and `retrieval/` are separated because they represent the two flows described in the Architecture document.
- `services/pinecone_client.py`, `policy_store.py`, and `result_store.py` are implementation decisions needed to make the four API endpoints work as specified (see Section 21) — they are not new product features.
- This structure is a reasonable starting point and may be refined during implementation.

---

## 3. Configuration and Environment Variables

All secrets and environment-specific values must come from environment variables, never hard-coded, and never committed to Git.

| Variable | Purpose |
|---|---|
| `LLM_API_KEY` | Authentication for the LLM used by the AI agent. |
| `LLM_MODEL_NAME` | Which LLM model the agent uses. |
| `PINECONE_API_KEY` | Authentication for Pinecone. |
| `PINECONE_INDEX_NAME` | Name of the Pinecone index used for policy chunks. |
| `PINECONE_ENVIRONMENT` | Pinecone environment/region configuration. |
| `EMBEDDING_MODEL_NAME` | Which embedding model/service is used to generate vectors. |
| `EMBEDDING_API_KEY` | Authentication for the embedding service (may be the same as `LLM_API_KEY`, depending on provider). |

- A `.env` file holds actual local values and must **never** be committed to Git.
- A `.env.example` file (committed to Git) lists the required variable names with placeholder values, so a new developer knows what to configure.
- No real API keys or secrets appear anywhere in this document, the source code, or Git history.

---

## 4. Data Models

### 4.1 Expense Claim

| Field | Type | Required | Description |
|---|---|---|---|
| `category` | `string` | Yes | The expense category (e.g., "meals", "travel"). Confirmed by the PRD. |
| `amount` | `float` | Yes | The claimed expense amount. Confirmed by the PRD. |
| `expense_date` | `date` | Yes | *(Implementation decision)* The date the expense occurred. Needed to select the applicable policy version, as described in Section 12. The PRD lists "date" as an example additional expense detail. |
| `description` | `string` | No | Free-text detail about the expense, used to improve retrieval relevance. |

### 4.2 Compliance Result

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | `enum`: `"compliant"` \| `"non_compliant"` \| `"needs_approval"` \| `"policy_silent"` | Yes | The compliance outcome, matching the four statuses defined in the PRD. |
| `explanation` | `string` | Yes | Plain-language reason for the outcome. |
| `citation` | `PolicyCitation` (see 4.4) | Conditional | Required for `compliant`, `non_compliant`, and `needs_approval`. Not required for `policy_silent`. |
| `policy_version` | `string` | Yes | Identifier of the policy version used to reach the decision. |
| `needs_human_review` | `boolean` | Yes | `true` when the case is routed for human review (see Section 14). |
| `review_reason` | `string` | No | Present when `needs_human_review` is `true`; explains why (e.g., "insufficient evidence", "approval required"). |

### 4.3 Policy Version / Metadata

| Field | Type | Required | Description |
|---|---|---|---|
| `version_id` | `string` | Yes | Unique identifier for the policy version. |
| `effective_date` | `date` | Yes | Date the policy version becomes applicable. |
| `source_document` | `string` | Yes | Name/reference of the uploaded document this version came from. |
| `uploaded_at` | `datetime` | Yes | When this version was ingested. |

### 4.4 Policy Chunk Metadata (stored alongside each Pinecone vector)

| Field | Type | Required | Description |
|---|---|---|---|
| `chunk_id` | `string` | Yes | Unique identifier for the chunk. |
| `version_id` | `string` | Yes | Which policy version this chunk belongs to. |
| `source_document` | `string` | Yes | The document the chunk was extracted from. |
| `section_reference` | `string` | No | Section/clause label, if identifiable from the document (e.g., a heading). |
| `text` | `string` | Yes | The verbatim chunk text, needed to produce citations. |

### 4.5 Policy Citation

| Field | Type | Required | Description |
|---|---|---|---|
| `version_id` | `string` | Yes | The policy version the clause belongs to. |
| `source_document` | `string` | Yes | Which document the clause came from. |
| `section_reference` | `string` | No | Section/clause label, if available. |
| `clause_text` | `string` | Yes | The verbatim policy text supporting the verdict. |

---

## 5. API Specification

### `POST /policy/upload`

**Purpose:** Upload a company expense policy document and its effective date, and trigger ingestion.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file (PDF) | Yes | The policy document. |
| `effective_date` | `date` | Yes | When this policy version takes effect. |

**Example response:**
```json
{
  "version_id": "policy_2026_01",
  "effective_date": "2026-01-01",
  "source_document": "expense_policy_2026.pdf",
  "status": "ingested",
  "chunks_created": 84
}
```

**Possible errors:**
- `400 Bad Request` — missing file or missing `effective_date`.
- `415 Unsupported Media Type` — file is not a supported format.
- `500 Internal Server Error` — document processing, embedding, or Pinecone storage failed.

---

### `POST /compliance/check`

**Purpose:** Check an expense claim against the applicable policy version.

**Request body:**
```json
{
  "category": "meals",
  "amount": 12000,
  "expense_date": "2026-03-15",
  "description": "Client dinner in Karachi"
}
```

**Processing flow (high level):**
1. Validate the request body.
2. Determine the applicable policy version using `expense_date` (Section 12).
3. Retrieve relevant policy chunks for that version (Section 11).
4. Pass the expense and retrieved chunks to the AI Compliance Agent.
5. Validate the agent's structured output through the output guardrail (Section 16).
6. Persist the result so it can later be looked up via `GET /compliance/{id}/clause`.
7. Return the structured result.

**Example response (Compliant):**
```json
{
  "id": "check_7f3a",
  "status": "compliant",
  "explanation": "Client meals up to PKR 15,000 are allowed under the applicable policy.",
  "citation": {
    "version_id": "policy_2026_01",
    "source_document": "expense_policy_2026.pdf",
    "section_reference": "Section 4.2 - Client Meals",
    "clause_text": "Client meal expenses up to PKR 15,000 per event are reimbursable without prior approval."
  },
  "policy_version": "policy_2026_01",
  "needs_human_review": false
}
```

**Example response (Policy is Silent):**
```json
{
  "id": "check_9d21",
  "status": "policy_silent",
  "explanation": "The applicable policy does not address this type of expense.",
  "citation": null,
  "policy_version": "policy_2026_01",
  "needs_human_review": false
}
```

**Possible errors:**
- `400 Bad Request` — missing or invalid fields (e.g., negative amount).
- `409 Conflict` — no applicable policy version exists for the given `expense_date`.
- `500 Internal Server Error` — retrieval, agent, or guardrail failure.

---

### `GET /compliance/{id}/clause`

**Purpose:** Retrieve the policy clause that supported a previously produced compliance result.

**Path parameter:** `id` — the compliance result identifier returned by `POST /compliance/check`.

**Example response:**
```json
{
  "id": "check_7f3a",
  "citation": {
    "version_id": "policy_2026_01",
    "source_document": "expense_policy_2026.pdf",
    "section_reference": "Section 4.2 - Client Meals",
    "clause_text": "Client meal expenses up to PKR 15,000 per event are reimbursable without prior approval."
  }
}
```

**Possible errors:**
- `404 Not Found` — the compliance result does not exist.
- `404 Not Found` — the result exists but has no citation (e.g., its status was `policy_silent`); the response should state this clearly rather than returning an empty object.

---

### `GET /policy/versions`

**Purpose:** List the available policy versions.

**Example response:**
```json
{
  "versions": [
    { "version_id": "policy_2025_06", "effective_date": "2025-06-01", "source_document": "expense_policy_2025.pdf" },
    { "version_id": "policy_2026_01", "effective_date": "2026-01-01", "source_document": "expense_policy_2026.pdf" }
  ]
}
```

No additional endpoints are introduced beyond the four required by the PRD.

---

## 6. Policy Ingestion Implementation

Pipeline: **Upload → Load → Extract → Chunk → Embed → Store**

1. **Upload** — `POST /policy/upload` accepts the PDF file and effective date as multipart form data.
2. **Load** — a LangChain PDF document loader reads the uploaded file.
3. **Extract** — text is extracted from the loaded document.
4. **Chunk** — the extracted text is split using LangChain's recursive character text splitter.
   - *(Implementation decision)* Starting chunk size: **~1000 characters**, with **~150 character overlap**. This is a reasonable starting point for policy-style text and can be tuned later based on retrieval quality.
5. **Embed** — each chunk is passed to the configured embedding model/service to produce a vector.
6. **Store** — each embedding is upserted into Pinecone along with its metadata (Section 4.4): `chunk_id`, `version_id`, `source_document`, `section_reference` (if available), and `text`.

The policy version record itself (`version_id`, `effective_date`, `source_document`) is saved to the lightweight policy metadata store (Section 2) so `GET /policy/versions` can list it without querying Pinecone directly.

---

## 7. Pinecone Design

- **Index purpose:** stores vector representations of policy text chunks for similarity search.
- **What each vector represents:** one chunk of policy text from one policy version.
- **Embedding dimension:** *(Implementation decision)* not fixed by the PRD or F9 source. A recommended starting choice is an OpenAI-compatible embedding model such as `text-embedding-3-small` (1536 dimensions), since the project already uses an OpenAI-compatible LLM setup. The Pinecone index must be created with a dimension matching whichever embedding model is actually configured.
- **Metadata stored per vector:** `chunk_id`, `version_id`, `source_document`, `section_reference`, `text` (see Section 4.4).
- **Vector identification:** each vector is stored with a unique `chunk_id` as its Pinecone record ID.
- **Retrieval queries:** a query embedding is compared against stored vectors using similarity search.
- **Policy version filtering:** retrieval queries include a metadata filter on `version_id`, so results only come from the applicable policy version (Section 12).

---

## 8. Retrieval Design

1. An expense claim is received by `POST /compliance/check`.
2. The applicable policy version is determined (Section 12).
3. A retrieval query is built from the expense's `category` and `description` fields.
4. The query text is embedded using the same embedding model used during ingestion.
5. Pinecone similarity search is performed, filtered by the applicable `version_id`.
6. Metadata filtering ensures no chunks from a different policy version are returned.
7. The top-matching chunks are returned.
   - *(Implementation decision)* Starting **top-k = 5**. This is a reasonable default and can be tuned later.
8. The retrieved chunk texts (with their metadata) are passed to the AI Compliance Agent as its evidence.

**When no useful chunks are found** (e.g., similarity scores are all low, or no chunks exist for the applicable version): the retrieval step returns an empty or low-confidence result set. The AI Compliance Agent must then produce `policy_silent` rather than guessing, consistent with the PRD's citation and evidence requirement (Section 16 below).

*(Implementation decision)* A relevance threshold may be applied to filter out clearly irrelevant chunks before they reach the agent; the exact threshold value is left to be tuned during implementation and is not a fixed product requirement.

---

## 9. Policy Version Selection

**Rule (confirmed by the PRD and Architecture document):** the expense must be evaluated against the policy version that was applicable on the expense's date, not automatically the newest version.

**Logic:**
1. Take the expense's `expense_date`.
2. From the stored policy versions, find all versions whose `effective_date` is **on or before** `expense_date`.
3. Among those, select the version with the **latest** `effective_date` — this is the version that was in effect on that date.
4. If no version qualifies (i.e., every stored version has an `effective_date` after the expense date), there is **no applicable policy version**. The API returns `409 Conflict` (Section 5) rather than guessing a version.
5. If two versions share the same `effective_date` (an edge case), the most recently uploaded one is treated as authoritative. *(Implementation decision — this scenario is not addressed by the PRD or F9 source.)*

The selected `version_id` is passed directly into the retrieval step (Section 8) as the metadata filter.

---

## 10. AI Agent Design

**Agent input:**
- The expense claim (`category`, `amount`, `expense_date`, `description`)
- The retrieved policy chunks for the applicable version (text + metadata)

**Agent instructions must enforce:**
- Base every decision only on the retrieved policy chunks provided — **never on general knowledge of typical expense policies**.
- If the retrieved chunks do not clearly address the expense, return `policy_silent` rather than inferring a rule.
- If the policy text indicates the expense type requires approval, return `needs_approval` and cite the relevant clause.
- Always include a verbatim citation from the retrieved chunks for any `compliant`, `non_compliant`, or `needs_approval` result.
- Never fabricate a citation, section reference, or clause text not present in the retrieved chunks.

**What the agent is allowed to use as evidence:** only the retrieved policy chunk text passed to it for this request.

**What the agent must not do:**
- Must not use general knowledge to invent policy rules.
- Must not produce a compliance verdict without a matching citation from the retrieved chunks.
- Must not hold a multi-turn conversation — each request is a single, self-contained evaluation.

The exact production prompt wording is an implementation detail to be written during development; this section defines what it must enforce.

---

## 11. Structured Output

The agent's `output_type` is the **Compliance Result** model defined in Section 4.2.

| Status | Citation Required? | Human Review? |
|---|---|---|
| `compliant` | Yes | No |
| `non_compliant` | Yes | No |
| `needs_approval` | Yes | Yes |
| `policy_silent` | No | Depends on case — set to `true` only if the case also needs manual follow-up beyond the silence itself |

**Ambiguity flagged:** neither the PRD nor the F9 source specifies whether a `policy_silent` result should always be routed to human review or only sometimes. This specification treats `needs_human_review` for `policy_silent` as case-dependent (e.g., true if a human should still look at an unusual claim), and this behavior should be confirmed with stakeholders during implementation rather than assumed.

---

## 12. Citation Design

A citation (Section 4.5) must contain enough information to:
- Identify which **policy version** it came from (`version_id`)
- Identify the **source document** (`source_document`)
- Identify the **clause/section**, when available (`section_reference`)
- Reproduce the **verbatim clause text** (`clause_text`)

**How it is created:** when the agent selects a retrieved chunk as its supporting evidence, it copies that chunk's metadata and text directly into the `citation` field of its structured output — it does not rewrite or summarize the clause.

**How it is preserved:** the full `ComplianceResult`, including its `citation`, is saved to the result store (Section 2) at the same time the response is returned to the client.

**How `GET /compliance/{id}/clause` uses it:** the endpoint looks up the stored `ComplianceResult` by `id` and returns its `citation` field. If the result has no citation (e.g., `policy_silent`), the endpoint returns `404 Not Found` with a message explaining that no citation exists for this result.

---

## 13. Output Guardrail

The output guardrail runs after the agent produces its structured result and before the API returns a response.

**Checks performed:**
1. Is the result one of the four valid statuses?
2. If the status is `compliant`, `non_compliant`, or `needs_approval` — is a `citation` present?
3. Does the citation contain non-empty `version_id`, `source_document`, and `clause_text` values?
4. Does the result otherwise match the `ComplianceResult` schema (structurally valid)?

**When validation fails** (e.g., a compliance verdict with no citation, or a malformed result):
- The result is **not** returned to the client as a compliance verdict.
- The case is instead converted to a result with `needs_human_review: true` and a `review_reason` explaining that automatic validation failed.
- This enforces the PRD's core rule: **a `compliant`, `non_compliant`, or `needs_approval` result must never be returned without supporting policy evidence.**

This section describes the guardrail's required behavior only; its implementation as an `@output_guardrail` function is left to the implementation stage.

---

## 14. Error Handling

| Category | Cause | System Behavior | HTTP Status |
|---|---|---|---|
| Invalid request | Missing/malformed fields in request body | Reject before processing | `400 Bad Request` |
| Missing required fields | Required field absent (e.g., no `amount`) | Reject with a field-specific message | `400 Bad Request` |
| Invalid/unsupported policy file | Non-PDF or unreadable file uploaded | Reject the upload | `415 Unsupported Media Type` |
| Policy processing failure | Text extraction or chunking fails | Reject the upload, log the failure | `500 Internal Server Error` |
| Embedding failure | Embedding service unavailable or errors | Fail the current operation (upload or check), log the failure | `500 Internal Server Error` |
| Pinecone failure | Index unreachable or query/upsert fails | Fail the current operation, log the failure | `500 Internal Server Error` |
| No applicable policy version | No stored version has an effective date on/before the expense date | Reject the compliance check | `409 Conflict` |
| No relevant policy evidence | Retrieval returns no useful chunks | Agent returns `policy_silent`; not treated as an API error | `200 OK` (with `policy_silent` status) |
| Invalid agent output | Agent output does not match the expected schema | Output guardrail intercepts; route to human review | `200 OK` (with `needs_human_review: true`) |
| Missing citation | Verdict lacks a citation | Output guardrail intercepts; route to human review | `200 OK` (with `needs_human_review: true`) |
| Internal server error | Any unhandled exception | Return a generic safe error message, log full details internally | `500 Internal Server Error` |

Errors that represent a genuine request problem return an HTTP error status. Situations where the *system* cannot safely produce an automatic verdict (missing evidence, missing citation, invalid output) are handled as successful requests that route to human review, consistent with the PRD's treatment of human review as a designed outcome, not a failure.

---

## 15. Logging and Observability

Logs should capture, at minimum:
- Policy upload attempts, including success/failure and the resulting `version_id`
- Which policy version was processed during an upload
- Retrieval attempts, including success/failure and number of chunks retrieved
- The compliance status returned for each check (without necessarily logging full expense details, depending on data sensitivity)
- Output guardrail failures (missing citation, invalid structure)
- Unexpected/internal errors, with enough detail for debugging

**Must never be logged:**
- API keys or other secrets
- Passwords
- Full raw environment variable values

Logging can use Python's standard `logging` module; no additional observability platform is required for this project.

---

## 16. Security Requirements

- All secrets (LLM key, Pinecone key, embedding service key) are read from environment variables, never hard-coded.
- No API keys or secrets are committed to Git; `.env` is excluded via `.gitignore`, and `.env.example` contains only placeholder names.
- Uploaded files are validated for type (PDF) before processing.
- Policy documents may contain internal company information and should be stored and transmitted securely (e.g., not logged in full, not exposed through unauthenticated endpoints beyond what the product requires).
- All API inputs are validated using Pydantic models before being used internally.
- Error responses returned to clients contain safe, generic messages; detailed internal error information stays in server-side logs only.
- Logs avoid including sensitive information (see Section 15).

This section defines practical, project-appropriate security requirements and does not constitute a full enterprise security specification.

---

## 17. Testing Requirements

### Policy ingestion
- Uploading a valid policy PDF succeeds and creates chunks.
- Uploading an invalid/unsupported file is rejected.
- Chunking produces a reasonable number of non-empty chunks for a sample document.
- Metadata is correctly attached to each stored chunk.

### Policy versioning
- The correct version is selected when the expense date matches an existing version's effective date.
- An older version is correctly selected when it was applicable on the expense date, even if a newer version exists.
- A newer version is correctly selected when its effective date has passed.
- A `409 Conflict` is returned when no applicable version exists.

### Retrieval
- A relevant policy chunk is retrieved for a matching expense category.
- Chunks from a non-applicable policy version are never returned.
- An expense with no matching policy content results in an empty/low-relevance retrieval, leading to `policy_silent`.

### Compliance
- A clearly compliant expense returns `compliant` with a citation.
- A clearly non-compliant expense returns `non_compliant` with a citation.
- An expense requiring approval returns `needs_approval` with `needs_human_review: true`.
- An expense not addressed by the policy returns `policy_silent`.
- An expense with insufficient retrieved evidence does not produce a forced verdict.

### Citation guardrail
- A valid result with a proper citation passes the guardrail unchanged.
- A result missing a citation is intercepted and converted to a human-review outcome.
- A structurally invalid result is intercepted and converted to a human-review outcome.

### API
- Each of the four endpoints returns the expected response for valid input.
- Each endpoint returns the expected error response for invalid input (see Section 14).

---

## 18. Technical Decisions and Assumptions

### Confirmed Requirements (from PRD / F9)
- RAG using Pinecone and LangChain is required.
- FastAPI service with exactly the four specified endpoints.
- Structured output for every compliance check.
- A compliance verdict must always include a verbatim policy citation, except `policy_silent`.
- Multiple policy versions with effective dates must be supported, and the applicable version must be selected correctly.
- Human review is a designed outcome for uncertain or approval-required cases.
- The OpenAI Agents SDK is used for the AI agent.

### Implementation Decisions
- Project folder structure (Section 2).
- Chunk size (~1000 characters) and overlap (~150 characters).
- Retrieval `top-k = 5`.
- Recommended embedding model: an OpenAI-compatible model such as `text-embedding-3-small` (1536 dimensions), configurable via environment variables.
- A lightweight metadata/result store for policy versions and past compliance results, needed to support `GET /policy/versions` and `GET /compliance/{id}/clause`.
- Tie-breaking rule for two policy versions sharing the same effective date.

### Assumptions
- `expense_date` is treated as a required expense claim field, since it is necessary to select the applicable policy version and is mentioned as an example field in the PRD.
- Whether `policy_silent` results always require human review, or only in some cases, is left as an open question for stakeholder confirmation (see Section 11).
- Exact performance/response-time targets are not defined by the source material and are not specified numerically here.

---

## 19. Implementation Boundaries

This document defines data models, API contracts, processing flows, and technical rules in enough detail to guide implementation. It does **not** include:

- Complete application source code
- Full Python class or function implementations
- Deployment configuration (hosting, containers, CI/CD)
- Authentication/authorization implementation
- Final production prompt text for the AI agent

The next stage is implementation, carried out directly from this Technical Specification together with `docs/PRD.md` and `docs/ARCHITECTURE.md`.
