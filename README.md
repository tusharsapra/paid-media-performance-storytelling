# Paid Media Performance Storytelling

I am Tushar Sapra, a marketing expert with experience handling multiple clients and helping them understand their marketing performance. I built this skill to turn paid media data across platforms into clear insights, evidence-backed reports, and practical actions, helping marketers explain what changed, why it matters, and what to prioritise next.

This is a portable agent skill for analysing supplied performance evidence. It helps produce weekly updates, monthly reviews, plan versus actual analysis, slide-ready insights and recommendations. The skill keeps platform metrics, analytics events and business outcomes separate when their definitions do not align.

## Install

Clone this repository into your Codex user skills directory:

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/tusharsapra/paid-media-performance-storytelling.git "$HOME/.agents/skills/paid-media-performance-storytelling"
```

For a project-only installation, clone it into that project's `.agents/skills/` directory instead. You can also download the repository ZIP and copy the extracted `paid-media-performance-storytelling` folder to either location. Keep `SKILL.md`, `references/`, `scripts/` and `assets/` together. Start a new Codex session after installing so it can discover the skill.

## Use

Invoke `$paid-media-performance-storytelling` and provide the performance exports, approved plan or targets, reporting period, business objective and any analytics or CRM summaries available. The skill asks for missing definitions that could change the conclusion and marks unresolved comparisons.

Example request:

```text
Use $paid-media-performance-storytelling to review these paid media exports.
Compare June with May for our lead generation campaigns.
Use the attached approved plan for targets and the CRM summary for qualified leads.
Explain the main changes, what the evidence supports, and the next actions.
```

The Python helper works with a **normalized CSV and an explicit JSON brief**. It does not directly import arbitrary platform exports or verify the truth of supplied metadata. See [data contract](references/data-contract.md) and [metrics](references/metrics.md) before using it on your own data.

## Verify the package

The helper uses the Python standard library. From the repository root:

```bash
python3 scripts/test_report_metrics.py
python3 scripts/report_metrics.py --data assets/sample-performance.csv --config assets/sample-brief.json --output /tmp/paid-media-total.json
python3 scripts/report_metrics.py --data assets/sample-performance.csv --config assets/sample-brief.json --group-by market --output /tmp/paid-media-markets.json
```

The sample data is fictional. The market report warns that the supplied total target does not apply to individual markets; that warning is expected.

## Contents

- `SKILL.md`: workflow and operating rules
- `references/`: data, metric, diagnosis, measurement and writing guidance
- `scripts/report_metrics.py`: validation and arithmetic for normalized CSVs
- `scripts/test_report_metrics.py`: regression tests
- `assets/`: fictional example inputs and intake template
- `agents/openai.yaml`: optional Codex interface metadata

Keep client exports, credentials and generated reports outside this public repository.
