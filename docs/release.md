# Release and migration

Reviewed 2026-10-13 (America/New_York) against main
[`1b795ca4`](https://github.com/elong0527/yamaa/commit/1b795ca4), the current
[#1969](https://github.com/elong0527/yamaa/issues/1969) and
[#1973](https://github.com/elong0527/yamaa/issues/1973) gate records, retained
qualification records and the authenticated GitHub release listing. This is the
current narrative; qualification observations keep their own tested revisions.

The [final release handoff](release-handoff.md) reconciles every entry gate,
independently re-admitted rollback receipts, measured-source renewal and exact
package selection. Transition acceptance and the final package selection remain
pending there until all evidence gates pass.

## State

| State | Observed scope |
| --- | --- |
| Implemented and merged | Shared language execution; Python/R domain/check/define; runner conversion; legacy evaluator/API/probe and R/cdiscbuilder removal; coordinated Python/R/Cargo 0.4.0 source versions. The performance harness is merged through PR #2137; subsequent native dependency/guard, portable-math control and performance admission repairs are merged through PRs #2164-#2168. |
| Qualified at earlier revisions | Retained public-conformance ratchet: run 38416920074, attempt 1, source `2ba10418607933f92597f7c00ac363a3113a49db`; earlier rollback rehearsals below. Their results do not qualify current main or its 0.4.0 composition. |
| Capacity policy | The bounded default policy below is selected from actual installed Python/R frontier evidence; exact-head native renewal and final combined-main qualification remain separate gates. |
| Pending evidence/decisions | Final combined-main installed/numerical audit, complete performance campaign and item-10 budgets, item-11 transition acceptance and exact artifact handoff. |
| Published | [Python source release 0.3.0](https://github.com/elong0527/yamaa/releases/tag/yamaa-py-0.3.0), source `845a91ff`, published 2026-10-11, with no package assets. No shared 0.4.0 release is listed. Prior source-built Python rollback packages and the pre-cutover R 0.3.0 candidate remain unpublished drafts. |

PR [#2165](https://github.com/elong0527/yamaa/pull/2165) merged without a passing
exact-head installed matrix. Its main run
[38503400832](https://github.com/elong0527/yamaa/actions/runs/38503400832) began
after merge, and qualification run
[38503459253](https://github.com/elong0527/yamaa/actions/runs/38503459253) was
canceled. Neither satisfies the required pre-merge gate; no approved exception
superseded that requirement. Final combined-main acceptance remains pending.

Removal and version changes landed **before** final evidence-based item-10/item-11
acceptance. Planning removal in PR #2161 and math-record replacement in PR #2162
also preceded this consolidated guide. Record the actual chronology; completed
implementation, closed work packages and approved target policy do not imply
transition approval. [#2147](https://github.com/elong0527/yamaa/issues/2147) records
acceptance only after the remaining evidence passes. Publication/tagging/asset
replacement is a separate operation.

## Approved decisions

[#1973](https://github.com/elong0527/yamaa/issues/1973) records items 1-9 and 12-19
as decided. The [approval comment](https://github.com/elong0527/yamaa/issues/1973#issuecomment-6112883568)
and [original decision source](https://github.com/elong0527/yamaa/blob/43bb4437d9c0890ec7877ec7575a517c771a8147/rust/planning/maintainer-decisions.md)
retain provenance. Their current policy is:

- Retain Python `domain`/`check`/`define`, result/error types, version metadata and
  `read_odm`/`write_odm_parquet`; retain R equivalents including `yamaa_define`.
  Legacy evaluators, probes, resolved-spec/IO/authoring extensions and
  `cdiscbuilder` are retired. The style CLI remains private and native-backed.
- Keep Python `environment` keyword-only, wrong argument types as `TypeError`,
  R argument failures as `yamaa_argument_error`, and missing specifications as
  issue rows. Check returns issues, without a public resolved-spec producer.
- Preserve full signed-i64 values and separate missingness, lossless R
  `yamaa_int64_vector`/`yamaa_utf8_vector`, preserve-or-error conversions and
  JSON-text diagnostic context. No JSON callback request/reply protocol remains.
- Resolve resources from their original declaring file, with approved absolute
  and parent-relative local paths and no project-root fallback. Preserve snapshots,
  original failures, callback counts and producer-first publication order.
- Keep normative diagnostics registry-owned, including the reviewed
  `unsupported_operation` and `engine_rejected` null-requirement exceptions.
  Cut breaks remain finite/strictly ascending; signed-i64 predicate overflow,
  CSV empty-string refusal, greatest/least first-source ties and row-filter
  behavior follow the normative rules and independent expected truth.
- Use PortableLibmV1 and pinned libm 0.2.16. EXP/LN/POWER results, downstream
  predicates, conversions and saved bytes may differ from historical platform
  math. This promises neither universal correct rounding nor historical bit
  compatibility. Current independent goldens live in
  [portable_math.tsv](https://github.com/elong0527/yamaa/blob/main/rust/crates/yamaa-core/tests/fixtures/portable_math.tsv);
  final qualification still requires all nine assessments and exact comparison.
  The [original numerical decision](https://github.com/elong0527/yamaa/blob/43bb4437d9c0890ec7877ec7575a517c771a8147/rust/planning/1740-math-decision.md)
  and [witness report](https://github.com/elong0527/yamaa/blob/43bb4437d9c0890ec7877ec7575a517c771a8147/rust/qualification/math-decision-v1.json)
  remain in Git. Current goldens do not replay the retired accuracy-certificate
  tools or establish universal correctly rounded behavior.
- Qualify CPython 3.12/3.13/3.14 wheel and independent source builds on Linux
  x86_64, macOS arm64 and Windows x64 (18 tuples), plus R 4.6.1 source builds on
  the same hosts (three tuples), each with strict `R CMD check` **Status: OK**.
  Other runtimes/architectures, free-threaded Python, musl and R binary packages
  are outside this first release. R distribution starts with a staged GitHub
  source tarball; CRAN/r-universe are later work.
- Keep canonical Cargo locking and unchanged source-package copies. Runtime,
  contract, cache and resource identities use references/canonical forms/bytes;
  only packaging-tool lockfiles carry their own checksum fields.

These are target decisions, not qualification results. Host behavior and source
installation commands have one home in the
[Python](https://github.com/elong0527/yamaa/blob/main/python/README.md) and
[R](https://github.com/elong0527/yamaa/blob/main/R/yamaa/README.md) guides.

## Remaining gates and owners

The historical B01-B19 identifiers remain useful for reconciliation. Closed
implementation owners are not reopened; the following owners renew final evidence.

| Gate | Current disposition and acceptance owner |
| --- | --- |
| B01 - active conformance | 316 active of 318 authored cases, with two explicit historical exclusions; final 21-tuple admission: [#2145](https://github.com/elong0527/yamaa/issues/2145). |
| B02 - Python API | Shared facade merged; final signatures/results/arguments/helpers: #2145; export/archive reconciliation: [#2147](https://github.com/elong0527/yamaa/issues/2147). |
| B03 - R API/scalars | Approved i64/NUL/error/Define surface merged; renew installed ownership/conversions: #2145. |
| B04 - filesystem/platforms | Declaring-file paths and Windows controls merged; renew final installed source: #2145. |
| B05 - probe/JSON retirement | Removal merged; reconcile unique retired assertions and retained consumers: #2147. |
| B06 - route/environment selection | Unified composition merged; final full installed evidence: #2145. |
| B07 - producers | Orchestration merged; final port/callback/failure/publication order: #2145. |
| B08 - submission | Shared Define and registry ownership merged; final installed render/Save/default-version controls: #2145. |
| B09 - language | Language families merged; renew complete active conformance and predicate/intermediate contracts: #2145. |
| B10 - codecs/publication | Implemented; renew exact CSV/logical Parquet, original failures and held Saves: #2145. |
| B11 - diagnostics | Shared ownership and null exceptions decided; final registry/installed controls: #2145. |
| B12 - numerical | PortableLibmV1 decided; final public truth, nine assessments and exact comparison: #2145. |
| B13 - builds/locks | Canonical locks and 0.4.0 versions merged; renew actual archive membership, byte equality, features/toolchains: #2145/#2147. |
| B14 - content identity | Policy resolved by the lockfile exception above; build evidence belongs to B13. |
| B15 - independent audit | Audit implemented; passing post-removal combined-main verdict and original-input offline replay: #2145. |
| B16 - lifecycle/removal | Installed controls retained; final ownership/interruptions/reentrancy/repeated use/Save: #2145; removal reconciliation: #2147. |
| B17 - performance/capacity | Harness merged; the bounded candidate profile below addresses [#2142](https://github.com/elong0527/yamaa/issues/2142) installed width/text refusals. New-source correctness and full native qualification precede adoption; [#2141](https://github.com/elong0527/yamaa/issues/2141) replay and [#2144](https://github.com/elong0527/yamaa/issues/2144) complete campaign remain separate gates. |
| B18 - numeric budgets | Item 10 remains unrecorded: [#2143](https://github.com/elong0527/yamaa/issues/2143) independent auditor and #2144 observations/budgets. |
| B19 - transition/rollback | Concrete plan and earlier rollback receipts exist; item 11, final re-admission and artifact handoff: #2147. |

For [#1969](https://github.com/elong0527/yamaa/issues/1969), fixtures/language/API
and installed/numerical gates map to #2145; performance/capacity to #2142-#2144;
transition/removal/handoff to #2147. This guide is
[#2146](https://github.com/elong0527/yamaa/issues/2146).
[#1998](https://github.com/elong0527/yamaa/issues/1998) accepts performance,
[#1999](https://github.com/elong0527/yamaa/issues/1999) accepts transition,
[#1994](https://github.com/elong0527/yamaa/issues/1994) accepts the existing cutover
and #1973 records items 10/11. Close #1969 last.

Performance acceptance is 27 cases (nine dimension variants at 1k/10k/100k) on
all 21 tuples: 567 combinations, ten cold and thirty warm samples after three
retained warmups. Use independent typed/output truth, raw clocks/RSS/phases/callbacks,
both Saves and the prior Python 0.3.0 baseline on the same machine without
concurrent compilation. Capacity follows the decision below. Refusals and
unavailable/incomparable metrics require explicit dispositions; do not choose
thresholds merely to make results pass.

### Bounded runtime capacity

Under the delegated [#1973](https://github.com/elong0527/yamaa/issues/1973)
authority, [#2142](https://github.com/elong0527/yamaa/issues/2142) proposes the
bounded default profile below. Original-source correctness covers the nine
authored dimension variants at 1k/10k/100k driving rows and separately reproduces
width, inherited-validation and text refusals. Adoption remains pending actual
installed correctness at the changed source and full native qualification.
These caller-selected resource limits are not language rules. Different
multiplicities/depths and the trusted Rust longitudinal profile keep explicit
admission outcomes; maximum dimensions cannot be freely combined.

| Admission scope | Candidate ceiling and units | Enforcement |
| --- | --- | --- |
| Compilation and validation | 256 declared/projected/source fields, 64 inputs; 64 Mi cumulative validation-work units. Keys and operands of one `first_available` remain separately bounded at 64. | Compiler, typing, producer contracts and physical decoders share the width policy. Validation still shares work across defaults, documents and normalization selection; document nodes/text/depth, diagnostics and regex limits remain finite and unchanged. |
| Ordinary source | 524,288 combined rows; 2,097,152 decoded cells; 32 MiB captured bytes. Each CSV admits 16 MiB, 2,097,408 scanned fields and 1,048,576 records including the header. Ordinary/typed physical tables admit 256 columns; Parquet retains its separate 8 MiB encoded framing allowance. | CSV scanning bounds temporary fields/records, including unread data. The header reserve is 256 fields; decoded shape admission precedes Arrow construction, and combined source admission precedes execution cell reads. Declared sources retain complete validation and cumulative charges. |
| Copied IPC sources | 64 sources; 8 MiB cumulative encoded bytes and a separate 8 MiB decoded logical-string counter; 256 batches and 256 columns, with the ordinary source row/cell ceilings. | All source framing, schemas and cumulative shapes are admitted before any Arrow decoder; checked text admission precedes owned payloads. |
| Arrow C sources | The same row/cell/column policy; 256 cumulative batches; separate 16 MiB input-buffer and logical-string counters; 64 KiB schema metadata. | One owner counts all sources and empty batches. A refused new stream releases its ownership without invalidating earlier accepted tables. |
| Ordinary execution | 128 Mi logical WorkCells; 131,072 output rows; 1,048,576 output cells; 524,288 key cells; 128 MiB cumulative scalar text; 8 MiB retained output text; 65,536 retained identity cells / 1 MiB identity text. | Checked arithmetic precedes bounded materialization and identity copies. Scalar text charges repeated operand copying/processing; output text charges retained UTF-8 values. Logical work units are not elapsed CPU time. |
| Graph capture and execution | 64 nodes; 32 MiB captured bytes; 16 MiB encoded artifacts; 2,097,152 decoded/owned output cells; 1,048,576 source/output rows, key cells and retained identity cells; 128 MiB scalar text; 16 MiB output/identity text; shared actual 128 Mi WorkCells; 64 MiB codec-storage, 256 Mi decode-work and 64 Mi routing reservations. | Source-row shares weight declared input slots; output-cell shares weight owned columns. Other row/key/text/identity shares remain conservative per node. Aliases consume read/cell/work admission while borrowing retained artifact bytes. CSV codec-storage reservations cap encoded input; field/record/shape policies separately bound temporary ownership. |
| Reports | 160 MiB compact encoded bytes; retained charge min(6 × requested encoded allowance, 768 MiB); 4,194,304 cells; 512 Mi logical report work. | Native node reports pool actual lengths/charges. Aggregate formatting, typed copying and each Save have separate owners. Row buffers charge 3 × requested capacity before reserve; text/entry charges precede copies. |
| Typed public copies | 8 MiB final IPC, with the report counters above; each of three passes charges 64 bytes per visited cell, 2,048 per column and 4 per UTF-8 payload byte. | A failed copy exposes no output or Save capability and retains the accepted native graph and original refusal. |
| Host evidence and publication | Host metadata: 65,536 identity bytes, 16 MiB replies, 65,536 records, 64 MiB source evidence, 1,024 functions and 2,049 version findings. Observer: 64 nodes, 1 MiB identity text, 1,024 stage records and 16 Saves. Publication: 64 nodes, 1 MiB paths, 16 MiB artifact bytes and 64 Mi logical work. | Borrowed evidence, the complete target set and every possible publication-report prefix are admitted before owned copies or the first publisher. Failures preserve original errors, actual entry order and prior writes; held Saves only republish retained bytes. |

The implementations remain
[capacity.rs](https://github.com/elong0527/yamaa/blob/main/rust/crates/yamaa-engine/src/capacity.rs),
[producer_build.rs](https://github.com/elong0527/yamaa/blob/main/rust/crates/yamaa-engine/src/producer_build.rs),
[report_projection.rs](https://github.com/elong0527/yamaa/blob/main/rust/crates/yamaa-adapters/src/report_projection.rs)
and [host_limits.rs](https://github.com/elong0527/yamaa/blob/main/rust/crates/yamaa-adapters/src/host_limits.rs).
These finite counters bound the admitted operation. Allocator overhead, already
allocated foreign buffers, host representations and collector transport are
separate quantities. In particular, separate owner charges must not be summed
as a whole-Build storage allowance or equated with RSS.

The width choice covers the reported clinical 70–150-variable scope with bounded
headroom. Four times the former field width and input count remains coupled to
unchanged total source/output cells, rows and execution work. Sixty-four Mi
validation-work units permits additional finite parent/child/default-selection
passes over wider documents; it changes no document arena, diagnostic, text,
depth or regex allowance. Width and expression complexity share the unchanged
262,144 cumulative normalization-edge allowance. Installed inherited controls
must demonstrate the supported joint geometries before this candidate is adopted.
Neither 4,096 fields nor an unbounded validation traversal is selected.

The frozen candidate
[`083e0b35`](https://github.com/elong0527/yamaa/commit/083e0b35de8ec31b6eab1de7e2a6b231f04e1808)
failed its original success expectations for complex 256-column inherited and
empty-parent documents; those results remain historical failed-candidate evidence.
The isolated [typed diagnostic](https://github.com/elong0527/yamaa/actions/runs/38530469892)
retains the exact original complex YAML and verifies unchanged runtime source.
Both refusals belong to dependency-reference extraction's normalization `Edges`
counter at 262,144. Successful charged prefixes are 261,964 and 262,006 edges,
respectively; the unchanged error exposes no required value. Their validation-work
prefixes are 21,774,333 and 22,082,186, below the 64 Mi work ceiling.

The supported correctness geometry is the authored three-branch case on 40 and
150 columns in standalone, inherited and empty-parent forms, the same complex
256-column standalone form, and separately simple source-reference 256-column
inherited and empty-parent forms. The diagnostic accepts the latter two at 43,779
and 40,140 edges; complete installed typed cells and both held Saves remain
required at the renewed source. The new candidate keeps the original complex
256-column inherited YAML as explicitly named edge-budget refusal controls with
failed Build, failed Saves and no publication. The additional installed renewal
therefore has 82 controls, including the two separate simple geometries. This
disposition changes no arena ceiling, validation order or diagnostic projection.

At native source
[`847f7045`](https://github.com/elong0527/yamaa/commit/847f70457cc328cfac2d061c45072f3f0a0efe69),
both fresh installed hosts passed all 82 controls: 67 complete successes and 15
preserved refusals. Each also passed the unchanged 27-case frontier and all 30
fresh children, retaining 270 original capacity-trace lines. These are untimed
correctness observations. The separately pinned optimized harness is
[`c04fcd40`](https://github.com/elong0527/yamaa/commit/c04fcd408f6fac88e5812d2ab40d8b688ab1760a);
independent truth comes from `847f7045`. Harness-source proof does not establish
native-source qualification. The clinical width controls above each use three
source rows, one key and one three-column source; their column counts are not a
promise at every row count or expression complexity.

Installed oversized CSV/scalar/output refusals expose generic
`build/result_projection`; complex inherited refusals expose
`prepare/issue_projection`, with a null observations report. Their reached
public issues, failed Saves and absence of publication are retained as observed.
Named typed CSV/scalar/output boundary controls and the actual typed inheritance
control establish the underlying admission owners; unavailable installed counter
or required values remain unavailable. The
[`847f7045` qualification](https://github.com/elong0527/yamaa/actions/runs/38533170653)
passed all three strict R hosts but failed a Rust fixture still expecting the
former 64-column IPC boundary. The reviewed test-only renewal exercises 257
columns against the current 256-column boundary, allowing 512 solely in that
fixture's compiler while preserving its original ownership and failed-Save
assertions. Adoption remains pending full qualification and independent replay
at the renewed source composed with current resource-path fixes.

On original source `1ac79ba5`, both installed hosts ran 67 additional independently
authored controls: 23 complete successes and 44 preserved refusals on each host.
The controls cover compiler/projection/input counts, typed and unread physical
widths, producer contracts, standalone/empty-parent/inherited case columns,
CSV bytes and fields, cumulative captured bytes/rows/cells, retained result text
and repeated predicate text. Successful controls compare every typed cell and
all root/producer CSV bytes from two held Saves; refused controls expose no
output, publish nothing, and retain the original errors through failed Saves.
These are correctness controls outside the unchanged 27 timing cases.

The 40-flag, 4,000-row control produces only 188,000 retained UTF-8 bytes. Each
non-key case evaluates a 40-byte source through distinct-value collection,
owns the 40-byte predicate operand, owns its 40-byte literal and selects a
one-byte result: 121 cumulative scalar-text bytes per result, plus seven key
bytes per row. The complete operation needs 19,388,000 scalar-text bytes, while
the original 16 MiB counter refuses at a required 16,777,223 bytes. These charges
bound repeated copying/processing, not retained result size or report copies.
The 128 MiB candidate permits this one-comparison, 40-byte-operand geometry even
when constrained by the 1,048,576 output-cell allowance. Longer operands, repeated
branches and nested expressions consume the same finite counter and may refuse.
Reports and each public typed copy retain their own checked counters.

The 8 MiB retained-text candidate admits the reported 30k-row, 80-byte result
shape beyond the former 2 MiB refusal. The final 8 MiB IPC ceiling still includes
framing, offsets, schema and payload, so 8 MiB retained text does not promise an
8 MiB export. The 16 MiB per-CSV and 32 MiB cumulative capture allowances support
the isolated 9 MiB unread file and three approximately 5.9 MiB files while still
validating their entire physical content. Decoded rows/cells, codec reservations,
source counts and schemas can independently refuse a byte-admitted input.

For example, 150 physical columns leave at most 13,981 combined source rows
under the unchanged cell allowance; 150 output columns leave at most 6,990
output rows. At 256 columns those bounds are 8,192 source and 4,096 output rows.
Short-text 100k-row inputs remain possible at the authored narrow widths, while
256 columns by 100k rows exceeds both cell policies. Sixty-four inputs means
sixty-four individually declared sources sharing the captured-byte, decoded-cell,
row and work allowances, not sixty-four maximum-sized files. All supported
examples remain subject to their other independent ceilings and full validation.

The fixed ODM interpretation keeps its existing eleven canonical output fields
and distinct codec/metadata policies. CSV scanning still admits its complete
physical fields and bytes before canonical projection, but the decoded-cell
counter measures the canonical table, not every vendor-only field. The ordinary
256-column examples above do not describe that interpretation. Its native source
contracts remain owned by [#2145](https://github.com/elong0527/yamaa/issues/2145).

Both installed frontiers used exact source
[`1ac79ba521b2e16c6c0ef2784df9c03ae722a1b0`](https://github.com/elong0527/yamaa/commit/1ac79ba521b2e16c6c0ef2784df9c03ae722a1b0):
CPython 3.12.14 wheel `yamaa-0.4.0-cp312-abi3-linux_x86_64.whl` and R 4.6.1 source
`yamaa_0.4.0.tar.gz`, installed outside all checkouts. Each passed all 27 authored
cases and all 30 fresh children, including three callback observers. Independent
generator truth checks every typed root cell and float bit, complete node/source
inventories, empty diagnostics/logs, zero Build publication and every CSV from
both held Saves. Each retains 270 original capacity-trace lines.

| Observed maximum, one admission owner | Python | R | Selected ceiling |
| --- | ---: | ---: | ---: |
| Complete encoded Save report, bytes | 129,386,283 | 129,386,077 | 167,772,160 |
| Largest conservative complete publication prefix, bytes | 129,386,361 | 129,386,155 | 167,772,160 |
| Native pooled retained charge, bytes | 622,193,264 | 622,187,528 | 805,306,368 |
| Native pooled report cells | 2,800,000 | 2,800,000 | 4,194,304 |
| Native pooled report-work units | 258,567,168 | 258,566,212 | 536,870,912 |

The largest report/charge case is the 100k depth-three producer. Its original row
blocks request twelve 8,388,608-byte buffers and one 16,777,216-byte buffer;
their 112 MiB total is charged before reserve. Independent compact-byte counting
of 1,078 conservative code/location/entry variants over each original graph
report stays within the complete publication-prefix ceiling for the authored
paths and suffixes, without executing a candidate again. It does not bound
arbitrary path metadata. Complete report and prefix observations replace the
exploratory metadata reserve as evidence.
The observed charge, cell and work maxima stay below their distinct ceilings;
the original 27-case passes used unchanged limits. They do not validate the
candidate width/text increases above. Whole-child Linux `wait4` peak RSS
was 1,406,869,504 bytes for Python and 1,644,023,808 bytes for R, including worker
collector transport. These observations deliberately establish no RSS budget.

The [#2169 review record](https://github.com/elong0527/yamaa/pull/2169) keeps this
source selection separate from native qualification. Original local installation
receipts, requests, responses, complete views, reports, both Save artifacts,
stderr charges, process records and generator bytes remain intact. Shared
controls pass equality/one-more refusal, cumulative source ownership and checked
shape/byte arithmetic; existing public Python/R controls preserve failed copies
and failed Save prefixes.

This local frontier is not relabeled as a newer source or a 21-tuple performance
campaign. The original reviewed-branch native run
[38503894937](https://github.com/elong0527/yamaa/actions/runs/38503894937), attempt 1,
failed Windows shared-Rust protocol/fixture controls and cannot qualify the
updated PR. Renew exact-head native qualification after the fixes, retain hosted
frontier/campaign inputs and require [#2145](https://github.com/elong0527/yamaa/issues/2145)
combined-main evidence before final release acceptance. Local scratch evidence
has no durable publication identity; [#2144](https://github.com/elong0527/yamaa/issues/2144)
and [#2154](https://github.com/elong0527/yamaa/issues/2154) retain/replay the original
hosted inputs. Performance budgets and transition acceptance remain pending.

## Qualification and retained records

Use [CI guidance](https://github.com/elong0527/yamaa/blob/main/.github/ci.md)
for sampled PR coverage, the full native route and independent audit/replay.
Ordinary dispatch supplies the installed matrix and component numeric checks;
shared Rust, nine math assessments/comparison and audit require main or explicit
qualification pushes. Main's audit is nonblocking: inspect its verdict and replay
the original inputs. Branch qualification stays `reviewed-branch`; only genuine
postmerge evidence is `combined-main`.

Benchmark directories and the public-conformance configuration determine the
current authored inventory and explicit exclusions. The generated
[benchmark index](https://github.com/elong0527/yamaa/blob/main/benchmarks/README.md#benchmarks)
accounts for all 318 authored cases, including 316 active cases shared by Python
and R and the two reviewed path-history exclusions. Runnable host entries describe
metadata. Each installed inventory must supply actual passing results for the
same current active set; the earlier JSON observations keep their original
source/run/attempt/artifact identities and do not qualify a later source.

New native audit snapshots retain exact-source benchmark specification paths in
`source.json` and the exclusion configuration in
`source/rust/tools/public_conformance.py`. Offline replay of a pre-change retained
snapshot uses its original `source/benchmarks/execution-manifest.yaml` and metadata.
This retained-input reader does not restore a runtime API or infer qualification
from current checkout labels. Original retained-snapshot replay and final
installed Python/R results remain evidence gates under #2145.

The live inventory is:

| Record | Reader and purpose |
| --- | --- |
| [Current rules](articles/rules.md) and [schema-navigation.tsv](https://github.com/elong0527/yamaa/blob/main/.github/scripts/yaml-validation/fixtures/schema-navigation.tsv) | `check_rule_rewrite.py` derives current normative ownership; `test_rule_rewrite.py` checks 363 independent schema owners. `generate_rule_reference.py` derives navigation from current contracts and schemas. |
| [release-api.json](https://github.com/elong0527/yamaa/blob/main/rust/qualification/release-api.json) | `check_release_api.py` and its tests compare declared exports/dispositions. `retain_candidate` labels remain inventory classifications, not final acceptance. |
| [benchmarks/](https://github.com/elong0527/yamaa/tree/main/benchmarks) and [public_conformance.py](https://github.com/elong0527/yamaa/blob/main/rust/tools/public_conformance.py) | Directories and explicit exclusions derive the current inventory, index/dashboard membership and the same mandatory active set for both installed hosts. |
| [public-conformance.json](https://github.com/elong0527/yamaa/blob/main/rust/qualification/public-conformance.json) | Prior passing observations retain original evidence identities. The comparator gates the current directory-derived active set and compares new passes with these observations. |
| [supplemental.json](https://github.com/elong0527/yamaa/blob/main/rust/qualification/supplemental.json) | Installed supplemental inventory and native audit enforce component/public obligations. |
| [rollback-assets.json](https://github.com/elong0527/yamaa/blob/main/rust/qualification/rollback-assets.json) and [prior-python-rollback-run.json](https://github.com/elong0527/yamaa/blob/main/rust/qualification/prior-python-rollback-run.json) | Retention/rehearsal tools pin original packages, attempts, asset IDs and earlier receipts. |
| [native-source-fixtures.json](https://github.com/elong0527/yamaa/blob/main/rust/qualification/native-source-fixtures.json) and [producer-cohort/](https://github.com/elong0527/yamaa/tree/main/rust/qualification/producer-cohort) | Staging and cohort comparison preserve independent fixture membership/truth. |

No active reader uses `rust/planning/`: its live API inventory moved atomically
to `rust/qualification/release-api.json` in #2161. Historical
[Python retirement](https://github.com/elong0527/yamaa/blob/43bb4437d9c0890ec7877ec7575a517c771a8147/rust/planning/python-retirement-inventory.json)
and [validator assertion](https://github.com/elong0527/yamaa/blob/43bb4437d9c0890ec7877ec7575a517c771a8147/rust/planning/validator-assertion-disposition.json)
maps are retrievable at their original revision; #2147 must reconcile every
unique replacement with final installed evidence. Git retrieval proves map
availability, not replay of external artifacts. Current normative ownership and
schema navigation use [the current rules](articles/rules.md), schema sources and
the independent owner controls above. No active reader requires the retired
[migration map](https://github.com/elong0527/yamaa/blob/43bb4437d9c0890ec7877ec7575a517c771a8147/rules/migration.yaml);
its former aliases, retirement decisions and prose provenance remain in Git.
[#2154](https://github.com/elong0527/yamaa/issues/2154) owns physical history removal
and durable replay. Raw `rust/measurements/` remains pending verified retention
of its original external inputs; a scratch path or expiring Actions URL is not a
durable archive. Add evidence to PR/issues and this compact index, without new
per-issue ledgers or rewriting previous observations.

## Rollback and artifact handoff

The retained receipt reports earlier Python 18-tuple rehearsal
[38460509078](https://github.com/elong0527/yamaa/actions/runs/38460509078) and R
same-archive three-host rehearsal
[38435902670](https://github.com/elong0527/yamaa/actions/runs/38435902670).
They keep their preparation/source identities and do not approve 0.4.0 transition.

| Retained package | Identity and availability |
| --- | --- |
| Python 0.3.0 | Published source tag `yamaa-py-0.3.0`, exact source `845a91ff9ba4ab6599efbd79fafe1c4e1dd14255`. Draft release 411980272 retains source asset 637944563, three source-built platform wheels, original lock/dependency pins and raw receipt bundle 638657402. Those wheels were never published prior binaries. |
| R 0.3.0 | Installed pre-cutover candidate at `a1a9c2d216075f331ac108aa4d3638573f103cea`, draft release 411979803, source asset 637944247 and receipt asset 637944307. No prior R release was published. |

Authenticated review can fetch these unpublished source packages by asset ID:

```sh
mkdir retained-prior-packages
gh api repos/elong0527/yamaa/releases/assets/637944563 \
  --header 'Accept: application/octet-stream' \
  > retained-prior-packages/yamaa-0.3.0.tar.gz
gh api repos/elong0527/yamaa/releases/assets/637944247 \
  --header 'Accept: application/octet-stream' \
  > retained-prior-packages/yamaa_0.3.0.tar.gz
```

Use a GitHub identity authorized to read the drafts. Public release-download URLs
for these drafts are unavailable. Preserve original bytes, API asset references,
calling code and complete dependency locks. In a fresh compatible prior Python
study checkout, keep `yamaa==0.3.0` and select the downloaded archive:

```toml
[tool.uv.sources]
yamaa = { path = "retained-prior-packages/yamaa-0.3.0.tar.gz" }
```

Then `uv lock` and `uv sync --locked`; keep original and restored locks. Use
Rust 1.90.0, pinned maturin 1.9.6 and the prior Cargo lock. For R, use R 4.6.1
and an empty library with `R CMD INSTALL --library=<fresh-library>` against the
retained archive; Windows requires Rtools45 and `x86_64-pc-windows-gnu`.
Study-specific complete renv/uv restoration remains a separate replay check.
Before reading study data or invoking callbacks, verify the installed version:

```python
from importlib.metadata import version
assert version("yamaa") == "0.3.0"
```

```r
stopifnot(identical(as.character(packageVersion("yamaa")), "0.3.0"))
```

Rollback starts a new whole run; earlier saved outputs retain their original
provenance.

After #2141-#2145 pass, #2147 re-admits rollback, records evidence-backed item-11
acceptance without backdating, and hands off the exact final source, run/attempt,
package names/bytes and artifact identities. Renew evidence affected by later
changes. The 0.4.0 source filenames and install templates identify preparation;
qualified download URLs and publication identities remain pending.
