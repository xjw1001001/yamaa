This isolated workflow prepares the missing prior Python rollback evidence for
#1999. It runs only when `migration/prior-python-rollback` is pushed. It does not
change main's installed qualification policy or publish, edit or upload a release.

The source is the prior `yamaa-py-0.3.0` tag, exact commit
`845a91ff9ba4ab6599efbd79fafe1c4e1dd14255`. Assets come from existing unpublished
retention draft 411980272, `yamaa-py-reference-845a91ff`. Every GET first checks
the draft's target, each asset ID/name/size and uploaded state. Redirects remove
credentials on a host change; signed URLs and credentials are never logged.

The Linux wheel is the exact retained source-built baseline asset 637944633.
macOS arm64 and Windows x64 wheels are built from installable prior source asset
637944563 using Rust 1.90.0, maturin 1.9.6 and its unchanged Cargo lock. These are
source-built prior packages, not previously published binary assets. Each platform
wheel is freshly installed on CPython 3.12, 3.13 and 3.14. The nine source lanes
independently rebuild that same source package on their own interpreters, then
freshly install their owned rebuild. This yields eighteen distinct reinstall lanes.

Every lane verifies prior package 0.3.0 and native core 0.1.0, module/environment
ownership, all unchanged installed wheel members and seventeen retained dependency
pins before extracting study data. It replays the original lookup, aggregate and
window fixture domains, removes the specification and input directories, and
performs two retained Saves per domain. Both Save files must equal independent
committed CSV bytes from the exact prior source. Raw Arrow output/issues, Save
bytes, version checks and build/retrieval receipts remain in the lane artifact.

The aggregate audit requires exactly all eighteen lanes and three platform wheel
artifacts from the same run, attempt and preparation commit. It rechecks full prior
repository entry bytes, symlink targets and executable modes against Git, source
package/lock equality, the retained Linux wheel bytes, runtime/form/build owners,
raw table shape and empty issues, byte-identical output before/after held Saves,
and every committed truth and held Save byte.
Mutation controls reject missing lanes, false identities, wrong owners and changed
truth or Save bytes. No expected outputs are regenerated or normalized.

This is rollback evidence for three representative prior domains and held results.
It does not establish a prior complete producer-graph Save baseline, candidate
installed qualification, numerical budgets or transition approval. Published
rollback URLs and actual pin restoration remain separate gates while the release
stays a draft. Success may be claimed only from the actual complete audit receipt.
