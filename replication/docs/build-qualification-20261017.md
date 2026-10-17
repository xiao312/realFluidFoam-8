# Solver build on 2026-10-17

The full OF8 solver build passed on SCNet. Scientific validation remains separate.

| Item | Evidence |
| --- | --- |
| Source | `b1153ea9c64b9abf55f7be6c488549024c081279` |
| Upstream solver baseline | `48506de20ce67f35279c5347b09dcd86865a4c39` |
| Successful job | `124657926`, COMPLETED, exit 0:0 |
| Resources | 16 CPUs, one-hour limit; elapsed 17 min 34 s |
| Slurm batch MaxRSS | 9,546,560 KiB |
| Runtime SIF SHA256 | `7d4e96e0b1a97a0b361cbaf808b6242fa0c576e5ee2a27cd6a9a514c59cb529e` |
| Source archive SHA256 | `60933848d8f5974da30b5ed465536ac2399e9a52233d5a1c9cad97d7b0df543c` |
| Evidence archive | `results/build-124657926-evidence.tar.gz` under the configured trial |
| Evidence SHA256 | `81c935ff63a0a93273221eb5b7861f90ae671dc21134ae9b3054bae8c0b0dc96` |

The receipt includes the full build log, environment, product hashes, image hash,
and dependency listings. `reactingFoam`, `realFluidFoam`, and
`realFluidReactingFoam` passed executable help checks with no unresolved shared
libraries. `realFluidFoam` resolved the isolated build's custom `libspecie.so`.
Subsequent validation checks the reacting solver's resolution independently.
Warnings about deprecated copy assignment remain in upstream code; they did not
prevent compilation. No solver physics was changed.

Repeat using the contained build recipe in `environment/README.md`:
`submit.sh plan ROOT IMAGE RELEASE build PARTITION`, then the same with `apply`.
The job writes only inside the configured trial, with separate source, build,
home, temporary, cache and log directories. The successful runtime is the staged
directory container described in the 2026-10-16 environment record.

## Failed attempt and staging correction

Job `124657636` failed before compilation with `$'\r': command not found` and
invalid Make-directory paths. On this Windows host, `git archive` inherited
`core.autocrlf=true`, changing 1,184 archived files despite LF Git blobs.
The corrected export uses `git -c core.autocrlf=false archive`. The new
`verify_archive.py` checks every archived file or symlink against its Git blob.
Both local and remote corrected-archive hashes matched. Preserve the failed job;
do not repair immutable source releases in place.

A Git Bash replay did not faithfully reproduce the Linux CRLF execution failure;
the original failed Slurm job is the runtime evidence. The archive/blob check is
the direct regression check for this staging defect.

## Next qualification

Validation source `a89c40520f22e914f3b0e47ffa3bbd7047d9f488` reuses this build's
products read-only, verifying their hashes before execution. Property job
`124659480` was submitted with two CPUs and a 20-minute limit. Its numerical
result and NIST agreement must be recorded separately from this build receipt.
