# Publication and search discoverability notes

This is the maintainer's implementation record, separate from the developer guide.

## Implemented content structure

- Descriptive repository name and main title match the concrete topic: Polymarket Data API.
- The opening paragraph answers what the API does, where it lives, and who the guide is for.
- One H1, a linked contents list, stable explicit endpoint anchors, and task-oriented headings make sections addressable.
- All 20 routes in the dated retrieved schema are covered, including parameter names/types/defaults/bounds.
- Python and JavaScript examples, live observations, and reproducible checks add practical value beyond a historical endpoint list.
- Primary citations, visible maintainer identity, a review date, source fingerprint, and correction instructions make claims easier to inspect.
- The companion public Gist uses the same Markdown guide and links to this repository for maintained examples and corrections.

## GitHub-specific limits

GitHub controls the rendered repository/Gist HTML, robots policy, response headers, title template, and canonical behavior. Markdown does not provide reliable control of meta descriptions, HTML head tags, JSON-LD, sitemap submission, or a cross-host rel=canonical. A visible source link is attribution/navigation, not a canonical tag. No fake structured data or invisible keyword text was added.

Publishing both repository and Gist may lead search engines to select either duplicate as the preferred result. Maintain one source file and avoid independently diverging copies. This publication does not establish that either URL is indexed or ranks for a query.

## Search and AI discoverability approach

The target intents are documentation, endpoints, wallet positions, trade history, holders, condition IDs, pagination, rate limits, P&L, Python, and JavaScript examples. These terms appear where they answer an actual developer question. This is an editorial intent map, not keyword-volume research.

Google's guidance emphasizes useful, original, accessible content and foundational SEO for AI search experiences. Clear answers and evidence support usability; no formatting trick guarantees rankings or AI citations. See [Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) and [SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide).

## Next measurements

After discovery/indexing has had time to occur, record dated visibility checks for the actual repository and Gist URLs and relevant developer queries. Track substantive issues, example usage, and genuine citations as maintenance feedback. No ranking outcome, backlink campaign, recurring monitor, or indexing submission has been claimed or performed as part of this initial publication.

## V2/V3 and SDK content revision

Expanded the title, introduction, navigation, and FAQ to answer current Polymarket API version and official SDK queries. Added a version compatibility table, official package directory with dated runtime/version pins, protocol-neutral identifier guidance, raw-versus-SDK field comparisons, runnable SDK examples, a contract map, and migration limitations. Existing endpoint anchors and public URLs are retained. The repository and existing Gist remain two views of one maintained README.

Validation distinguishes official code evidence of Exchange V3 support from live public CTF data reads. No ranking, indexing, or AI citation outcome is implied by this revision.
