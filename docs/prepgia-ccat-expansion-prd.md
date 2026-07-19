# PrepGIA + CCAT Expansion PRD

## 1. Purpose

This document defines the next product phase for the existing PrepGIA platform:

- keep the current Thomas GIA product working as-is
- add a second assessment track for `CCAT-style practice`
- reuse the same overall learning flow:
  - practice mode
  - module-wise test mode
  - full test mode
- allow users to choose which assessment they want to prepare for from the Practice area

This is not a literal reproduction of proprietary test items. The product should generate original practice questions that match the format, pacing, and skill profile of each assessment.

## 2. Product Goal

Turn PrepGIA from a single-test practice site into a multi-assessment aptitude practice platform.

Phase 1 product families:

- `PrepGIA`
- `CCAT`

Long-term direction:

- one shared platform shell
- one account and subscription system
- multiple assessment families under the same product

## 3. Core User Experience

### 3.1 Practice entry point

The current `/practice` page should become an assessment chooser first.

Top-level choices:

- `PrepGIA`
- `CCAT`

After choosing one, the user should see:

- full test card
- module cards
- progress summary

This keeps the current UI pattern but scopes it to the selected assessment family.

### 3.2 Shared assessment flow

Both products should support:

- `Practice mode`
  - no overall timer
  - immediate right/wrong feedback
  - question-by-question flow
- `Module test mode`
  - timed by module
  - no immediate answer reveal
  - results shown at end
- `Full test mode`
  - all modules in the right order
  - timed by module or by whole test depending on the assessment design
  - final score summary + module breakdown

### 3.3 Assessment selector behavior

Recommended UX:

- `/practice` shows two large cards: `PrepGIA` and `CCAT`
- clicking one goes to a scoped practice dashboard:
  - `/practice/prepgia`
  - `/practice/ccat`

This avoids overloading one page with too many cards.

## 4. Product Scope

## 4.1 PrepGIA

PrepGIA remains as already implemented:

- 5 modules
- practice mode
- section-wise test mode
- full test mode
- role-based access
- subscription logic
- progress tracking

No major format change is required for PrepGIA in this phase beyond making it one assessment family among multiple.

## 4.2 CCAT

CCAT should launch with 3 modules:

- `Math & Numerical Reasoning`
- `Verbal Reasoning`
- `Spatial / Abstract Reasoning`

CCAT features to support:

- module practice
- module test
- full CCAT-style test
- dashboard tracking
- subscription gating using the same billing system

## 5. Structural Comparison: PrepGIA vs CCAT

This is useful because the UI can stay consistent while generator logic differs.

### PrepGIA structure

- multiple highly distinct modules
- context-first interaction in some modules
- strong emphasis on speed within short section timers
- question payloads vary significantly by module

### CCAT structure

- fewer modules
- more mixed reasoning within each module
- more conventional aptitude question formats
- less dependency on special context-reveal UI
- more MCQ-heavy across all modules

### Shared UX opportunities

Both assessments can still use the same platform primitives:

- assessment family
- module
- practice session
- timed module test
- full test
- attempt history
- progress bars
- subscription gating

### UX differences that should remain

PrepGIA:

- some modules use `context -> click -> question`
- highly section-specific rendering

CCAT:

- mostly direct question + options
- less custom rendering per module
- more reuse of a standard MCQ player

## 6. CCAT Module Definitions

## 6.1 Math & Numerical Reasoning

Purpose:

- fast arithmetic reasoning
- pattern recognition with numbers
- ratio and percentage fluency
- basic work-rate and algebra thinking

Planned question subtypes:

- number series
- percentage change
- markup / discount
- ratios and proportions
- work-rate
- averages
- simple equations
- comparison questions

Answer format:

- mostly 4-option MCQ
- some numeric answer converted to MCQ distractors

## 6.2 Verbal Reasoning

Purpose:

- vocabulary
- word relationships
- sentence logic
- language-based classification

Planned question subtypes:

- analogies
- sentence completion
- odd one out
- synonym / antonym relationship
- category match
- short inference passages in phase 2

Answer format:

- 4-option MCQ

## 6.3 Spatial / Abstract Reasoning

Purpose:

- non-verbal logic
- transformation recognition
- shape relationships
- visual pattern deduction

Planned question subtypes:

