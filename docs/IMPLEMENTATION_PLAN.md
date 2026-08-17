# Expense Policy Compliance Checker — Implementation Plan

This document converts `docs/TECHNICAL_SPECIFICATION.md` (together with `docs/PRD.md` and `docs/ARCHITECTURE.md`) into an ordered, task-by-task development plan. It is meant to be followed step by step, and to be given to an AI coding agent (OpenCode) one task at a time.

No new product features, requirements, or technologies are introduced here. Every task exists to implement something already defined in the prior documents.

---

## How to Read This Plan

Each task follows this format:

### Task X — Task Name
**Goal:** What this task accomplishes.
**Dependencies:** What must already exist before starting.
**Work:** Specific implementation actions.
**Acceptance Criteria:** Conditions that must be true when done.
**Verification:** How to check the result.

Tasks are grouped into phases, and phases are ordered by dependency — each phase relies only on phases completed before it.

---

## Phase 1 — Project Foundation

**Purpose:** Get a running, empty FastAPI service with configuration and dependencies in place, before any business logic is added.

### Task 1.1 — Repository and Python Environment Setup
- [ ] **Goal:** Create the base project structure and a working Python environment.
**Dependencies:** None.
**Work:**
- Create the folder structure defined in `docs/TECHNICAL_SPECIFICATION.md` Section 2 (`app/`, `tests/`, `docs/`, `main.py`, etc.).
- Set up a Python virtual environment.
**Acceptance Criteria:**
- The folder structure matches the Technical Specification.
- The virtual environment activates without errors.
**Verification:** Manually inspect the folder tree against Section 2 of the Technical Specification.

### Task 1.2 — Install Core Dependencies
- [ ] **Goal:** Install the technologies listed in the Technical Specification's required stack.
**Dependencies:** Task 1.1.
**Work:**
- Add a dependency file (e.g., `requirements.txt` or `pyproject.toml`) listing: FastAPI, Pydantic, the OpenAI Agents SDK, LangChain, the Pinecone client, and an ASGI server.
- Install the dependencies.
**Acceptance Criteria:**
- All dependencies install without conflicts.
- No dependency outside the Technical Specification's stack (Section 1) is added.
**Verification:** Run the dependency installation command and confirm a clean install.

### Task 1.3 — `.gitignore` and `.env.example`
- [ ] **Goal:** Prevent secrets and local artifacts from being committed.
**Dependencies:** Task 1.1.
**Work:**
- Create `.gitignore` excluding `.env`, virtual environment folders, and cache files.
- Create `.env.example` listing the variable names from Technical Specification Section 3 with placeholder values only.
**Acceptance Criteria:**
- `.env` is excluded from Git.
- `.env.example` contains no real secrets.
**Verification:** Confirm `.env` does not appear in `git status` after being created locally.

