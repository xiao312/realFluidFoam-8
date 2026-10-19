# realFluidFoam replication

Read `replication/README.md` before environment, case, or validation work.
Read `replication/docs/writing.md` before project reports or work-log entries.

- Preserve the upstream solver until a separate, reviewed change is needed.
- Use Conventional Commits: `type(scope): description`.
- Pin source revisions and container digests. Record all build and run inputs.
- Keep site paths and credentials in ignored `*.local.json` files.
- Run the read-only plan before remote preparation or job submission.
- All controlled writes belong inside the configured project root. This includes
  HOME, temporary files, caches, build outputs, logs, and scheduler output.
- Use Slurm for compilation and simulation. Login nodes perform short control work.
- Keep raw output outside Git. Commit small evidence summaries and input manifests.
- Record failures. A build or help check does not establish scientific validation.
- Do not modify unrelated jobs, software, or historical project directories.
- All new realFluidFoam-based simulation runs must start from the original time-0
  initialization. Never continue from a saved intermediate state, use latestTime,
  or relabel saved fields as time 0 unless the owner explicitly authorizes that
  particular restart. Record the authorization with the run inputs.

Windows checkouts use sparse checkout for replication files. Build from a full
Git checkout on a case-sensitive Linux filesystem; upstream has case collisions.
