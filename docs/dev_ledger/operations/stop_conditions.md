# Stop Conditions

Codex should continue autonomously within approved scope unless one of these occurs.

Stop and ask the user when:

- acceptance criteria conflict
- a new dependency is required
- a live API, secret, credential, or external service is required
- roadmap scope or order must change
- tests fail after 2 repair attempts
- the implementation would affect more than the approved scope
- a destructive tracked-file operation is needed
- push or merge is requested or required
- a user/business/product decision is required

If none of these conditions applies, Codex should make a reasonable local decision, keep scope narrow, validate, and continue.

