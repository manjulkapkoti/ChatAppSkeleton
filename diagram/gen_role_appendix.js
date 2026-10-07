// Reads the same elements JSON the diagram is drawn from and injects a
// "Box reference" appendix (role + responsibility, grouped by section) into
// the already-generated HTML, right before </body>. Run this AFTER svg_gen.js
// on every regen — it does not draw anything itself.
// Usage: node gen_role_appendix.js <elements.json> <diagram.html>
const fs = require("fs");
const [, , inFile, htmlFile] = process.argv;
const els = JSON.parse(fs.readFileSync(inFile, "utf8"));

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Group boxes by `section`, preserving first-seen order (Map does this natively).
const sections = new Map();
for (const el of els) {
  if (el.type !== "rectangle" || !el.role) continue;
  if (!sections.has(el.section)) sections.set(el.section, []);
  sections.get(el.section).push(el.role);
}

let html = `<section class="appendix">
<h2>Box reference — role &amp; responsibility of every box above</h2>
<p class="appendix-note">Generated from the same JSON the diagram is drawn from — edit a box's <code>role</code> field there, not here.</p>`;

for (const [section, items] of sections) {
  html += `\n<h3>${esc(section)}</h3>\n<ul>\n`;
  for (const { title, text, file } of items) {
    html += `<li><strong>${esc(title)}</strong> — ${esc(text)}${file ? ` <code>${esc(file)}</code>` : ""}</li>\n`;
  }
  html += `</ul>\n`;
}
html += `</section>\n`;

const css = `<style>
  .appendix { background: #ffffff; border-radius: 16px; padding: 24px 28px; box-shadow: 0 8px 30px rgba(15,23,42,.08); max-width: 1240px; width: 100%; margin-top: 20px; box-sizing: border-box; }
  .appendix h2 { font-size: 19px; margin: 0 0 4px; color: #111827; }
  .appendix-note { font-size: 12.5px; color: #94a3b8; margin: 0 0 18px; }
  .appendix h3 { font-size: 14px; letter-spacing: .3px; text-transform: uppercase; color: #7c3aed; margin: 22px 0 8px; }
  .appendix h3:first-of-type { margin-top: 0; }
  .appendix ul { margin: 0 0 4px; padding-left: 20px; }
  .appendix li { font-size: 14px; line-height: 1.55; color: #374151; margin-bottom: 8px; }
  .appendix li strong { color: #111827; }
  .appendix li code { display: inline-block; margin-left: 6px; font-size: 12.5px; background: #f1f5f9; color: #475569; padding: 1px 6px; border-radius: 4px; }
</style>`;

let page = fs.readFileSync(htmlFile, "utf8");
if (!page.includes('class="appendix"')) {
  page = page.replace("</head>", `${css}\n</head>`);
  page = page.replace("<footer>", `${html}<footer>`);
} else {
  // Re-running after a diagram edit: replace the previous appendix + its style block.
  page = page.replace(/<style>\n {2}\.appendix[\s\S]*?<\/style>\n/, `${css}\n`);
  page = page.replace(/<section class="appendix">[\s\S]*?<\/section>\n/, html);
}
fs.writeFileSync(htmlFile, page);
console.log(`injected role appendix (${sections.size} sections) into ${htmlFile}`);
