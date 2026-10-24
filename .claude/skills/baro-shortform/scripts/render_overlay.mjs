// 그래픽 레이어를 30fps 투명 PNG로 캡처한다. pipeline.py overlay 가 호출한다.
// 사용: node render_overlay.mjs <template.html> <plan.json> <out_dir> <duration_s>
// - 설치된 Chrome(channel: chrome)을 쓰고 외부 네트워크는 막는다.
// - Playwright 모듈 위치는 PW_MODULE 환경변수(절대 경로)로 받는다.
import { pathToFileURL, fileURLToPath } from "node:url";
import { mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import path from "node:path";

const [tpl, planPath, outDir, durS] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(process.env.PW_MODULE).href);
const here = path.dirname(fileURLToPath(import.meta.url));
const fontUrl = pathToFileURL(path.join(here, "..", "assets", "fonts", "PretendardVariable.woff2")).href;
const handFontUrl = pathToFileURL(path.join(here, "..", "assets", "fonts", "NanumPenScript-Regular.ttf")).href;
const plan = JSON.parse(readFileSync(planPath, "utf8"));
const FPS = plan.fps || 30;
const n = Math.round(Number(durS) * FPS);

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
const page_html = path.join(outDir, "_page.html");
writeFileSync(page_html, readFileSync(tpl, "utf8").replace("__FONT_URL__", fontUrl).replace("__HAND_FONT_URL__", handFontUrl));

const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.route(/^https?:/, (r) => r.abort());
await page.addInitScript(([p, layer]) => { window.PLAN = p; window.LAYER = layer; }, [plan, process.env.LAYER || "all"]);
await page.goto(pathToFileURL(page_html).href);
await page.evaluate(async () => { await document.fonts.load('800 60px "Pretendard"', "교정나이"); if ([...document.fonts].some((f) => f.family.includes("BaroHand"))) await document.fonts.load('60px "BaroHand"', "교정나이"); await document.fonts.ready; });
if (!(await page.evaluate(() => document.fonts.check('800 60px "Pretendard"', "교정")))) throw new Error("Pretendard not loaded");
const overlaps = {};   // "요소 × 요소" → 겹친 프레임 수
for (let i = 0; i < n; i++) {
  const hits = await page.evaluate((t) => { window.renderAt(t); return window.__overlaps ? window.__overlaps() : []; }, i / FPS);
  for (const h of hits) { overlaps[h] ??= { frames: 0, first: i / FPS }; overlaps[h].frames++; }
  await page.screenshot({ path: path.join(outDir, `f${String(i).padStart(5, "0")}.png`), omitBackground: true });
}
await browser.close();
rmSync(page_html);
console.log(JSON.stringify({ frames: n, fps: FPS, font: "Pretendard", overlaps }));
