import sharp from "sharp";
import { fileURLToPath } from "node:url";

const source = fileURLToPath(new URL("../src/assets/tailorahub-atelier-hero.png", import.meta.url));
const destination = fileURLToPath(new URL("../src/assets/tailorahub-atelier-hero.webp", import.meta.url));

await sharp(source)
  .resize({ width: 1600, withoutEnlargement: true })
  .webp({ quality: 80, effort: 6 })
  .toFile(destination);

const metadata = await sharp(destination).metadata();
console.log(`Optimized hero: ${metadata.width}x${metadata.height} WebP`);
