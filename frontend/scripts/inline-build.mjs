import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const distDir = path.join(root, "dist");
const outDir = path.join(root, "dist-single");

function assetPath(src) {
  return path.join(distDir, src.replace(/^\//, ""));
}

let html = await readFile(path.join(distDir, "index.html"), "utf8");

html = await replaceAsync(
  html,
  /<link rel="stylesheet" crossorigin href="([^"]+)">/g,
  async (_tag, href) => {
    const css = await readFile(assetPath(href), "utf8");
    return `<style>\n${css}\n</style>`;
  },
);

html = await replaceAsync(
  html,
  /<script type="module" crossorigin src="([^"]+)"><\/script>/g,
  async (_tag, src) => {
    const js = await readFile(assetPath(src), "utf8");
    return `<script type="module">\n${js}\n</script>`;
  },
);

await rm(outDir, { recursive: true, force: true });
await mkdir(outDir, { recursive: true });
await writeFile(path.join(outDir, "index.html"), html, "utf8");

console.log("Created single-file frontend build at dist-single/index.html");

async function replaceAsync(value, regex, replacer) {
  const matches = [...value.matchAll(regex)];
  let output = value;
  for (const match of matches.reverse()) {
    const replacement = await replacer(...match);
    output = output.slice(0, match.index) + replacement + output.slice(match.index + match[0].length);
  }
  return output;
}
