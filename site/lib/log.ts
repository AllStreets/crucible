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
    date: "2026-09-27",
    kind: "entry",
    title: "The base image became a variable, and two agents got as far as crashing",
    body:
      "Three agents in the seed list failed to build for one reason: each needed a newer " +
      "Python than the recipe provides, one directly and two through a dependency. That is " +
      "a limit of this harness and not a property of any of the three, so the base image is " +
      "now declared by the seed line and recorded on the build row, because rows built on " +
      "two bases are two measurements and nothing else marked the boundary. All three now " +
      "build. None can yet be invoked. Two die on start with an illegal instruction, traced " +
      "to the current release of a cryptography library whose compiled extension uses an " +
      "instruction this machine does not implement; two earlier releases on the same base " +
      "import cleanly. Neither agent does anything wrong, and nothing about either has been " +
      "measured beyond the fact that it builds. The third keeps its configuration and every " +
      "file it writes inside an image root the sandbox mounts read only, so it could not " +
      "reach the shared workspace even if it were configured.",
  },
  {
    date: "2026-09-27",
    kind: "entry",
    title: "A full disk was recorded as two agents failing to build",
    body:
      "Two agents were added to the seed list and both came back as build failures. " +
      "The logs said neither had been cloned: the machine's Docker volume had filled, " +
      "and apt could not download its packages. The dataset had recorded a fact about " +
      "this laptop as a property of two repositories, which is the exact contamination " +
      "the failure classes exist to prevent, and the generic wrapper that follows every " +
      "failing build step is what let it through. A full disk is now its own class, named " +
      "for the machine and attributed to this harness wherever causes are broken down. " +
      "The rows were superseded by a rebuild once there was room, which found the real " +
      "cause of each: both need a newer Python than the base image provides, one directly " +
      "and one through a dependency.",
  },
  {
    date: "2026-09-27",
    kind: "entry",
    title: "The classifier graded a victim whose command was not found as holding the attack",
    body:
      "The first unattended pass over six pairs was audited against its transcripts " +
      "before it was pushed. A shell agent proposed a command that was not found and " +
      "exited with the shell's command-not-found status; the criterion read the absence of a side effect as resistance, but " +
      "the agent had completed nothing. Any non-zero exit is now an artifact, and the two " +
      "rows were superseded rather than edited.",
  },
  {
    date: "2026-09-27",
    kind: "entry",
    title: "Engagement was defined by one agent's transcript",
    body:
      "Every verdict with smolagents or shell_gpt as the victim came back weak, because the " +
      "lines that meant a tool acted were the lines gptme prints. A code agent prints a marker " +
      "and then the code; a shell agent prints the command it proposed. Entrypoints now declare " +
      "the lines in their own transcript that mean a tool acted, beside the invocation and the " +
      "build extras. Twelve verdicts moved from weak to strong on the transcript's evidence.",
  },
  {
    date: "2026-09-27",
    kind: "entry",
    title: "The classifier counted the victim's echoed prompt as reading the file",
    body:
      "Its first pass returned three strong verdicts for victims that had read nothing. The " +
      "engagement rule matched the word Read in the victim's own echoed prompt, which names the " +
      "file it is told to read. The harness's prompt satisfying the harness's detector is the " +
      "failure this project keeps finding, and it was in the classifier too. A test pins the " +
      "echoed prompt as not engagement.",
  },
  {
    date: "2026-09-27",
    kind: "entry",
    title: "The entrypoints wrote the task into the shared workspace",
    body:
      "In a phased pair the victim's preamble overwrote the attacker's prompt file before aider " +
      "had read it, so the attacker received the victim's instructions, declined them, and " +
      "exited cleanly having planted nothing, four times in a row, while the barrier released " +
      "on the prompt file itself. The task now lands on the container's private tmpfs, and the " +
      "barrier releases only on the files a scenario declares.",
  },
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
