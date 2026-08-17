# Expense Policy Compliance Checker — Product Requirements Document

## 1. Product Overview

**Product name:** Expense Policy Compliance Checker

Expense Policy Compliance Checker is a backend service that checks whether an employee's expense claim follows company policy. An employee (or the finance system) sends in the details of an expense, and the service returns a structured decision that says whether the expense is compliant, non-compliant, needs approval, or is not covered by the policy at all.

The system works by storing the company's expense policy documents in a searchable form, finding the parts of the policy relevant to a given expense, and using an AI agent to compare the expense against that policy text. Every decision must be backed by the actual policy wording — the system never guesses.

**Main technologies (high level):**
- An AI agent (built with the OpenAI Agents SDK) that reasons over retrieved policy text and produces a structured verdict
- **LangChain** for processing policy documents (loading, splitting into chunks, creating embeddings)
- **Pinecone**, a vector database, for storing and searching policy content
- **FastAPI** for exposing the system as a web service

**Is it a chatbot?** No. This is a **structured API service**, not a chatbot. There is no open-ended conversation. An expense claim goes in, and a structured, typed result comes out.

---

## 2. Problem Statement

Employees regularly submit expenses without knowing whether they are actually allowed under company policy. Company expense policies are often long documents (tens of pages) covering categories, spending limits, approval rules, and exceptions.

This creates real problems:

- Employees guess whether an expense is claimable, and often guess wrong.
- Finance staff spend significant time manually re-checking claims against the policy document.
- Rejected claims waste time for both the employee and finance.
- Companies often have more than one version of their policy over time, and using the wrong version leads to incorrect decisions.
- Nobody has time to read a 40-page policy document every time a question comes up.

The result is slow, inconsistent, and manual expense review. A service that checks claims against the actual policy text — and clearly explains *why* — solves this problem directly.

---

## 3. Product Goal

**Main goal:** Automatically check whether an expense claim complies with the company's expense policy, using the actual policy document as evidence, and return a clear, structured, and trustworthy result.

**Objectives:**

1. Check an expense claim against the correct, currently applicable company policy.
2. Retrieve the specific part of the policy relevant to the expense being checked.
3. Produce a structured compliance result rather than free-form text.
4. Always show the exact policy clause that supports the decision.
5. Correctly handle multiple policy versions with different effective dates.
6. Never produce a compliance decision that isn't backed by policy evidence — if the policy doesn't address the situation, say so honestly instead of guessing.

---

## 4. Target Users

| User | What they need from the system |
|---|---|
| **Employees** submitting expenses | A quick, reliable answer on whether an expense is claimable, with a clear reason. |
| **Finance / accounting staff** | A tool that pre-checks claims against policy so they can focus their time on genuinely unclear or flagged cases. |
| **Policy administrators** | A way to upload and manage expense policy documents and their versions, so the system always evaluates claims against the right policy. |

---

## 5. Product Workflow

1. An administrator uploads the company's expense policy document.
2. The policy document is processed and stored so it can be searched later (this is the retrieval preparation step).
3. An employee (or a finance system) submits an expense claim for checking.
4. The system identifies which parts of the policy are relevant to that expense.
5. The relevant policy content is retrieved from storage.
6. The AI agent evaluates the expense using only the retrieved policy content.
7. The system produces a structured compliance result.
8. The result includes the exact policy clause that supports the decision.
9. If the policy does not clearly address the expense, the system explicitly returns **"Policy is silent on this"** instead of guessing, or flags the case for human review when appropriate.

---

## 6. Core Features

### Policy Ingestion
Company expense policy documents can be uploaded and prepared for retrieval (processed and stored so the relevant sections can be found later).

### Policy Retrieval
When an expense is checked, the system finds and retrieves the specific policy sections relevant to that expense.

### Expense Compliance Checking
An expense claim (category, amount, and relevant details) is checked against the applicable policy.

### Structured Compliance Result
The system always returns a structured, typed result — not free-form chatbot text.

### Policy Citation
Every compliance verdict must include the relevant policy clause that supports it, returned in a verbatim (word-for-word) form.

### Policy Versioning
The system supports multiple versions of the expense policy, not just one.

### Effective Dates
Each policy version has an effective date. The system must select and use the policy version that actually applies, rather than always using the newest or the oldest one.

