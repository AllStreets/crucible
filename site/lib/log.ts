export interface LogEntry {
  date: string;
  title: string;
  body: string;
  kind: "entry" | "retraction";
  /** The claim this entry withdraws, kept readable rather than deleted. */
  withdrawn?: string;
}

/** The research log. Prose only: no entry may state a figure, because a figure
 *  typed here is a number nobody can trace to a row. Counts belong on pages
 *  that read the dataset. */
export const LOG: LogEntry[] = [
  {
    date: "2026-09-26",
    kind: "retraction",
    title: "The README described paper generation in the present tense",
    withdrawn: "Papers are generated from run records rather than written about them.",
    body:
      "That sentence described a design as though it were working software, and " +
      "a reader came away expecting papers that do not exist. The press stage " +
      "is not built and no paper has been generated. This is the precise " +
      "failure this project exists to avoid, committed by its own README.",
  },
  {
    date: "2026-09-26",
    kind: "entry",
    title: "A sentinel string leaked into the failure classifier",
    body:
      "BuildKit echoes the entire failing command in its error trailer. The " +
      "build recipe wrote its sentinel inline, so that string appeared in the " +
      "log of every failed build of that recipe whatever actually went wrong, " +
      "and the classifier duly labelled a build that had failed inside pip as " +
      "an ambiguous manifest. The same trap was already documented in the " +
      "codebase for a different needle and was reintroduced two functions " +
      "away. The logic now lives in a script so the trailer carries only its " +
      "path, and a regression test asserts that a log whose only mention of " +
      "the script is the trailer is claimed by no manifest class.",
  },
  {
    date: "2026-09-26",
    kind: "entry",
    title: "The build recipe was not pinned in the build record",
    body:
      "Rows recorded the commit and the image but not the recipe that produced " +
      "them. The recipe decides which agents are buildable at all, so editing " +
      "it changes the answer, and rows produced under two versions are two " +
      "measurements. Without the pin, one edit would have silently redefined " +
      "every figure already published and nothing would have marked the " +
      "boundary. Every build row now carries a digest of the recipe.",
  },
  {
    date: "2026-09-26",
    kind: "entry",
    title: "Three failure classes blamed agents for gaps in the harness",
    body:
      "The recipe searched for a package only at the repository root, so every " +
      "monorepo was recorded as having no installable manifest. Two widely run " +
      "coding agents written in TypeScript were recorded the same way, though " +
      "both ship a package.json and simply are not Python. A workspace root " +
      "that setuptools refuses to install was pooled into a generic build " +
      "failure, losing the one fact that made it actionable. Each is now its " +
      "own class naming a limit of this harness rather than a defect of an " +
      "agent, and the search goes two levels deep with one stated rule for " +
      "choosing among candidates and a refusal when none applies.",
  },
  {
    date: "2026-09-26",
    kind: "entry",
    title: "First run against a live Docker daemon",
    body:
      "The engine had been reviewed eight times and never run. The first run " +
      "confirmed that reading the image digest from RepoDigests, which the " +
      "original code did, fails for any locally built image: the field is " +
      "empty, the template errors, and every genuinely viable agent would have " +
      "been recorded as a build failure. The fix had been argued from the " +
      "documented contract. It is now observed.",
  },
];
