# report/

Where written reports get compiled from — separate from `results/`
(generated data) and `docs/` (working project docs like `status.md` /
`training-log.md`). Nothing in here is generated automatically; this is
where drafts live.

```
report/
    <report-name>/
        draft.md                 the actual write-up
        figures/                 copies (not symlinks — keep reports
                                  reproducible/portable) of whichever
                                  results/<label>/figures/*.png this
                                  specific report cites
        source_manifest.json     copy of the results/<label>/manifest.json
                                  this report is based on, so "which sweep
                                  produced these numbers" is always
                                  answerable later
```

**Convention:** every report subfolder should be traceable to exactly one
`results/<label>/` (or a small, explicitly-listed set, if a report spans
multiple sweeps/checkpoints) via `source_manifest.json`. A report that
can't say which run its numbers came from isn't reproducible.

Final export format (Word doc, PDF, slides, etc.) is a build step on top
of `draft.md`, not a separate hand-maintained copy — regenerate the export
from the draft, don't hand-edit two versions of the same report.
