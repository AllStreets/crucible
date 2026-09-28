import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return walk(path);
    return path.endsWith(".tsx") ? [path] : [];
  });
}

test("no component hardcodes a figure", () => {
  // The site's credibility rests on every number being a query. A numeral
  // typed into JSX text is a number nobody can trace to a row, and it is
  // exactly how a presentation drifts from its dataset without anyone
  // noticing. Figure numbers and years are the only exceptions, because
  // neither is a measurement.
  const offenders: string[] = [];
  for (const file of [...walk("app"), ...walk("components")]) {
    const src = readFileSync(file, "utf8");
    const body = src.split("<style>")[0];
    // The > must close a JSX tag, which means it sits directly against the
    // tag's last character. A > with a space before it is a comparison, and
    // an arrow function's > follows an equals sign. Both were matched by
    // earlier drafts of this pattern, so every sort comparator and every
    // length check in the file read as a hardcoded figure.
    // Line by line, because the pattern is allowed to cross nothing. Run over
    // the whole file it spanned newlines, so a TypeScript generic on one line
    // could close a match that began on another and a hook declaration read as
    // JSX text. Real JSX text that states a figure sits on one line.
    for (const line of body.split("\n")) {
      for (const m of line.matchAll(/(?<=[A-Za-z0-9"'\/}\]])>[^<>{}]*\b\d+(?:\.\d+)?\b[^<>{}]*</g)) {
        if (/Figure \d|20\d\d/.test(m[0])) continue;
        offenders.push(`${file}: ${m[0].trim().slice(0, 70)}`);
      }
    }
  }
  expect(offenders, `\n${offenders.join("\n")}`).toEqual([]);
});

test("the research log states no figure", () => {
  // Prose in the log is written by hand, so a count typed there is precisely
  // the untraceable number this site must not carry.
  const src = readFileSync("lib/log.ts", "utf8");
  const bodies = [...src.matchAll(/body:\s*((?:"[^"]*"\s*\+?\s*)+)/g)].map((m) => m[1]);
  for (const body of bodies) {
    // Words are fine, digits are not.
    expect(/\b\d+\b/.test(body), `a figure appears in a log body: ${body.slice(0, 60)}`)
      .toBe(false);
  }
});