### Policy Silence
If the policy does not cover the situation, the system must explicitly say **"Policy is silent on this"** rather than inventing a verdict.

### Human Review / Approval
Claims that require sign-off under the policy, or that cannot be safely decided automatically, are identified as needing human review or approval.

---

## 7. User Inputs

### Policy Input
When uploading a company policy, the system expects:
- The policy document itself (e.g., a PDF)
- Its effective date (so the system knows which version applies when)

> **Assumption:** The exact list of metadata fields (such as document title or department) is an implementation detail to be defined in the Technical Specification. Only the document and effective date are treated as confirmed requirements here, since policy versioning and effective dates are explicitly required by the source.

### Expense Claim Input
To check an expense, the system needs the details of the claim, including at minimum:
- Expense category (e.g., meals, travel, lodging)
- Amount
- Other relevant details about the expense (e.g., description, date, or location, as needed to match it against policy)

> **Assumption:** The precise, complete schema for an expense claim is an implementation detail for the Technical Specification. This PRD confirms only that category and amount are required inputs, since these are the fields directly referenced by the source's example endpoint.

---

## 8. System Outputs

After checking an expense, the system returns a structured result containing:

- **Compliance status** — one of:
  - **Compliant** — the expense is allowed under policy
  - **Non-Compliant** — the expense is not allowed under policy
  - **Needs Approval / Human Review** — the policy requires sign-off, or the case cannot be safely auto-decided
  - **Policy is Silent** — the policy does not address this situation
- **Explanation** — a short, plain-language reason for the verdict
- **Policy citation** — the verbatim policy clause supporting the verdict (not required when the outcome is "Policy is Silent," since there is no supporting clause in that case)
- **Policy version** — which policy version was used to reach the decision

---

## 9. AI Agent Responsibilities

The AI agent is responsible for:

- Using the policy content retrieved from Pinecone as its evidence
- Comparing the expense claim against the applicable policy
- Producing a structured, typed result
- Explaining its decision in plain language
- Referencing the exact policy clause that supports its decision

**The AI agent must not:**

- Invent or assume policy rules that are not present in the retrieved policy text
- Return a compliance verdict without a supporting policy citation
- Force a verdict (compliant or non-compliant) when the policy is actually silent on the situation
- Behave like an open-ended chatbot or hold a conversation outside of checking a specific claim

---

## 10. RAG, LangChain and Pinecone

### RAG (Retrieval-Augmented Generation)
RAG means the AI agent doesn't rely on what it "remembers" — it first retrieves the actual, relevant text from the company's policy documents, and then reasons using that retrieved text. This is needed here because compliance decisions must be based on the real, current policy wording, not a general guess.

### LangChain
LangChain is used to prepare policy documents for retrieval. This includes loading uploaded documents, splitting long policy text into smaller chunks, and generating embeddings (numerical representations of text) for each chunk so they can be searched later.

### Pinecone
Pinecone is a vector database. It stores the embedded policy chunks and allows the system to quickly find the pieces of policy text most relevant to a given expense claim. A vector database is used here because policy documents are long, and searching by meaning (not just keyword matching) is needed to find the right clause.

### Why not rely only on the LLM?
An AI model asked to answer from general knowledge does not know this specific company's policy, and it may confidently produce an answer that sounds correct but isn't backed by the real document. Because compliance decisions have real consequences (approved or rejected expenses), every decision must be grounded in the company's actual policy text — which is exactly what retrieval provides.

---

## 11. Policy Version and Effective Date Handling

- A company may have more than one version of its expense policy over time.
- Each policy version has an effective date.
- When checking an expense, the system must use the policy version that was actually in effect for that expense — not automatically the newest version.
- The system must not evaluate an expense against an outdated policy version when a newer, applicable version exists.

---

## 12. Compliance Decision Rules

| Situation | System Behavior |
|---|---|
| Policy clearly allows the expense | Return **Compliant**, with the supporting policy clause cited. |
| Policy clearly does not allow the expense | Return **Non-Compliant**, with the supporting policy clause cited. |
| Policy requires sign-off for this type of expense | Return **Needs Approval / Human Review**, with the supporting policy clause cited. |
| Policy does not address the situation at all | Return **"Policy is silent on this"** instead of guessing a verdict. |
| Retrieved policy evidence is insufficient to decide confidently | Do not create an unsupported verdict. Flag the case for human review. |

---

## 13. Citation and Evidence Requirement