### Task 1.4 — Configuration/Settings Module
- [ ] **Goal:** Centralize environment variable loading.
**Dependencies:** Task 1.3.
**Work:**
- Implement `app/config/settings.py` to load and expose the environment variables listed in Technical Specification Section 3 (`LLM_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `EMBEDDING_MODEL_NAME`, etc.).
**Acceptance Criteria:**
- Missing required variables produce a clear startup error, not a silent failure.
- No secret value is hard-coded.
**Verification:** Start the app with a variable missing and confirm a clear error is raised.

### Task 1.5 — FastAPI Entry Point and Health Endpoint
- [ ] **Goal:** Get a running FastAPI application.
**Dependencies:** Task 1.2, Task 1.4.
**Work:**
- Implement `main.py` to create the FastAPI app and load settings.
- Add a simple `GET /health` endpoint for development verification (not one of the four product endpoints).
**Acceptance Criteria:**
- The app starts successfully.
- `GET /health` returns a success response.
**Verification:** Start the server and call `/health` locally.

---

## Phase 2 — Data Models

**Purpose:** Implement the models from Technical Specification Section 4, so every later component has a shared, typed contract.

### Task 2.1 — Expense Claim Model
- [ ] **Goal:** Implement the `ExpenseClaim` model.
**Dependencies:** Task 1.2.
**Work:** Create `app/models/expense.py` with fields `category`, `amount`, `expense_date`, `description`, per Technical Specification Section 4.1.
**Acceptance Criteria:** Required fields (`category`, `amount`, `expense_date`) are enforced; `description` is optional; types match the specification.
**Verification:** Write a quick model instantiation test with valid and invalid data.

### Task 2.2 — Compliance Result Model
- [ ] **Goal:** Implement the `ComplianceResult` model.
**Dependencies:** Task 1.2.
**Work:** Create `app/models/compliance.py` with `status` (enum of the four values), `explanation`, `citation` (optional), `policy_version`, `needs_human_review`, `review_reason` (optional), per Technical Specification Section 4.2.
**Acceptance Criteria:** `status` only accepts the four defined values; the model can represent all four statuses correctly.
**Verification:** Instantiate the model with each of the four status values.

### Task 2.3 — Policy Version Model
- [ ] **Goal:** Implement the `PolicyVersion` model.
**Dependencies:** Task 1.2.
**Work:** Create `app/models/policy.py` with `version_id`, `effective_date`, `source_document`, `uploaded_at`, per Technical Specification Section 4.3.
**Acceptance Criteria:** All fields required and correctly typed.
**Verification:** Instantiate the model with sample data.

### Task 2.4 — Policy Chunk Metadata Model
- [ ] **Goal:** Implement the `PolicyChunkMetadata` model.
**Dependencies:** Task 2.3.
**Work:** Add to `app/models/policy.py`: `chunk_id`, `version_id`, `source_document`, `section_reference` (optional), `text`, per Technical Specification Section 4.4.
**Acceptance Criteria:** Model matches the metadata that will be stored per Pinecone vector.
**Verification:** Instantiate the model with sample chunk data.

### Task 2.5 — Policy Citation Model
- [ ] **Goal:** Implement the `PolicyCitation` model.
**Dependencies:** Task 2.3.
**Work:** Create `app/models/citation.py` with `version_id`, `source_document`, `section_reference` (optional), `clause_text`, per Technical Specification Section 4.5.
**Acceptance Criteria:** Model can be embedded inside `ComplianceResult.citation`.
**Verification:** Instantiate a `ComplianceResult` with a nested `PolicyCitation`.

---

## Phase 3 — Policy Version and Metadata Storage

**Purpose:** Provide the lightweight storage identified in Technical Specification Section 2 and 21 — needed only to support `GET /policy/versions` and `GET /compliance/{id}/clause`, not a general-purpose database.

### Task 3.1 — Policy Metadata Store
- [ ] **Goal:** Store and list policy version records.
**Dependencies:** Task 2.3.
**Work:** Implement `app/services/policy_store.py` with functions to save a `PolicyVersion` and list all stored versions. Use the simplest storage approach consistent with the Technical Specification (e.g., a lightweight file-based or embedded store) — do not introduce a new external database.
**Acceptance Criteria:** A saved `PolicyVersion` can be retrieved and listed correctly.
**Verification:** Save two versions and confirm both are returned by the list function.

### Task 3.2 — Compliance Result Store
- [ ] **Goal:** Store past compliance results so citations can be retrieved later.
**Dependencies:** Task 2.2, Task 2.5.
**Work:** Implement `app/services/result_store.py` with functions to save a `ComplianceResult` by ID and retrieve it by ID.
**Acceptance Criteria:** A saved result can be retrieved by its ID; a missing ID returns a clear "not found" signal.
**Verification:** Save a result, retrieve it by ID, and confirm the data matches.

---

## Phase 4 — Policy Document Ingestion

**Purpose:** Implement the ingestion pipeline from Technical Specification Section 6: **Upload → Load → Extract → Chunk → Embed → Store**.

### Task 4.1 — File Upload Handling
- [ ] **Goal:** Accept an uploaded policy PDF and effective date.
**Dependencies:** Task 2.3.
**Work:** Implement the file-receiving logic (used later by the upload endpoint) that validates the file is present and is a PDF, and that `effective_date` is provided.
**Acceptance Criteria:** Non-PDF files are rejected; missing `effective_date` is rejected.
**Verification:** Test with a valid PDF, a non-PDF file, and a missing date.

### Task 4.2 — PDF Loading and Text Extraction
- [ ] **Goal:** Extract raw text from an uploaded PDF.
**Dependencies:** Task 4.1.
**Work:** Implement `app/ingestion/document_loader.py` using a LangChain PDF loader to extract text.
**Acceptance Criteria:** Given a sample PDF, readable text is extracted.
**Verification:** Run extraction on a sample policy PDF and inspect the output text.

### Task 4.3 — Text Chunking
- [ ] **Goal:** Split extracted text into chunks.
**Dependencies:** Task 4.2.
**Work:** Implement `app/ingestion/chunker.py` using LangChain's recursive character text splitter, with the starting chunk size (~1000 characters) and overlap (~150 characters) from Technical Specification Section 6.
**Acceptance Criteria:** A sample document produces multiple non-empty, reasonably sized chunks.
**Verification:** Run the chunker on extracted text and inspect chunk count and sizes.

### Task 4.4 — Chunk Metadata Creation
- [ ] **Goal:** Attach metadata to each chunk.
**Dependencies:** Task 4.3, Task 2.4.
**Work:** For each chunk, generate a `PolicyChunkMetadata` record (`chunk_id`, `version_id`, `source_document`, `section_reference` if identifiable, `text`).
**Acceptance Criteria:** Every chunk has complete, correctly populated metadata.
**Verification:** Inspect metadata for a sample set of chunks.

### Task 4.5 — Embedding Generation
- [ ] **Goal:** Convert chunks into vector embeddings.
**Dependencies:** Task 4.3, Task 1.4.
**Work:** Implement `app/ingestion/embedder.py` calling the configured embedding model/service (Technical Specification Section 7) for a batch of chunk texts.
**Acceptance Criteria:** Each chunk produces an embedding vector of the expected dimension.
**Verification:** Generate embeddings for sample chunks and confirm vector length matches the configured embedding model.

### Task 4.6 — Pinecone Connection Setup
- [ ] **Goal:** Establish a working Pinecone client and index connection.
**Dependencies:** Task 1.4.
**Work:** Implement `app/services/pinecone_client.py` to connect to Pinecone using configuration values, and confirm/create the index with the correct dimension.
**Acceptance Criteria:** The client connects successfully and the index dimension matches the embedding model's output.
**Verification:** Connect to Pinecone in a test run and confirm no connection errors.

### Task 4.7 — Vector Upsert
- [ ] **Goal:** Store chunk embeddings and metadata in Pinecone.
**Dependencies:** Task 4.4, Task 4.5, Task 4.6.
**Work:** Implement the upsert logic to write each chunk's embedding and metadata into Pinecone, using `chunk_id` as the record ID.
**Acceptance Criteria:** All chunks from a sample document are stored and queryable in Pinecone.
**Verification:** After upserting, query Pinecone directly and confirm the expected number of vectors exist.

### Task 4.8 — Ingestion Service Orchestration
- [ ] **Goal:** Combine Tasks 4.1–4.7 into a single ingestion flow.
**Dependencies:** Tasks 4.1–4.7, Task 3.1.
**Work:** Implement `app/ingestion/ingestion_service.py` to run the full Upload → Load → Extract → Chunk → Embed → Store pipeline, and save the resulting `PolicyVersion` record via the policy metadata store.
**Acceptance Criteria:** Given a sample PDF and effective date, the full pipeline runs end-to-end and produces searchable vectors plus a stored policy version record.
**Verification:** Run the full ingestion service on a sample policy PDF and confirm both Pinecone and the policy metadata store reflect the new version.

---

## Phase 5 — Policy Retrieval

**Purpose:** Implement retrieval as defined in Technical Specification Section 8.

### Task 5.1 — Retrieval Query Construction
- [ ] **Goal:** Build a retrieval query from an expense claim.
**Dependencies:** Task 2.1.
**Work:** Implement query text construction from `category` and `description`, in `app/retrieval/retriever.py`.
**Acceptance Criteria:** Given a sample expense claim, a non-empty query string is produced.
**Verification:** Test with several sample expense claims.

### Task 5.2 — Query Embedding
- [ ] **Goal:** Embed the retrieval query.
**Dependencies:** Task 5.1, Task 4.5.
**Work:** Reuse the embedding logic from Task 4.5 to embed the query text.
**Acceptance Criteria:** The query embedding has the same dimension as stored chunk embeddings.
**Verification:** Compare embedding dimensions between a query and a stored chunk.

### Task 5.3 — Pinecone Similarity Search with Version Filtering
- [ ] **Goal:** Retrieve relevant chunks for the applicable policy version only.
**Dependencies:** Task 5.2, Task 4.7.
**Work:** Implement similarity search against Pinecone, filtered by `version_id`, returning the top-k matches (starting `top-k = 5`, per Technical Specification Section 8).
**Acceptance Criteria:** Results only include chunks from the specified `version_id`; no more than `top-k` chunks are returned.
**Verification:** Query with a known `version_id` and confirm no chunks from other versions appear.

### Task 5.4 — No-Evidence Handling
- [ ] **Goal:** Handle cases where retrieval finds nothing useful.
**Dependencies:** Task 5.3.
**Work:** Detect empty or low-relevance retrieval results and signal this clearly to the calling component (to be used later by the agent, Phase 7, to produce `policy_silent`).
**Acceptance Criteria:** A query with no matching policy content returns a clear "no evidence" signal rather than an error or an empty silent failure.
**Verification:** Query against a policy version with unrelated content and confirm the no-evidence signal is returned.

---

## Phase 6 — Policy Version Selection

**Purpose:** Implement the deterministic effective-date logic from Technical Specification Section 9.

### Task 6.1 — Version Selection Logic
- [ ] **Goal:** Select the correct policy version for a given expense date.
**Dependencies:** Task 3.1.
**Work:** Implement `app/retrieval/version_selector.py`: find all versions with `effective_date <= expense_date`, select the one with the latest `effective_date`; if none qualify, signal "no applicable version"; apply the same-date tie-break rule from Technical Specification Section 9.
**Acceptance Criteria and Tests:**
- Exact effective-date match → that version is selected.
- Expense date between two versions → the earlier, still-applicable version is selected.
- Expense date before all stored versions → "no applicable version" is signaled.
- Multiple versions exist → the correct one is selected based on the latest qualifying effective date.
- Two versions share the same effective date → the tie-break rule is applied consistently.
**Verification:** Run each of the five scenarios above against a small set of test policy versions and confirm the expected version (or "no applicable version" signal) is returned.

---

## Phase 7 — AI Compliance Agent

**Purpose:** Implement the agent from Technical Specification Section 10, using the OpenAI Agents SDK.

### Task 7.1 — Agent and Model Configuration
- [ ] **Goal:** Set up the base agent and its model connection.
**Dependencies:** Task 1.4.
**Work:** Implement `app/agent/compliance_agent.py`, configuring the LLM connection using settings from Task 1.4.
**Acceptance Criteria:** The agent can be instantiated without errors.
**Verification:** Instantiate the agent in a test script.

### Task 7.2 — Agent Instructions
- [ ] **Goal:** Write instructions enforcing the rules from Technical Specification Section 10.
**Dependencies:** Task 7.1.
**Work:** Write agent instructions that require: using only retrieved policy evidence; never using general knowledge to invent rules; returning `policy_silent` when evidence doesn't address the case; always citing a retrieved chunk for a compliance verdict.
**Acceptance Criteria:** Instructions explicitly state all four rules above.
**Verification:** Review the instructions text against Technical Specification Section 10.

### Task 7.3 — Structured Output Wiring
- [ ] **Goal:** Make the agent return a `ComplianceResult`.
**Dependencies:** Task 7.1, Task 2.2.
**Work:** Set `output_type=ComplianceResult` on the agent.
**Acceptance Criteria:** The agent's `final_output` is a `ComplianceResult` instance, not raw text.
**Verification:** Run the agent on a sample input and confirm the output type.

### Task 7.4 — Agent Invocation with Expense and Retrieved Context
- [ ] **Goal:** Feed the agent an expense claim and its retrieved policy chunks.
**Dependencies:** Task 7.3, Task 5.4, Task 6.1.
**Work:** Implement the call that passes the expense claim and retrieved chunk text/metadata into the agent's input.
**Acceptance Criteria:** Given a sample expense and retrieved chunks, the agent produces a status, explanation, and (when applicable) a citation drawn from the retrieved chunks.
**Verification:** Run the agent with a sample compliant case, a non-compliant case, and a no-evidence case; confirm the outputs are reasonable and match the expected status pattern.

---

## Phase 8 — Output Guardrail

**Purpose:** Implement the citation-enforcement guardrail from Technical Specification Section 13.

### Task 8.1 — Guardrail Implementation
- [ ] **Goal:** Validate the agent's structured result before it can be returned.
**Dependencies:** Task 7.3.
**Work:** Implement `app/agent/output_guardrail.py` as an output guardrail checking: valid status value; citation present and non-empty for `compliant`/`non_compliant`/`needs_approval`; structural validity of the result. On failure, produce a result with `needs_human_review: true` and a `review_reason`.
**Acceptance Criteria:** A verdict without a citation never passes the guardrail unchanged.
**Verification:** Feed the guardrail a valid result and an invalid (no-citation) result, and confirm the correct behavior for each.

### Task 8.2 — Guardrail Test Coverage
- [ ] **Goal:** Confirm the guardrail behaves correctly across all cases.
**Dependencies:** Task 8.1.
**Work:** Write tests for: valid compliant result, valid non-compliant result, valid approval result, valid policy-silent result (no citation required), missing citation, invalid/malformed structured output.
**Acceptance Criteria:** All six cases behave as defined in Technical Specification Section 13.
**Verification:** Run the test suite for this task and confirm all cases pass.

---

## Phase 9 — Compliance Service

**Purpose:** Connect all previously built components into the full flow described in `docs/ARCHITECTURE.md` Section 6.

### Task 9.1 — End-to-End Compliance Flow
- [ ] **Goal:** Implement the full flow: **Expense → Policy Version → Retrieval → Agent → Structured Result → Guardrail → Result Storage → Response.**
**Dependencies:** Task 6.1, Task 5.4, Task 7.4, Task 8.1, Task 3.2.
**Work:** Implement a compliance service function that: selects the applicable policy version; retrieves relevant chunks; invokes the agent; passes the result through the guardrail; saves the final result via the result store; returns the final `ComplianceResult`.
**Acceptance Criteria:** Given a sample expense claim, the service returns a complete, guardrail-checked, stored `ComplianceResult`.
**Verification:** Run the service against sample compliant, non-compliant, needs-approval, and policy-silent scenarios, and confirm each stage of the flow executes correctly.

---

## Phase 10 — API Endpoints

**Purpose:** Expose the four required endpoints from Technical Specification Section 5.

### Task 10.1 — `POST /policy/upload`
- [ ] **Goal:** Expose policy ingestion via the API.
**Dependencies:** Task 4.8.
**Work:** Implement the route in `app/api/policy_routes.py`, accepting the file and `effective_date`, calling the ingestion service, and returning the response shape from Technical Specification Section 5.
**Acceptance Criteria:** A valid upload returns a success response with `version_id` and `chunks_created`; invalid input returns the documented error codes (`400`, `415`, `500`).
**Verification:** Call the endpoint with a valid PDF and with invalid inputs; confirm responses match the specification.

### Task 10.2 — `POST /compliance/check`
- [ ] **Goal:** Expose expense checking via the API.
**Dependencies:** Task 9.1.
**Work:** Implement the route in `app/api/compliance_routes.py`, accepting an `ExpenseClaim`, calling the compliance service, and returning the response shape from Technical Specification Section 5.
**Acceptance Criteria:** Valid requests return a structured result; invalid input returns `400`; no applicable policy version returns `409`.
**Verification:** Call the endpoint with valid and invalid expense claims, and with a date outside all policy versions.

### Task 10.3 — `GET /compliance/{id}/clause`
- [ ] **Goal:** Expose citation lookup via the API.
**Dependencies:** Task 3.2, Task 10.2.
**Work:** Implement the route to look up a stored `ComplianceResult` by ID and return its citation, or `404` if not found or if no citation exists.
**Acceptance Criteria:** A valid ID with a citation returns the citation; a missing ID or a citation-less result (`policy_silent`) returns `404` with a clear message.
**Verification:** Call the endpoint with a valid compliant result ID and with a policy-silent result ID.

### Task 10.4 — `GET /policy/versions`
- [ ] **Goal:** Expose the list of policy versions via the API.
**Dependencies:** Task 3.1.
**Work:** Implement the route to list all stored `PolicyVersion` records.
**Acceptance Criteria:** Returns all uploaded versions with `version_id`, `effective_date`, and `source_document`.
**Verification:** Upload two policy versions and confirm both appear in the response.

---

## Phase 11 — Error Handling and Logging

**Purpose:** Implement Technical Specification Sections 14 and 15 consistently across the service.

### Task 11.1 — Centralized Error Handling
- [ ] **Goal:** Ensure all error categories from Technical Specification Section 14 are handled consistently.
**Dependencies:** Phase 10 complete.
**Work:** Implement shared error types/handlers in `app/utils/errors.py` and wire them into the API routes, covering: invalid request, missing fields, invalid file, processing failure, embedding failure, Pinecone failure, no applicable version, no evidence, invalid agent output, missing citation, internal error.
**Acceptance Criteria:** Each error category returns the HTTP status defined in Technical Specification Section 14; client-facing messages are safe and generic where required.
**Verification:** Trigger each error category (where feasible) and confirm the correct status and message.

### Task 11.2 — Logging
- [ ] **Goal:** Add logging per Technical Specification Section 15.
**Dependencies:** Task 11.1.
**Work:** Implement `app/utils/logging.py` and add log statements for: upload success/failure, version processed, retrieval success/failure and chunk count, compliance status per check, guardrail failures, unexpected errors.
**Acceptance Criteria:** Logs never include API keys, passwords, or raw secret values.
**Verification:** Run through the main flows and inspect logs for completeness and absence of sensitive data.

---

## Phase 12 — Testing

**Purpose:** Implement the testing plan from Technical Specification Section 17.

### Task 12.1 — Unit Tests
- [ ] **Goal:** Cover individual components in isolation.
**Dependencies:** Corresponding component tasks in Phases 2–8.
**Work:** Add unit tests for models, chunking, version selection, and the guardrail.
**Acceptance Criteria:** Unit tests cover the scenarios listed in Technical Specification Section 17 for ingestion, versioning, and the guardrail.
**Verification:** Run the unit test suite and confirm all tests pass.

### Task 12.2 — Component/Integration Tests
- [ ] **Goal:** Cover multi-step flows within a single area.
**Dependencies:** Phase 4, Phase 5, Phase 7, Phase 8.
**Work:** Add tests for the full ingestion pipeline, the full retrieval flow, and agent + guardrail together.
**Acceptance Criteria:** Each integration test reflects a scenario from Technical Specification Section 17.
**Verification:** Run the integration test suite and confirm all tests pass.

### Task 12.3 — API Tests
- [ ] **Goal:** Cover all four endpoints.
**Dependencies:** Phase 10, Phase 11.
**Work:** Add tests for successful and error responses for each of the four endpoints.
**Acceptance Criteria:** All documented success and error responses from Technical Specification Section 5 are tested.
**Verification:** Run the API test suite and confirm all tests pass.

### Task 12.4 — End-to-End Test
- [ ] **Goal:** Confirm the full system works together.
**Dependencies:** All prior phases.
**Work:** Write a test that uploads a sample policy, submits a compliant expense, a non-compliant expense, an approval-required expense, and an out-of-policy expense, and confirms the correct structured result and citation behavior for each.
**Acceptance Criteria:** All four scenarios behave as defined in the PRD and Technical Specification.
**Verification:** Run the end-to-end test and confirm all assertions pass.

---

## Phase 13 — Final Validation

**Purpose:** Confirm the complete project meets the PRD, Architecture, and Technical Specification before considering it done.

**Final Checklist:**
- [ ] Policy upload works and produces searchable vectors in Pinecone.
- [ ] `GET /policy/versions` correctly lists uploaded versions.
- [ ] The correct policy version is selected based on `expense_date` in all tested scenarios.
- [ ] Compliance checks are evaluated using retrieved policy evidence, not general knowledge.
- [ ] Every response from `POST /compliance/check` is a structured result matching `ComplianceResult`.
- [ ] Every `compliant`, `non_compliant`, and `needs_approval` result includes a verbatim citation.
- [ ] Policy silence is returned explicitly and correctly when the policy doesn't address a case.
- [ ] Human review cases (`needs_human_review: true`) are produced correctly for approval-required, insufficient-evidence, and guardrail-failure situations.
- [ ] All four required API endpoints work as specified, with correct error handling.
- [ ] The full test suite passes.
- [ ] No secrets exist in source code or Git history.
- [ ] `docs/PRD.md`, `docs/ARCHITECTURE.md`, and `docs/TECHNICAL_SPECIFICATION.md` remain accurate to the final implementation.

---

## Dependency Order Overview

```
Phase 1  Foundation
  → Phase 2  Data Models
    → Phase 3  Storage
      → Phase 4  Ingestion
        → Phase 5  Retrieval
          → Phase 6  Version Selection
            → Phase 7  AI Agent
              → Phase 8  Output Guardrail
                → Phase 9  Compliance Service
                  → Phase 10  API Endpoints
                    → Phase 11  Error Handling & Logging
                      → Phase 12  Testing
                        → Phase 13  Final Validation
```

Each phase depends only on phases above it. Within a phase, tasks are ordered so earlier tasks unblock later ones.

**External API configuration required before implementation can proceed past Phase 1:**
- LLM API access (Technical Specification Section 3, `LLM_API_KEY`)
- Pinecone account and API key (`PINECONE_API_KEY`, `PINECONE_INDEX_NAME`)
- Embedding service access (`EMBEDDING_API_KEY`, `EMBEDDING_MODEL_NAME`)

---

## OpenCode Usage Guidance

This plan is designed to be worked through with an AI coding agent (OpenCode) one task at a time:

- Give OpenCode **one task at a time**, referencing the relevant section of `docs/TECHNICAL_SPECIFICATION.md` so it has the exact technical requirement, not just the task summary.
- After each task, **inspect the changed files** to confirm only the files relevant to that task were touched.
- **Run the relevant tests** after each meaningful task, not just at the end of a phase.
- Confirm the task's **acceptance criteria** are met before moving to the next task.
- If OpenCode makes an **incorrect architectural decision** (e.g., introduces a new database, changes an endpoint contract, or deviates from the Technical Specification), **stop and correct it immediately** rather than continuing on top of it.
- Do not batch multiple unrelated tasks into a single OpenCode session — small, verifiable steps are easier to review and correct.

Actual OpenCode prompts are not included in this document; they will be written individually during implementation, one per task.
