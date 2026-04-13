---
name: github-review
description: Use when reviewing pull requests, summarizing repository changes, or preparing review feedback.
requiredMcpServers:
  - github
preferredTools:
  - github.list_pull_requests
  - github.get_pull_request
  - github.get_pull_request_files
resources:
  - checklist.md
---

# GitHub Review Skill

Use this skill when the user asks to review pull requests, summarize changes, or identify risks in repository updates.

## Workflow

1. Identify the target pull request or compare range from user context.
2. Fetch metadata, changed files, and relevant discussion.
3. Prioritize risks, regressions, and missing tests before style feedback.
4. Return a concise summary followed by actionable findings.

## Output Rules

- Put high-severity findings first.
- Reference concrete file paths and observed behaviors.
- Clearly separate confirmed issues from assumptions.
- If data is missing, request exactly what is needed.