- rotation completion
- mirror / same-different
- odd figure out
- sequence continuation
- 2x2 and 3x3 matrix reasoning

Answer format:

- 4-option MCQ
- payload may include SVG or structured shape data

## 7. Generator Plan For CCAT

## 7.1 Generator design principles

All CCAT generators should be:

- deterministic by seed
- fast enough for on-demand generation
- server-generated
- answer-key hidden in test mode
- reusable in practice mode and test mode
- validated by subtype-specific unit tests

Shared interface:

```python
generate_question(
    assessment_type: str,
    module_type: str,
    difficulty: str,
    seed: str,
) -> GeneratedQuestion
```

Recommended result shape:

```python
{
    "question_id": "...",
    "assessment_type": "ccat",
    "module_type": "verbal_reasoning",
    "subtype": "analogy",
    "prompt": {...},
    "options": [...],
    "metadata": {...}
}
```

## 7.2 CCAT math generator plan

Implement as a weighted subtype generator.

Suggested subtype weights:

- number series: 20%
- percentages and discount: 15%
- ratios and proportions: 15%
- work-rate: 10%
- averages: 10%
- simple algebra: 10%
- numeric comparison: 10%
- word problems: 10%

Generation logic:

- build each subtype from parameterized templates
- generate the correct answer first
- generate distractors by:
  - common arithmetic mistakes
  - off-by-one errors
  - swapped ratio direction
  - wrong operation path

Validation rules:

- answer must be unique in options
- distractors must be plausible
- question should avoid messy decimals unless intended

## 7.3 CCAT verbal generator plan

Implement with curated lexical banks plus template logic.

Suggested subtype weights:

- analogy: 25%
- sentence completion: 25%
- odd one out: 20%
- synonym / antonym relation: 15%
- category / relationship match: 15%

Content sources:

- synonym banks
- antonym banks
- category groupings
- common workplace / academic vocabulary
- sentence templates with difficulty tiers

Difficulty design:

- easy:
  - common vocabulary
  - direct relationships
- medium:
  - less common words
  - weaker distractor separation
- hard:
  - nuanced word meaning
  - tighter distractor quality

Validation rules:

- only one option can fully satisfy the relationship
- sentence completion options must all fit grammatically, but only one fits semantically best

## 7.4 CCAT spatial / abstract generator plan

Implement with structured shape payloads rather than image files where possible.

Recommended representation:

- SVG paths
- JSON shape instructions
- transform metadata

Suggested subtype weights:

- rotation: 25%
- mirror / same-different: 20%
- odd figure: 20%
- sequence continuation: 20%
- matrix reasoning: 15%

Generation logic:

- define a base shape grammar
- apply transforms:
  - rotate
  - reflect
  - invert fill
  - add/remove element
  - move element by rule

Validation rules:

- one clear correct option
- distractors must be rule-adjacent
- avoid ambiguous visuals

## 7.5 CCAT difficulty framework

For all CCAT modules:

- `easy`
  - direct logic
  - fewer elements
  - simpler distractors
- `medium`
  - moderate complexity
  - tighter distractors
- `hard`
  - more steps
  - more subtle distinctions

Recommended mode mapping:

- practice mode: mostly `easy` and `medium`
- module tests: mixed
- full test: mixed, weighted toward `medium`

## 8. Data Model Changes

The current data model is centered on PrepGIA sections. We should generalize it.

### 8.1 New concept: assessment family

Add `assessment_type` to all major attempt and progress models.

Examples:

- `prepgia`
- `ccat`

### 8.2 Rename where useful

Current naming uses `section` heavily.

Recommended generalization:

- keep `section` in PrepGIA-specific UI if desired
- use `module` as the product-wide neutral term

Suggested model evolution:

- `Attempt`
  - add `assessment_type`
- `AttemptSection`
  - either rename later to `AttemptModule`
  - or keep model name but add `module_type`
- `SectionProgress`
  - add `assessment_type`
  - keep one row per user + assessment + module

### 8.3 Question payload storage

Continue storing generated question payloads in JSON fields.

This is especially useful for CCAT because:

- math questions store parameters and computed values
- verbal questions store category metadata
- spatial questions store shape instructions

## 9. Routing And Page Plan

Recommended new routes:

- `/practice/`
  - assessment chooser
- `/practice/prepgia/`
  - PrepGIA dashboard
- `/practice/ccat/`
  - CCAT dashboard