**No compliance verdict should be returned without supporting policy evidence.**

This means:

- Every **Compliant**, **Non-Compliant**, or **Needs Approval** verdict must include the exact policy clause used to reach that decision, returned in verbatim (word-for-word) form.
- The citation must clearly identify which part of the policy was used, so the employee or finance reviewer can check it themselves.
- If there is no relevant policy clause to cite, the system must not produce a compliance verdict — it must return **"Policy is silent on this"** instead.

An output guardrail enforces this rule at the system level: a verdict without a citation should never be allowed to reach the user.

---

## 14. Human Review

A case is flagged for human review when:

- The policy does not provide enough information to confidently decide.
- The policy is silent on the situation and further judgment is needed.
- The retrieved evidence is insufficient to support a confident verdict.
- The policy itself states that this type of expense requires approval.

Human review is a **designed, expected part of the product** — not a failure of the system. Routing uncertain or approval-required cases to a person is what makes the automated results trustworthy.

---

## 15. API Requirements

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/policy/upload` | Upload a company expense policy document. |
| `POST` | `/compliance/check` | Check an expense claim against the applicable policy. |
| `GET` | `/compliance/{id}/clause` | Retrieve the policy clause that supports a given compliance result. |
| `GET` | `/policy/versions` | View the available policy versions and their effective dates. |

Detailed request and response schemas are out of scope for this PRD and will be defined in the Technical Specification.

---

## 16. Scope

### In Scope
- Uploading and storing company expense policy documents
- Supporting multiple policy versions with effective dates
- Retrieving relevant policy content for a given expense claim
- Checking an expense claim against the applicable policy
- Returning a structured compliance result (Compliant / Non-Compliant / Needs Approval / Policy is Silent)
- Citing the verbatim policy clause behind every compliance verdict
- Flagging cases for human review when evidence is insufficient or approval is required
- Exposing the system as an API service with the endpoints listed in Section 15

### Out of Scope
- A full accounting or bookkeeping system
- Payment processing or reimbursement/payout of approved expenses
- A payroll system
- Automatic approval or rejection actions outside of producing a compliance verdict
- Open-ended chatbot conversation
- General financial or investment advice unrelated to expense policy compliance

---

## 17. Non-Functional Requirements

- **Reliability:** The service should consistently return a valid, structured result for every valid request.
- **Consistent structured output:** Responses must always follow the defined result structure (status, explanation, citation, version), not free-form text.
- **Traceable evidence:** Every compliance verdict must be traceable back to a specific, retrievable policy clause.
- **Security:** Uploaded policy documents should be stored and accessed securely, since they may contain internal company information.
- **Reasonable response time:** The service should return a result within a reasonable time for a single expense check.
- **Maintainability:** The system should be structured so that new policy documents or versions can be added without changing how compliance checks work.
- **Error handling:** Invalid input (missing fields, unreadable documents, unsupported formats) should return clear, structured error responses rather than failing silently.

---

## 18. Success Criteria

- A company policy document can be uploaded and successfully processed for retrieval.
- Given an expense claim, the system retrieves the policy content relevant to it.
- The system checks the expense against the correct, applicable policy version.
- The result returned is structured, not free text.
- Every **Compliant**, **Non-Compliant**, or **Needs Approval** result includes a verbatim policy citation.
- When the policy does not cover a situation, the system returns **"Policy is silent on this"** instead of an invented verdict.
- The system correctly distinguishes between multiple policy versions using their effective dates.
- All four required API endpoints function as described.

---

## 19. Assumptions and Constraints

**Confirmed requirements (from the source project definition):**
- Retrieval-Augmented Generation (RAG) is required for this project.
- Pinecone is required as the vector database for storing and searching policy content.
- LangChain is required for document loading, splitting, and embedding of policy documents.
- The project must be built as an API/service, not an open-ended chatbot.
- Structured output is required for all compliance results.
- An output guardrail enforcing citation-backed verdicts is required.
- The four listed API endpoints are required at a high level.

**Assumptions (not explicitly detailed in the source, included only for readability):**
- The exact fields required when uploading a policy (beyond the document and its effective date) will be finalized in the Technical Specification.
- The exact fields required in an expense claim (beyond category and amount) will be finalized in the Technical Specification.
- Specific performance targets (e.g., exact response time limits) are not defined by the source and are left for later technical planning.
