import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const distDir = path.join(root, "dist");
const outDir = path.join(root, "dist-single");

function assetPath(src) {
  return path.join(distDir, src.replace(/^\//, ""));
}

let html = await readFile(path.join(distDir, "index.html"), "utf8");
html = html.replace("<head>", "<head>\n    <script>window.__TAILORAHUB_SINGLE_FILE__ = true;</script>");
html = html.replace(/\s*<link rel="manifest"[^>]*>/g, "");

html = await replaceAsync(html, /<link rel="(?:icon|apple-touch-icon)"[^>]*>/g, async (tag) => {
  const href = tag.match(/href="([^"]+)"/)?.[1];
  if (!href) return tag;
  const data = await readFile(assetPath(href));
  return tag.replace(href, `data:image/png;base64,${data.toString("base64")}`);
});

html = await replaceAsync(
  html,
  /<link rel="stylesheet" crossorigin href="([^"]+)">/g,
  async (_tag, href) => {
    let css = await readFile(assetPath(href), "utf8");
    css = await inlineAssetUrls(css);
    return `<style>\n${css}\n</style>`;
  },
);

html = await replaceAsync(
  html,
  /<script type="module" crossorigin src="([^"]+)"><\/script>/g,
  async (_tag, src) => {
    let js = await readFile(assetPath(src), "utf8");
    js = await inlineAssetUrls(js);
    return `<script type="module">\n${js}\n</script>`;
  },
);

await rm(outDir, { recursive: true, force: true });
await mkdir(outDir, { recursive: true });
await writeFile(path.join(outDir, "index.html"), html, "utf8");

console.log("Created single-file frontend build at dist-single/index.html");

async function inlineAssetUrls(value) {
  return replaceAsync(value, /\/assets\/[A-Za-z0-9_.-]+\.(?:png|jpg|jpeg|webp|svg)/g, async (assetUrl) => {
    const extension = path.extname(assetUrl).slice(1).replace("jpg", "jpeg");
    const data = await readFile(assetPath(assetUrl));
    return `data:image/${extension};base64,${data.toString("base64")}`;
  });
}

async function replaceAsync(value, regex, replacer) {
  const matches = [...value.matchAll(regex)];
  let output = value;
  for (const match of matches.reverse()) {
    const replacement = await replacer(...match);
    output = output.slice(0, match.index) + replacement + output.slice(match.index + match[0].length);
  }
  return output;
}