- `/practice/prepgia/full-test/`
- `/practice/ccat/full-test/`
- `/practice/prepgia/<module>/`
- `/practice/ccat/<module>/`

This keeps the URL model clean and SEO-friendly.

## 10. Access And Subscription Rules

Subscription logic should remain shared across products.

Recommended behavior:

- free users:
  - limited full tests across the platform or per assessment, depending on commercial decision
  - access to module practice
- paid users:
  - unlimited PrepGIA
  - unlimited CCAT

Recommended product decision:

- keep subscription entitlement platform-wide
- avoid separate CCAT-only and GIA-only plans in phase 1

This simplifies billing and messaging.

## 11. Practice Page Product Design

## 11.1 New top-level practice page

The Practice page should show two assessment cards:

- `PrepGIA`
- `CCAT`

Each card should include:

- title
- one-line description
- module count
- CTA: `Open practice`

### Example copy

PrepGIA:

- 5 modules
- Thomas GIA-style speed practice

CCAT:

- 3 modules
- numerical, verbal, and abstract aptitude practice

## 11.2 Assessment-specific practice dashboard

Once inside an assessment family, show:

- full test banner
- module grid
- progress summary
- recent attempt summary

Same structure for both products.

## 12. Dashboard Changes

Dashboard should support filtering or grouping by assessment family.

Recommended sections:

- recent attempts
- PrepGIA summary
- CCAT summary
- full test history
- module-wise test history

Important:

- users should be able to distinguish PrepGIA attempts from CCAT attempts immediately

## 13. Technical Reuse Strategy

The current platform already has strong reusable primitives.

Reuse as-is where possible:

- auth
- subscription system
- dashboard shell
- attempt lifecycle
- fullscreen test mode
- practice progress recording
- section detail player architecture

Refactor where needed:

- generalize single-assessment assumptions
- move hardcoded PrepGIA constants into assessment configs
- split generator registry by assessment family

Recommended config structure:

```python
ASSESSMENT_CONFIG = {
    "prepgia": {...},
    "ccat": {...},
}
```

Each assessment entry should define:

- display name
- module list
- module titles
- module descriptions
- time limits
- practice counts
- generator bindings

## 14. CCAT Generator Implementation Phases

### Phase 1

- add `assessment_type` plumbing
- create CCAT module config
- add assessment chooser UI
- add CCAT dashboard pages
- implement CCAT math generator
- implement CCAT verbal generator
- implement CCAT spatial generator
- enable module practice

### Phase 2

- enable timed module tests
- enable full CCAT test
- add CCAT-specific results breakdown
- add analytics by CCAT module

### Phase 3

- add richer verbal content
- add matrix reasoning improvements
- add adaptive difficulty
- add generator health/admin tools for CCAT content packs

## 15. Risks

### Content quality risk

CCAT-style verbal and abstract questions can feel repetitive if the content bank is weak.

Mitigation:

- large lexical banks
- weighted subtype rotation
- stronger distractor logic

### Visual ambiguity risk

Spatial reasoning questions can be ambiguous if transform rules are not strict.

Mitigation:

- structured shape grammar
- validation tests
- screenshot-based QA for sample outputs

### Product complexity risk

A second assessment family can make the app feel cluttered.

Mitigation:

- assessment chooser first
- same shell, isolated dashboards
- clear naming and attempt labels

## 16. Recommended Immediate Next Steps

1. Refactor platform constants from PrepGIA-only to `assessment config`.
2. Add `assessment_type` to attempt and progress models.
3. Create the new practice chooser page with `PrepGIA` and `CCAT`.
4. Add CCAT module metadata and routes.
5. Implement the 3 CCAT generators in this order:
   - math
   - verbal
   - spatial
6. Reuse the current practice player for CCAT with mostly direct MCQ rendering.
7. Add CCAT attempts to the dashboard and subscription flows.

## 17. Final Recommendation

The platform should evolve from `PrepGIA only` to `PrepGIA + CCAT` using one shared Django codebase, one shared billing model, and one reusable assessment engine.

The best implementation approach is:

- keep PrepGIA stable
- introduce `assessment_type` as the core abstraction
- build CCAT as a second assessment family on top of the same player and attempt system
- keep the UI parallel across both products so the app feels coherent

This gives a clean path to support more aptitude tests later without rewriting the foundation.
