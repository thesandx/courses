# 🎯 PDE Mock Exam — Interactive Practice

A self-contained, browser-based mock exam with **110 original practice questions**
covering every domain of the Google Cloud **Professional Data Engineer** certification.

> These are original questions written for this course in the style of the real
> exam (scenario → best-service/best-practice choice). They are **not** copied from
> the actual exam or from any question-dump site.

## How to Use

Just open the exam in your browser — no server, no build step:

```bash
# from the repo root
open gcp_data_engineer_mastery/mock_exam/index.html        # macOS
xdg-open gcp_data_engineer_mastery/mock_exam/index.html    # Linux
start gcp_data_engineer_mastery\mock_exam\index.html       # Windows
```

## Features

- **Instant feedback** — pick an answer and immediately see whether you were right,
  which option was correct, and a full **explanation** of the reasoning.
- **Question palette** — jump to any question; answered ones are color-coded
  green (correct) / red (incorrect).
- **Domain filter** — drill just BigQuery, just Dataflow, etc.
- **Score tracking & results** — live score in the header, plus a final results
  screen with a **per-domain breakdown** so you know what to restudy
  (the real exam pass mark is ≈70%).
- **Progress is saved** — answers persist in your browser (localStorage), so you
  can close the tab and resume later. "Reset exam" wipes it for a fresh attempt.
- **Keyboard shortcuts** — `←`/`→` to navigate, `A`–`D` to answer.

## Coverage (110 questions)

| Domain | Questions |
|---|---|
| BigQuery (fundamentals, scale, cost, security) | 20 |
| Dataflow & Apache Beam | 14 |
| Databases (Spanner, Bigtable, Cloud SQL, Firestore, Memorystore) | 14 |
| Pub/Sub & Streaming | 12 |
| Security & Governance (IAM, CMEK, DLP, VPC-SC, Dataplex) | 10 |
| Storage & Data Lakes | 8 |
| Dataproc & Hadoop migration | 8 |
| Orchestration & Integration (Composer, Data Fusion, Datastream, DTS) | 8 |
| ML & Analytics (BigQuery ML, Vertex AI, Looker) | 8 |
| Reliability, Monitoring & Cost | 8 |

## Suggested Study Loop

1. Finish (or skim) the course modules.
2. Take the full 110-question exam untimed; read every explanation — including
   for questions you got right.
3. Check the per-domain breakdown; re-read the weakest modules' **Exam Focus** tables.
4. Retake filtered to your weak domains until you're consistently above 80%.
