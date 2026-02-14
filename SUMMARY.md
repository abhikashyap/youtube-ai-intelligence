
# System Summary – Full Roadmap & Future Scope

This document describes the full long-term architecture beyond Pipeline 1.

---

# Phase 1 – Metadata Intelligence (Current)

Fast, lightweight pipeline using:

- YouTube metadata only
- LLM classification on title + description
- Config-driven scoring
- Daily ranking generation

Purpose:
Quick signal extraction with minimal compute cost.

---

# Phase 2 – Transcript Extraction Pipeline

A separate, independent Airflow DAG.

## Transcript Bronze

