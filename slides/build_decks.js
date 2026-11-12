// Builds one supporting PowerPoint deck per demo topic.
//   NODE_PATH=<dir with pptxgenjs, react-icons, react, react-dom, sharp> node slides/build_decks.js
// Slide text is kept short; the talking points live in the speaker notes.

const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Fa = require("react-icons/fa");
const { applyTheme } = require(process.env.APPLY_THEME);

const ROOT = path.resolve(__dirname, "..");
const IMG = path.join(__dirname, "img");
const OUT = __dirname;
const W = 13.333;
const FOOTER = "Talk 03 · Manipulation and Contact";

const THEME = {
  name: "Isaac Demos",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2333", lt1: "FFFFFF", dk2: "0E1726", lt2: "EEF2F7",
    accent1: "FFC400", accent2: "3D7EA6", accent3: "E0393E", accent4: "2EAD5B",
    accent5: "6B778C", accent6: "F28C28", hlink: "3D7EA6", folHlink: "6B778C",
  },
};

const CREDIT_NAMES = {
  t9_hand: "Richard Greenhill & Hugo Elias, Shadow Robot Co.",
  t3_surgery: "Marcy Sanchez, U.S. Army",
};
const credits = JSON.parse(fs.readFileSync(path.join(IMG, "web", "credits.json")));
function credit(key) {
  const c = credits[key];
  return `Photo: ${CREDIT_NAMES[key] || c.artist} · ${c.license} · Wikimedia Commons`;
}

const iconCache = {};
async function icon(name, hex) {
  const k = name + hex;
  if (!iconCache[k]) {
    const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Fa[name], { color: "#" + hex, size: 256 }));
    const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
    iconCache[k] = "image/png;base64," + buf.toString("base64");
  }
  return iconCache[k];
}

async function pngData(file) {
  const buf = await sharp(file).png().toBuffer();
  return "data:image/png;base64," + buf.toString("base64");
}

function fmt(t) {
  const s = Math.floor(t);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// ---------------------------------------------------------------- deck setup
function newDeck(topic) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Talk 03";
  pres.title = topic.title;
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  const footer = (dark) => [
    { text: { text: FOOTER, options: { x: 0.6, y: 6.95, w: 6, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ];
  const slideNum = { x: 12.13, y: 6.95, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5, align: "right", margin: 0 };

  pres.defineSlideMaster({
    title: "Title Dark",
    background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.7, y: 1.7, w: 5.6, h: 0.5, fontSize: 18, bold: true, color: C.accent1, margin: 0, valign: "top" }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.25, w: 5.8, h: 2.4, fontSize: 40, align: "left", bold: true, color: C.background1, margin: 0, valign: "top", fontFace: THEME.headFontFace }, text: "" } },
      { placeholder: { options: { name: "sub", type: "body", x: 0.7, y: 4.85, w: 5.5, h: 1.4, fontSize: 20, color: C.background2, margin: 0, valign: "top" }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content",
    background: { color: C.background1 },
    objects: [
      ...footer(false),
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.13, h: 0.8, fontSize: 32, bold: true, color: C.text1, margin: 0, valign: "middle", align: "left", fontFace: THEME.headFontFace }, text: "" } },
    ],
    slideNumber: slideNum,
  });
  pres.defineSlideMaster({
    title: "Content Dark",
    background: { color: C.text2 },
    objects: [
      ...footer(true),
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.13, h: 0.8, fontSize: 32, bold: true, color: C.background1, margin: 0, valign: "middle", align: "left", fontFace: THEME.headFontFace }, text: "" } },
    ],
    slideNumber: slideNum,
  });
  pres.defineSlideMaster({
    title: "Photo Split",
    background: { color: C.background1 },
    objects: [
      ...footer(false).map((o) => ({ text: { ...o.text, options: { ...o.text.options, x: 7.0 } } })),
      { placeholder: { options: { name: "title", type: "title", x: 7.0, y: 1.0, w: 5.73, h: 1.7, fontSize: 34, bold: true, color: C.text1, margin: 0, valign: "bottom", align: "left", fontFace: THEME.headFontFace }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 7.0, y: 3.0, w: 5.73, h: 3.4, fontSize: 20, color: C.text1, margin: 0, valign: "top" }, text: "" } },
    ],
    slideNumber: slideNum,
  });
  return { pres, C };
}

// ---------------------------------------------------------------- slide helpers
function shadow() {
  return { type: "outer", color: "000000", opacity: 0.25, blur: 8, offset: 3, angle: 90 };
}

function pic(slide, file, x, y, w, h, extra = {}) {
  slide.addImage({ path: file, x, y, w, h, sizing: { type: "cover", w, h }, shadow: shadow(), ...extra });
}

function caption(slide, C, text, x, y, w, color, align = "left") {
  slide.addText(text, { x, y, w, h: 0.3, fontSize: 10, color: color || C.accent5, margin: 0, isTextBox: true, align });
}

function titleSlide(deck, s, { kicker, title, sub, image, notes, section }) {
  const { pres, C } = deck;
  const slide = pres.addSlide({ masterName: "Title Dark", sectionTitle: section });
  slide.addText(kicker, { placeholder: "kicker" });
  slide.addText(title, { placeholder: "title" });
  slide.addText(sub, { placeholder: "sub" });
  slide.addImage({ path: image, x: 6.9, y: 0, w: W - 6.9, h: 7.5, sizing: { type: "cover", w: W - 6.9, h: 7.5 }, objectName: "Hero image" });
  slide.addNotes(notes);
  return slide;
}

function photoSplit(deck, { title, lines, photo, creditKey, notes, section }) {
  const { pres, C } = deck;
  const slide = pres.addSlide({ masterName: "Photo Split", sectionTitle: section });
  slide.addImage({ path: photo, x: 0, y: 0, w: 6.4, h: 7.5, sizing: { type: "cover", w: 6.4, h: 7.5 }, objectName: "Photo" });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 7.1, w: 6.4, h: 0.4, fill: { color: "000000", transparency: 45 }, line: { type: "none" } });
  caption(slide, C, credit(creditKey), 0.2, 7.15, 6.0, C.background1);
  slide.addText(title, { placeholder: "title" });
  slide.addText(
    lines.map((l, i) => ({ text: l, options: { bullet: false, breakLine: i < lines.length - 1, paraSpaceAfter: 14, bold: i === 0 && lines.length > 1 && false } })),
    { placeholder: "body" }
  );
  slide.addNotes(notes);
  return slide;
}

async function videoSlide(deck, { title, video, cover, captions, notes, section }) {
  const { pres, C } = deck;
  const slide = pres.addSlide({ masterName: "Content Dark", sectionTitle: section });
  slide.addText(title, { placeholder: "title" });
  const vw = 8.2, vh = 4.61;
  slide.addMedia({ type: "video", path: video, x: 0.6, y: 1.45, w: vw, h: vh, cover: await pngData(cover) });
  caption(slide, C, "Click the video to play", 0.6, 6.2, 4, C.accent5);
  slide.addText("Watch for", { x: 9.2, y: 1.45, w: 3.53, h: 0.45, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  const runs = [];
  captions.forEach(([t, label], i) => {
    runs.push({ text: fmt(t) + "  ", options: { bold: true, color: C.accent1 } });
    runs.push({ text: label, options: { color: C.background1, breakLine: i < captions.length - 1 } });
  });
  slide.addText(runs, { x: 9.2, y: 2.05, w: 3.53, h: 4.2, fontSize: 15, margin: 0, valign: "top", paraSpaceAfter: 10, isTextBox: true });
  slide.addNotes(notes);
  return slide;
}

// Row of screenshots with a numbered label under each.
function strip(deck, slide, items, { y = 1.6, h = 3.6, labelColor } = {}) {
  const { pres, C } = deck;
  const gap = 0.3, n = items.length, w = (12.13 - gap * (n - 1)) / n;
  items.forEach((it, i) => {
    const x = 0.6 + i * (w + gap);
    pic(slide, it.img, x, y, w, h, { objectName: `Step ${i + 1} image` });
    slide.addShape(pres.shapes.OVAL, { x, y: y + h + 0.25, w: 0.42, h: 0.42, fill: { color: it.accent || C.accent1 }, line: { type: "none" } });
    slide.addText(String(i + 1), { x, y: y + h + 0.25, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    slide.addText(it.label, { x: x + 0.55, y: y + h + 0.2, w: w - 0.55, h: 0.5, fontSize: 18, bold: true, color: labelColor || C.text1, margin: 0, valign: "middle", isTextBox: true });
    if (it.sub) slide.addText(it.sub, { x: x + 0.55, y: y + h + 0.7, w: w - 0.55, h: 0.4, fontSize: 14, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
  });
}

// Rounded box with an icon in a yellow circle and a short label.
async function iconBox(deck, slide, { x, y, w, h, iconName, title, sub, fill, titleColor }) {
  const { pres, C } = deck;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.15, fill: { color: fill || C.background2 }, line: { type: "none" } });
  const d = 0.8;
  slide.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + (h - d) / 2, w: d, h: d, fill: { color: C.accent1 }, line: { type: "none" } });
  slide.addImage({ data: await icon(iconName, THEME.colors.dk2), x: x + 0.3 + 0.2, y: y + (h - d) / 2 + 0.2, w: 0.4, h: 0.4 });
  slide.addText(
    [{ text: title, options: { bold: true, fontSize: 20, color: titleColor || C.text1, breakLine: !!sub } }].concat(sub ? [{ text: sub, options: { fontSize: 15, color: C.accent5 } }] : []),
    { x: x + 1.3, y, w: w - 1.45, h, margin: 0, valign: "middle", isTextBox: true }
  );
}

function arrow(deck, slide, x1, y1, x2, y2, color, width = 3) {
  const { pres } = deck;
  const flipH = x2 < x1, flipV = y2 < y1;
  slide.addShape(pres.shapes.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipH, flipV,
    line: { color, width, endArrowType: "triangle" },
  });
}

function bigStat(deck, slide, { x, y, w, value, label, color }) {
  const { C } = deck;
  slide.addText(value, { x, y, w, h: 1.2, fontSize: 60, bold: true, color: color || C.accent2, margin: 0, isTextBox: true, fontFace: THEME.headFontFace });
  slide.addText(label, { x, y: y + 1.25, w, h: 0.8, fontSize: 18, color: C.text1, margin: 0, valign: "top", isTextBox: true });
}

async function finish(deck, file) {
  const out = path.join(OUT, file);
  await deck.pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
}

const im = (f) => path.join(IMG, f);
const web = (f) => path.join(IMG, "web", f);
const vid = (f) => path.join(ROOT, "videos", "edited", f);
const narrated = (f) => path.join(ROOT, "videos", "narrated", f);  // voice-over + captions

// ================================================================ Topic 3
async function topic3() {
  const deck = newDeck({ title: "Topic 3 · Robot Kinematics" });
  const { pres, C } = deck;

  pres.addSection({ title: "Intro" });
  titleSlide(deck, null, {
    section: "Intro", kicker: "TOPIC 3", title: "Robot Kinematics",
    sub: "From “put your hand there” to seven joint angles", image: im("t3_00315.jpg"),
    notes: "This is a Franka Panda, a common research arm with 7 joints. Kinematics is the geometry of motion: how joint angles relate to where the hand ends up. No forces yet, just geometry.",
  });

  photoSplit(deck, {
    section: "Intro", title: "Arms that put a tool exactly there",
    lines: ["Car factories: welding torches on every seam", "Surgery: instrument tips moved by a surgeon", "Same question each time: how should the joints move?"],
    photo: web("t3_factory.jpg"), creditKey: "t3_factory",
    notes: "Welding robots on a car body line follow seams to the millimetre. Surgical robots turn the surgeon's hand motion into instrument-tip motion. In both, someone specifies where the tool must be, and the robot must work out the joint angles.",
  });

  pres.addSection({ title: "Concept" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("Two directions of one question", { placeholder: "title" });
    const bx = (x, y, label, sub, fill, tc) => {
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.5, h: 1.2, rectRadius: 0.15, fill: { color: fill }, line: { type: "none" } });
      slide.addText([{ text: label, options: { bold: true, fontSize: 20, color: tc, breakLine: true } }, { text: sub, options: { fontSize: 14, color: tc } }],
        { x, y, w: 2.5, h: 1.2, align: "center", valign: "middle", margin: 0.05, isTextBox: true });
    };
    // Forward kinematics row
    slide.addText("Forward kinematics", { x: 0.6, y: 1.55, w: 6.6, h: 0.45, fontSize: 20, bold: true, color: C.accent2, margin: 0, isTextBox: true });
    bx(0.6, 2.1, "Joint angles", "7 numbers", C.background2, C.text1);
    arrow(deck, slide, 3.25, 2.7, 4.45, 2.7, C.accent2, 4);
    bx(4.6, 2.1, "Hand position", "where it ends up", C.background2, C.text1);
    slide.addText("Easy: one answer", { x: 0.6, y: 3.4, w: 6.5, h: 0.4, fontSize: 15, color: C.accent5, margin: 0, isTextBox: true });
    // Inverse kinematics row
    slide.addText("Inverse kinematics (IK)", { x: 0.6, y: 4.0, w: 6.6, h: 0.45, fontSize: 20, bold: true, color: C.accent6, margin: 0, isTextBox: true });
    bx(0.6, 4.55, "Hand target", "the red cube", C.text2, C.background1);
    arrow(deck, slide, 3.25, 5.15, 4.45, 5.15, C.accent6, 4);
    bx(4.6, 4.55, "Joint angles", "?", C.text2, C.background1);
    slide.addText("Hard: none, one, or many answers", { x: 0.6, y: 5.85, w: 6.5, h: 0.4, fontSize: 15, color: C.accent5, margin: 0, isTextBox: true });
    pic(slide, im("t3_00441.jpg"), 7.75, 1.6, 4.98, 4.65, { objectName: "Arm reaching the target" });
    slide.addNotes("Forward kinematics: give me the joint angles and I tell you where the hand is. One answer, simple trigonometry. Inverse kinematics is the reverse and is what we actually need: we know where the hand should go and ask which joint angles get it there. There may be no answer (too far), one, or infinitely many. The demo solves IK continuously as the cube moves.");
  }

  pres.addSection({ title: "Demo" });
  await videoSlide(deck, {
    section: "Demo", title: "Demo: follow the red cube", video: vid("01_follow_target.mp4"), cover: im("cover_01_follow_target.jpg"),
    captions: [[0.3, "Cube = hand goal"], [3.8, "Only WHERE is given"], [11.2, "IK re-solved 60× a second"], [18, "Many poses, one point"], [24.6, "Cube leaves the workspace"], [30, "Arm stretches, stops"], [35.6, "Back in reach"]],
    notes: "Play the video. Point out that we never tell the robot any joint angle, only where the cube is. Around 0:25 the cube moves about 1.15 m away, beyond the roughly 0.85 m reach: the arm stretches as far as it can and waits. When the cube returns, tracking resumes instantly.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("One controller, every target", { placeholder: "title" });
    strip(deck, slide, [
      { img: im("t3_00063.jpg"), label: "Near" },
      { img: im("t3_00315.jpg"), label: "Far and high" },
      { img: im("t3_00441.jpg"), label: "Low and wide" },
      { img: im("t3_00945.jpg"), label: "Out of reach", accent: C.accent3 },
    ], { y: 1.55, h: 3.9 });
    slide.addNotes("Same code, very different arm shapes. Nobody programmed these poses; IK found them. The last frame is the interesting failure: the target is outside the workspace, so the best the arm can do is point at it.");
  }

  pres.addSection({ title: "Wrap-up" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Wrap-up" });
    slide.addText("Three numbers to remember", { placeholder: "title" });
    bigStat(deck, slide, { x: 0.6, y: 2.4, w: 3.7, value: "7", label: "joints: one more than needed, so many poses fit one target" });
    bigStat(deck, slide, { x: 4.8, y: 2.4, w: 3.7, value: "0.85 m", label: "reach: the edge of the workspace", color: C.accent6 });
    bigStat(deck, slide, { x: 9.0, y: 2.4, w: 3.7, value: "60×", label: "per second the solver updates the joint targets", color: C.accent4 });
    slide.addNotes("6 joints are enough to place a hand anywhere in reach with any orientation; the 7th gives the robot a choice of elbow position, which helps avoid joint limits and obstacles. The workspace is everything the hand can reach. The solver (RMPflow in cuMotion) re-solves 60 times a second, which is why it can chase a moving target.");
  }

  titleSlide(deck, null, {
    section: "Wrap-up", kicker: "TAKEAWAY", title: "Say WHERE. Kinematics works out HOW.",
    sub: "Inverse kinematics turns a target into joint angles, as long as it is within reach.", image: im("t3_00945.jpg"),
    notes: "Recap: forward is easy, inverse is the useful one. Reachability limits what is possible. Next topics build on this: planning adds obstacles, contact adds forces.",
  });

  await finish(deck, "Topic03_Kinematics.pptx");
}

// ================================================================ Topic 4
async function eqImg(slide, file, x, y, h, extra = {}) {
  const m = await sharp(file).metadata();
  const w = (h * m.width) / m.height;
  slide.addImage({ path: file, x: extra.center ? x - w / 2 : x, y, w, h, objectName: extra.name || "Equation" });
  return w;
}

async function topic4() {
  const deck = newDeck({ title: "Topic 4 · Robot Dynamics" });
  const { pres, C } = deck;

  pres.addSection({ title: "Intro" });
  titleSlide(deck, null, {
    section: "Intro", kicker: "TOPIC 4", title: "Robot Dynamics",
    sub: "Forward and inverse dynamics: from torques to motion, and back", image: im("dyn_hover.jpg"),
    notes: "Kinematics told us WHERE the joints must be. Dynamics asks HOW HARD the motors must work to get there, and what happens when forces act on the robot. This arm is floating with no position control at all: its motors give exactly the torque that cancels gravity. By the end you will know how that torque is computed.",
  });

  pres.addSection({ title: "Concept" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("Kinematics said where. Dynamics says how hard", { placeholder: "title" });
    const card = (y, head, body, color) => {
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 6.4, h: 1.25, rectRadius: 0.15, fill: { color: C.background2 }, line: { type: "none" } });
      slide.addText([{ text: head, options: { bold: true, fontSize: 20, color, breakLine: true } }, { text: body, options: { fontSize: 16, color: C.text1 } }],
        { x: 0.9, y, w: 5.9, h: 1.25, margin: 0, valign: "middle", isTextBox: true });
    };
    card(1.55, "Kinematics (topic 3)", "joint angles ↔ hand position. Pure geometry, no mass, no forces", C.accent5);
    card(2.95, "Dynamics (today)", "torques ↔ motion. Mass, inertia, gravity and the motors' effort", C.accent3);
    slide.addText("One joint: Newton's second law, for rotation", { x: 0.6, y: 4.5, w: 6.4, h: 0.4, fontSize: 16, bold: true, color: C.accent5, margin: 0, isTextBox: true });
    await eqImg(slide, im("eq_pendulum.png"), 0.6, 5.0, 0.62, { name: "Pendulum equation" });
    slide.addText("inertia × angular acceleration  +  gravity torque  =  motor torque", { x: 0.6, y: 5.8, w: 6.4, h: 0.4, fontSize: 14, color: C.accent5, margin: 0, isTextBox: true });
    pic(slide, im("dyn_fall.jpg"), 7.5, 1.55, 5.23, 3.2, { objectName: "Arm collapsed with motors off" });
    slide.addText("Motors off (τ = 0): gravity wins", { x: 7.5, y: 4.9, w: 5.23, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true });
    slide.addNotes("Kinematics only dealt with geometry: which joint angles put the hand where. It never asked whether the motors are strong enough, or what happens if they switch off. Dynamics adds mass and forces. For a single joint it is just Newton's F = m a for rotation: the inertia times the angular acceleration, plus the torque gravity creates, equals the torque the motor applies. Switch the motor off, tau becomes zero, and gravity alone decides the motion: the arm on the right collapsed to the floor.");
  }

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("The equation of motion", { placeholder: "title" });
    await eqImg(slide, im("eq_motion.png"), W / 2, 1.65, 0.95, { center: true, name: "Equation of motion" });
    const terms = [
      ["Inertia", "M(q) q̈", "Mass matrix × joint accelerations. M changes with the arm's pose", C.accent2],
      ["Coriolis & centrifugal", "C(q, q̇) q̇", "Appear when several joints move at once; grow with speed²", C.accent6],
      ["Gravity", "g(q)", "Torque needed just to hold the arm up. Depends on pose only", C.accent4],
      ["Motor torques", "τ", "What the actuators apply: one number per joint", C.accent3],
    ];
    const cw = 2.85, gap = 0.243;
    terms.forEach(([name, sym, desc, color], i) => {
      const x = 0.6 + i * (cw + gap);
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.05, w: cw, h: 2.75, rectRadius: 0.15, fill: { color: C.background2 }, line: { color, width: 2.5 }, objectName: name + " card" });
      slide.addText(sym, { x: x + 0.25, y: 3.25, w: cw - 0.5, h: 0.6, fontSize: 26, bold: true, color, margin: 0, isTextBox: true, fontFace: "Cambria" });
      slide.addText(name, { x: x + 0.25, y: 3.9, w: cw - 0.5, h: 0.7, valign: "top", fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true });
      slide.addText(desc, { x: x + 0.25, y: 4.7, w: cw - 0.5, h: 1.0, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true });
    });
    slide.addText("q = joint angles, q̇ = velocities, q̈ = accelerations. One row per joint: 2 for our 2-link arm, 7 for the Franka, 30+ for a humanoid", { x: 0.6, y: 6.05, w: 12.13, h: 0.5, fontSize: 14, color: C.accent5, margin: 0, isTextBox: true });
    slide.addNotes("This is the same F = m a, written for a whole robot. q is the list of joint angles, one per joint. Read it left to right. Inertia: the mass matrix times the joint accelerations; the matrix depends on the pose, because a stretched-out arm is harder to swing than a folded one. Coriolis and centrifugal terms: extra forces that appear when several joints move at the same time; they grow with speed squared, so they matter in fast moves. Gravity: the torque needed just to hold the arm still in a pose. On the right, tau: what the motors apply. Every robot simulator and every torque controller is built on this one line.");
  }

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("One equation, two questions", { placeholder: "title" });
    const bx = (x, y, w, label, sub, fill, tc) => {
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 1.2, rectRadius: 0.15, fill: { color: fill }, line: { type: "none" } });
      slide.addText([{ text: label, options: { bold: true, fontSize: 20, color: tc, breakLine: true } }, { text: sub, options: { fontSize: 14, color: tc } }],
        { x, y, w, h: 1.2, align: "center", valign: "middle", margin: 0.05, isTextBox: true });
    };
    const row = async (y, title, question, color, a, eqFile, b, users) => {
      slide.addText([{ text: title + "   ", options: { bold: true, color } }, { text: question, options: { color: C.text1 } }],
        { x: 0.6, y, w: 12.13, h: 0.45, fontSize: 20, margin: 0, isTextBox: true });
      bx(0.6, y + 0.6, 2.4, a[0], a[1], C.background2, C.text1);
      arrow(deck, slide, 3.1, y + 1.2, 3.6, y + 1.2, color, 4);
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.7, y: y + 0.6, w: 4.4, h: 1.2, rectRadius: 0.15, fill: { color: C.text2 }, line: { type: "none" } });
      await eqImg(slide, eqFile, 5.9, y + 0.95, 0.5, { center: true });
      arrow(deck, slide, 8.2, y + 1.2, 8.7, y + 1.2, color, 4);
      bx(8.8, y + 0.6, 2.2, b[0], b[1], C.background2, C.text1);
      slide.addText([{ text: "Used by", options: { fontSize: 13, color: C.accent5, breakLine: true } }, { text: users, options: { fontSize: 14, color: C.text1 } }],
        { x: 11.2, y: y + 0.6, w: 1.6, h: 1.2, margin: 0, valign: "middle", isTextBox: true });
    };
    await row(1.5, "Forward dynamics", "Given these torques, how will the robot move?", C.accent2,
      ["Torques τ", "what we apply"], im("eq_forward_w.png"), ["Motion", "integrate q̈ → q̇ → q"], "simulators like Isaac Sim");
    await row(3.75, "Inverse dynamics", "To move like this, what torques do I need?", C.accent3,
      ["Motion", "q, q̇, q̈ wanted"], im("eq_inverse_w.png"), ["Torques τ", "for the motors"], "controllers, motor sizing");
    slide.addText("Forward: solve and integrate, step after step.  Inverse: one direct evaluation, fast enough for 1 kHz control loops", { x: 0.6, y: 6.1, w: 12.13, h: 0.45, fontSize: 15, color: C.accent5, margin: 0, isTextBox: true });
    slide.addNotes("Exactly like kinematics, dynamics comes in two directions, and it is the same equation read two ways. Forward dynamics: we know the torques and ask how the robot will move. Solve the equation for the accelerations, then integrate over time to get velocities and angles. That is what a physics simulator such as Isaac Sim's PhysX does thousands of times a second. Inverse dynamics: we know the motion we want, the angles, velocities and accelerations, and ask which torques produce it. Just plug in and multiply, no integration. That is what a torque controller does every millisecond, and what engineers use to size motors.");
  }

  pres.addSection({ title: "Demo" });
  await videoSlide(deck, {
    section: "Demo", title: "The maths, animated", video: narrated("08a_dynamics_math.mp4"), cover: im("cover_08a_dynamics_math.jpg"),
    captions: [[0, "One joint: F = m a"], [26, "Equation, term by term"], [58, "Forward vs inverse"], [86, "Forward: motors off, it falls"], [112, "Inverse: torques for a circle"], [129, "2× speed: inertia ×4"], [146, "The control loop"]],
    notes: "This animation walks through the maths on a two-joint arm simulated with exactly the equation on the previous slides. First a pendulum, then the full equation term by term. In the forward-dynamics part the motors are off: the simulator only solves for the acceleration and integrates, and the arm falls and swings chaotically. In the inverse part we ask for a circle and compute the torques; the bar chart shows each term. Watch what happens when the circle speeds up: the inertia torque roughly quadruples, while the gravity torque stays the same because it depends only on the pose.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Faster moves cost more", { placeholder: "title" });
    pic(slide, im("dyn_math_inverse.jpg"), 0.6, 1.55, 7.6, 4.28, { objectName: "Inverse dynamics animation frame" });
    bigStat(deck, slide, { x: 8.7, y: 1.55, w: 4.0, value: "2× speed", label: "around the same circle", color: C.accent2 });
    bigStat(deck, slide, { x: 8.7, y: 3.75, w: 4.0, value: "≈ 4×", label: "the inertia torque (q̈ grows with speed²); gravity torque unchanged", color: C.accent3 });
    slide.addNotes("Acceleration around a circle grows with the square of the speed, so doubling the speed needs about four times the inertia torque. Gravity torque depends only on where the arm is, not how fast it moves, so it does not change. This is why fast robots need bigger motors and why motion planners limit acceleration.");
  }

  await videoSlide(deck, {
    section: "Demo", title: "Demo: torque-controlled Franka in Isaac Sim", video: narrated("08b_dynamics_franka.mp4"), cover: im("cover_08b_dynamics_franka.jpg"),
    captions: [[9, "τ = 0: forward dynamics, it falls"], [19, "τ = g(q): it floats"], [36, "Computed torque: tracks a wave"], [52, "Base joint: inertia only"]],
    notes: "Now the real 7-joint Franka model in Isaac Sim. We switched off its position controllers and command raw motor torques every 1/120 s. Take one: zero torque. PhysX does forward dynamics and the arm collapses. Take two: we ask Isaac Sim for g(q), the gravity term of the equation, and apply exactly that. Nothing holds the angles in place, yet the arm floats: the shoulder needs about 34 newton-metres. Take three: the full inverse dynamics, computed-torque control, follows a wave on four joints. The plots show the shoulder torque is almost all gravity, while the base joint, which rotates about a vertical axis, has zero gravity torque: everything it needs is inertia.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Three torque commands, three outcomes", { placeholder: "title" });
    strip(deck, slide, [
      { img: im("dyn_fall.jpg"), label: "τ = 0", sub: "Forward dynamics: falls", accent: C.accent3 },
      { img: im("dyn_hover.jpg"), label: "τ = g(q)", sub: "Holds still: floats", accent: C.accent4 },
      { img: im("dyn_track.jpg"), label: "τ = M q̈ + C q̇ + g", sub: "Follows the wave", accent: C.accent2 },
    ], { y: 1.55, h: 3.7 });
    slide.addNotes("Same robot, same simulator, only the torque formula changes. With zero torque the simulator's forward dynamics lets it fall. With the gravity term it holds any pose: the joint angles drifted less than 0.2 degrees in twelve seconds. With the full inverse dynamics plus a little feedback it follows the desired motion, within about 4 degrees at the fastest moments.");
  }

  pres.addSection({ title: "Wrap-up" });
  {
    const slide = pres.addSlide({ masterName: "Content Dark", sectionTitle: "Wrap-up" });
    slide.addText("Both directions, in one loop", { placeholder: "title" });
    const node = (x, w, head, sub, color) => {
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.9, w, h: 1.6, rectRadius: 0.15, fill: { color: "1E2A3D" }, line: { color, width: 2.5 } });
      slide.addText([{ text: head, options: { bold: true, fontSize: 20, color, breakLine: true } }, { text: sub, options: { fontSize: 15, color: C.background2 } }],
        { x, y: 1.9, w, h: 1.6, align: "center", valign: "middle", margin: 0.1, isTextBox: true });
    };
    node(0.6, 3.0, "Desired motion", "q, q̇, q̈ from the planner", C.accent1);
    arrow(deck, slide, 3.7, 2.7, 4.4, 2.7, C.background2, 3);
    node(4.5, 3.7, "Controller", "inverse dynamics: motion → τ", C.accent3);
    arrow(deck, slide, 8.3, 2.7, 9.0, 2.7, C.accent3, 3);
    node(9.1, 3.63, "Robot / simulator", "forward dynamics: τ → motion", C.accent2);
    slide.addText("sensors measure q, q̇ and send them back to the controller", { x: 4.5, y: 3.7, w: 8.23, h: 0.4, fontSize: 15, color: C.accent5, margin: 0, isTextBox: true, align: "right" });
    const cards = [
      ["FaHandPaper", "Gravity compensation", "τ = g(q): cobots feel weightless to hand-guide"],
      ["FaTachometerAlt", "Fast moves cost more", "Inertia torque grows with acceleration"],
    ];
    for (let i = 0; i < cards.length; i++) {
      const [ic, t, s] = cards[i];
      await iconBox(deck, slide, { x: 0.6 + i * 6.23, y: 4.5, w: 5.9, h: 1.8, iconName: ic, title: t, sub: s, fill: "1E2A3D", titleColor: C.background1 });
    }
    slide.addNotes("In a real robot both directions run together. The planner says what motion we want. The controller uses inverse dynamics to turn it into torques. The robot, or the simulator standing in for it, is forward dynamics: physics answering back with the actual motion. Sensors close the loop. Two practical consequences: gravity compensation lets collaborative robots feel weightless so people can push them around by hand, and fast moves need disproportionately more torque.");
  }

  titleSlide(deck, null, {
    section: "Wrap-up", kicker: "TAKEAWAY", title: "Forward: torques → motion. Inverse: motion → torques",
    sub: "Simulators run forward dynamics; controllers run inverse dynamics.", image: im("dyn_track.jpg"),
    notes: "Recap: one equation of motion, read two ways. Forward dynamics predicts motion from torques, which is what Isaac Sim does. Inverse dynamics computes the torques a motion needs, which is what controllers do. Next, contact: what happens when the robot touches the world.",
  });

  await finish(deck, "Topic04_Dynamics.pptx");
}

// ================================================================ Topic 7
async function topic7() {
  const deck = newDeck({ title: "Topic 7 · Collision Checking & Motion Planning" });
  const { pres, C } = deck;

  pres.addSection({ title: "Intro" });
  titleSlide(deck, null, {
    section: "Intro", kicker: "TOPIC 7", title: "Collision Checking & Motion Planning",
    sub: "Getting from A to B without hitting anything", image: im("t7_wall_00380.jpg"),
    notes: "Last topic answered where the joints should be for one target. Now: how do we move from here to there when something is in the way?",
  });

  photoSplit(deck, {
    section: "Intro", title: "Like finding your way through a maze",
    lines: ["Know where the walls are", "Check each step before taking it", "Pick a route that gets there safely"],
    photo: web("t7_maze.jpg"), creditKey: "t7_maze",
    notes: "A maze is a good mental model. You need a map of the walls, a way to tell whether a step hits a wall, and a strategy to choose a route. A robot arm does the same, except its 'body' is a chain of links that all must avoid obstacles.",
  });

  pres.addSection({ title: "Concept" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("How the robot plans", { placeholder: "title" });
    await iconBox(deck, slide, { x: 0.6, y: 1.6, w: 5.9, h: 1.3, iconName: "FaCubes", title: "1  Model the world", sub: "Robot and obstacles as simple shapes" });
    await iconBox(deck, slide, { x: 0.6, y: 3.15, w: 5.9, h: 1.3, iconName: "FaExclamationTriangle", title: "2  Check collisions", sub: "Do any shapes overlap? Thousands of checks a second" });
    await iconBox(deck, slide, { x: 0.6, y: 4.7, w: 5.9, h: 1.3, iconName: "FaRoute", title: "3  Choose a path", sub: "Safe, smooth, and short" });
    pic(slide, im("t7_wall_00170.jpg"), 6.95, 1.6, 5.78, 4.4, { objectName: "Arm lifting cube over wall" });
    slide.addNotes("Step 1: the planner keeps a model of the robot's links and every obstacle, usually as spheres and boxes. Step 2: collision checking tests whether any of those shapes overlap for a candidate pose. It is cheap and runs thousands of times per second. Step 3: the planner picks a motion that stays collision-free. In the demo we used RMPflow, a reactive planner: obstacles push the arm away, the goal pulls it in.");
  }

  pres.addSection({ title: "Demo" });
  await videoSlide(deck, {
    section: "Demo", title: "Demo: same task, add a wall", video: vid("02_obstacle_planning.mp4"), cover: im("cover_02_obstacle_planning.jpg"),
    captions: [[0.3, "The task"], [3.8, "No obstacle"], [11, "Now add a wall"], [15.6, "Up and over"], [20.6, "Same task, new route"]],
    notes: "First take: no wall, the blue dots trace a low, direct path. Second take: a wall appears between the cube and the green pad. Nothing else changes in the code, only the world model. The yellow path lifts up and over.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Same start, same goal, different route", { placeholder: "title" });
    strip(deck, slide, [
      { img: im("t7_open_00323.jpg"), label: "No wall", sub: "Low and direct (blue)", accent: C.accent2 },
      { img: im("t7_wall_00380.jpg"), label: "Wall", sub: "Up and over (yellow)" },
    ], { y: 1.5, h: 4.15 });
    slide.addNotes("Side by side: the dotted lines are the gripper's path while carrying the cube. Collision checking changed how the robot moved, not what it did. Both runs place the cube on the green pad.");
  }

  pres.addSection({ title: "Wrap-up" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Wrap-up" });
    slide.addText("Where planning matters", { placeholder: "title" });
    const w = 5.9, h = 3.6;
    pic(slide, web("t7_warehouse.jpg"), 0.6, 1.55, w, h, { objectName: "Warehouse robot" });
    pic(slide, web("t7_cobot.jpg"), 6.83, 1.55, w, h, { objectName: "Human-robot collaboration" });
    slide.addText("Warehouses: robots share busy floors", { x: 0.6, y: 5.3, w, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true });
    slide.addText("Next to people: obstacles that move", { x: 6.83, y: 5.3, w, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true });
    caption(slide, C, credit("t7_warehouse"), 0.6, 5.8, w);
    caption(slide, C, credit("t7_cobot"), 6.83, 5.8, w);
    slide.addNotes("Warehouse drive units plan paths among each other. Collaborative robots must re-plan constantly because people move. A limitation worth mentioning: when we raised the wall to 42 cm, our reactive planner got stuck behind it and gave up. Reactive planners are fast but can get trapped; global planners (RRT, or GPU planners like cuRobo) search the whole space and find a way out, at more compute cost.");
  }

  titleSlide(deck, null, {
    section: "Wrap-up", kicker: "TAKEAWAY", title: "Collision checking changes HOW, not WHAT",
    sub: "Know the obstacles, check every move, pick a safe path.", image: im("t7_wall_00170.jpg"),
    notes: "Recap: model the world, check collisions, choose a path. Tall obstacles show the trade-off between fast reactive planners and slower global ones.",
  });

  await finish(deck, "Topic07_Collision_Planning.pptx");
}

// ================================================================ Topic 9
async function topic9() {
  const deck = newDeck({ title: "Topic 9 · Contact Mechanics & Friction" });
  const { pres, C } = deck;

  pres.addSection({ title: "Intro" });
  titleSlide(deck, null, {
    section: "Intro", kicker: "TOPIC 9", title: "Contact Mechanics & Friction",
    sub: "Why a grasped object stays put, and when it slips", image: im("t9_grip_00187.jpg"),
    notes: "Planning gets the gripper to the object. Now the hand touches it, and physics takes over: contact forces and friction decide whether the object comes along.",
  });

  photoSplit(deck, {
    section: "Intro", title: "Holding = squeeze + friction",
    lines: ["Too loose: it slips", "Too tight: it breaks", "Robots need the right balance"],
    photo: web("t9_hand.jpg"), creditKey: "t9_hand",
    notes: "A robot hand holding a light bulb: squeeze too hard and it shatters, too gently and it slides out. People do this balance without thinking; robots need it modelled or sensed.",
  });

  pres.addSection({ title: "Concept" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("What holds the cube up?", { placeholder: "title" });
    // force diagram
    const cx = 2.6, cy = 2.6, s = 1.8;
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: cy, w: s, h: s, fill: { color: C.accent3 }, line: { type: "none" }, objectName: "Cube" });
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx - 0.55, y: cy - 0.6, w: 0.55, h: s + 0.9, rectRadius: 0.08, fill: { color: C.accent5 }, line: { type: "none" }, objectName: "Left finger" });
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx + s, y: cy - 0.6, w: 0.55, h: s + 0.9, rectRadius: 0.08, fill: { color: C.accent5 }, line: { type: "none" }, objectName: "Right finger" });
    arrow(deck, slide, cx - 1.75, cy + s / 2, cx - 0.65, cy + s / 2, C.text1, 4);
    arrow(deck, slide, cx + s + 1.65, cy + s / 2, cx + s + 0.6, cy + s / 2, C.text1, 4);
    slide.addText("squeeze", { x: cx - 1.95, y: cy + s / 2 - 0.55, w: 1.4, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true });
    slide.addText("squeeze", { x: cx + s + 0.6, y: cy + s / 2 - 0.55, w: 1.4, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, align: "right", isTextBox: true });
    arrow(deck, slide, cx + 0.3, cy + s - 0.15, cx + 0.3, cy + 0.2, C.accent1, 5);
    arrow(deck, slide, cx + s - 0.3, cy + s - 0.15, cx + s - 0.3, cy + 0.2, C.accent1, 5);
    slide.addText("friction", { x: cx + 0.45, y: cy + 0.2, w: 0.95, h: 0.4, fontSize: 15, bold: true, color: C.background1, margin: 0, isTextBox: true });
    arrow(deck, slide, cx + s / 2, cy + s + 0.05, cx + s / 2, cy + s + 1.25, C.text1, 4);
    slide.addText("weight", { x: cx + s / 2 + 0.15, y: cy + s + 0.75, w: 1.3, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true });
    // rule card
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.2, y: 1.7, w: 5.53, h: 4.4, rectRadius: 0.15, fill: { color: C.text2 }, line: { type: "none" } });
    slide.addText("Holds if", { x: 7.6, y: 2.0, w: 4.8, h: 0.5, fontSize: 20, color: C.accent1, bold: true, margin: 0, isTextBox: true });
    slide.addText("friction ≥ weight", { x: 7.6, y: 2.55, w: 4.9, h: 0.9, fontSize: 36, bold: true, color: C.background1, margin: 0, isTextBox: true, fontFace: THEME.headFontFace });
    slide.addText("friction ≤ μ × squeeze", { x: 7.6, y: 3.6, w: 4.9, h: 0.7, fontSize: 26, color: C.background2, margin: 0, isTextBox: true, fontFace: THEME.headFontFace });
    slide.addText("μ (“mu”) = how grippy the two surfaces are", { x: 7.6, y: 4.6, w: 4.9, h: 0.9, fontSize: 18, color: C.background2, margin: 0, isTextBox: true });
    slide.addNotes("The fingers squeeze the cube from both sides. That squeeze (the normal force) does not lift anything by itself, but it lets friction act along the surfaces, pointing up. Friction can grow only up to mu times the squeeze. If that maximum is less than the weight, plus extra force when the arm accelerates, the cube slides. Mu depends on both materials: rubber on dry wood is high, anything wet or oily is low.");
  }

  pres.addSection({ title: "Demo" });
  await videoSlide(deck, {
    section: "Demo", title: "Demo: same grip, less friction", video: vid("03_friction_slip.mp4"), cover: im("cover_03_friction_slip.jpg"),
    captions: [[0, "Only the surface changes"], [3.2, "μ = 1.0: carried"], [11, "μ = 0.3: wet surface"], [15.2, "Slip! The cube drops"], [21.9, "Slow-motion replay"]],
    notes: "Two takes with identical robot code, identical squeeze and identical motion. The only change is the friction coefficient of the cube, from 1.0 to 0.3. In the second take the cube lifts, then slides out as the arm speeds up. Watch the slow-motion replay at the end.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("μ = 0.3: the slip, frame by frame", { placeholder: "title" });
    strip(deck, slide, [
      { img: im("t9_slip_00136.jpg"), label: "Held", accent: C.accent4 },
      { img: im("t9_slip_00142.jpg"), label: "Tilting" },
      { img: im("t9_slip_00147.jpg"), label: "Sliding out", accent: C.accent6 },
      { img: im("t9_slip_00153.jpg"), label: "Dropped", accent: C.accent3 },
    ], { y: 1.55, h: 3.9 });
    slide.addNotes("These frames are a fraction of a second apart. Lifting slowly works, but as the arm accelerates sideways the cube needs more friction than mu = 0.3 can provide. It rotates in the fingers, slides out, and falls short of the green pad.");
  }

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("How grippy is it?", { placeholder: "title" });
    const x0 = 1.0, span = 10.5, ly = 5.05;
    const X = (mu) => x0 + mu * span;
    slide.addShape(pres.shapes.LINE, { x: x0, y: ly, w: span * 1.05, h: 0, line: { color: C.accent5, width: 3 } });
    [0, 0.5, 1.0].forEach((m) => slide.addText(m.toFixed(1), { x: X(m) - 0.4, y: ly + 0.15, w: 0.8, h: 0.35, fontSize: 14, color: C.accent5, align: "center", margin: 0, isTextBox: true }));
    const pts = [
      { mu: 0.05, label: "Ice", color: C.accent2 },
      { mu: 0.3, label: "Wet / oily", color: C.accent3 },
      { mu: 0.5, label: "Wood on wood", color: C.accent5 },
      { mu: 1.0, label: "Rubber", color: C.accent4 },
    ];
    pts.forEach((p) => {
      slide.addShape(pres.shapes.OVAL, { x: X(p.mu) - 0.17, y: ly - 0.17, w: 0.34, h: 0.34, fill: { color: p.color }, line: { color: "FFFFFF", width: 2 } });
      slide.addText(p.label, { x: X(p.mu) - 1.0, y: ly + 0.55, w: 2.0, h: 0.4, fontSize: 16, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
    });
    // demo thumbnails above their points
    const tw = 2.9, th = 2.2;
    pic(slide, im("t9_slip_00153.jpg"), X(0.3) - tw / 2, 1.75, tw, th, { objectName: "Slip take" });
    pic(slide, im("t9_grip_00187.jpg"), X(1.0) - tw / 2, 1.75, tw, th, { objectName: "Grip take" });
    slide.addText("Our slip take", { x: X(0.3) - tw / 2, y: 4.0, w: tw, h: 0.4, fontSize: 15, color: C.accent3, bold: true, align: "center", margin: 0, isTextBox: true });
    slide.addText("Our grip take", { x: X(1.0) - tw / 2, y: 4.0, w: tw, h: 0.4, fontSize: 15, color: C.accent4, bold: true, align: "center", margin: 0, isTextBox: true });
    caption(slide, C, "Values are rough, for intuition only", 0.6, 6.4, 6);
    slide.addNotes("Rough friction coefficients for intuition: ice is around 0.05, wet or oily surfaces around 0.3, dry wood about 0.5, rubber on a dry surface around 1. Our two demo takes sit at 0.3 and 1.0. Real values depend on both surfaces, so treat these as ballpark numbers.");
  }

  await videoSlide(deck, {
    section: "Demo", title: "Demo: a human-like hand, squeezing less", video: vid("05_hand_grasp.mp4"), cover: im("cover_05_hand_grasp.jpg"),
    captions: [[0, "Five-finger Shadow Hand"], [1.7, "Fingers close on the rod"], [4.5, "Support removed"], [7.1, "Squeeze fades"], [10.7, "Starts to slide"], [14.5, "Slow-motion replay"]],
    notes: "Same lesson, now with a human-like hand: the Shadow Hand, 24 joints. The finger motions are scripted, not AI. Once the stand drops away, only friction between fingers and rod holds the rod up. Then we slowly turn down how hard the finger motors may squeeze; the meter on the right shows it. The friction coefficient never changes. Friction grows with squeeze, so at about 1.4 percent of full squeeze, friction falls below the rod's weight and it slides down onto the stand. Behind the scenes: while the fingers close, the rod is made temporarily heavy so the fingers cannot knock it over; it gets its real weight, 250 grams, before the stand drops.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Same friction, less squeeze", { placeholder: "title" });
    strip(deck, slide, [
      { img: im("t5_00720.jpg"), label: "100%", sub: "Held", accent: C.accent4 },
      { img: im("t5_01140.jpg"), label: "18%", sub: "Still held" },
      { img: im("t5_01440.jpg"), label: "1.4%", sub: "Sliding", accent: C.accent6 },
      { img: im("t5_01488.jpg"), label: "1%", sub: "Slipped", accent: C.accent3 },
    ], { y: 1.55, h: 3.6 });
    slide.addNotes("Squeeze is shown as a percentage of the hand's full grip. The robot hand is far stronger than this light rod needs, so it holds until the squeeze is almost gone. Then friction (mu times squeeze) drops below the weight and the rod slides. The topic 3 Franka demo changed friction; this one changes squeeze. Both are terms of the same equation.");
  }

  await videoSlide(deck, {
    section: "Demo", title: "Demo: pushing on rough vs smooth", video: narrated("09_friction_push.mp4"), cover: im("cover_09_friction_push.jpg"),
    captions: [[0, "Same block, same push"], [11, "Rough: big, bumpy force"], [17, "Smooth: tiny, steady force"], [27, "Effort and bumpiness compared"], [38, "Stick-slip"]],
    notes: "Now friction working against the robot. The Franka pushes the same 2 kg block along the same path at the same speed, on two mats: rough, like rubber (mu about 1.0 static, 0.6 sliding), and smooth, like ice or a polished, oily surface (mu about 0.04). The graph is the force the fingers measure on the block, straight from the physics engine. On the rough mat the robot needs about 14 newtons, and the force chatters by about plus or minus 1.7 newtons as the surfaces grip and let go. On the smooth mat it needs well under 1 newton, and the curve is flat.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Rough costs effort, and it's bumpy", { placeholder: "title" });
    pic(slide, im("t9_push_rough.jpg"), 0.6, 1.55, 3.9, 2.2, { objectName: "Rough mat push" });
    pic(slide, im("t9_push_smooth.jpg"), 0.6, 4.05, 3.9, 2.2, { objectName: "Smooth mat push" });
    slide.addText("Rough", { x: 4.8, y: 1.6, w: 2.2, h: 0.45, fontSize: 20, bold: true, color: C.accent3, margin: 0, isTextBox: true });
    slide.addText("Smooth", { x: 4.8, y: 4.1, w: 2.2, h: 0.45, fontSize: 20, bold: true, color: C.accent2, margin: 0, isTextBox: true });
    bigStat(deck, slide, { x: 4.8, y: 1.95, w: 3.6, value: "13.6 N", label: "push force, ripple ± 1.7 N", color: C.accent3 });
    bigStat(deck, slide, { x: 4.8, y: 4.45, w: 3.6, value: "0.65 N", label: "push force, ripple ± 0.01 N", color: C.accent2 });
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.9, y: 1.55, w: 3.83, h: 4.7, rectRadius: 0.15, fill: { color: C.text2 }, line: { type: "none" } });
    slide.addText("Sliding friction", { x: 9.2, y: 1.85, w: 3.3, h: 0.45, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    slide.addText("push ≈ μ × N", { x: 9.2, y: 2.4, w: 3.3, h: 0.8, fontSize: 32, bold: true, color: C.background1, margin: 0, isTextBox: true, fontFace: THEME.headFontFace });
    slide.addText("N ≈ the block's weight. Same block, so effort scales with μ: about 21× more on the rough mat", { x: 9.2, y: 3.35, w: 3.3, h: 1.5, fontSize: 16, color: C.background2, margin: 0, valign: "top", isTextBox: true });
    slide.addText("Bumpiness: grip, let go, grip again (stick-slip)", { x: 9.2, y: 5.0, w: 3.3, h: 1.0, fontSize: 16, color: C.background2, margin: 0, valign: "top", isTextBox: true });
    slide.addNotes("Numbers measured in the simulation while the block was sliding. Sliding friction is roughly mu times the normal force, and the normal force is about the block's weight, 20 newtons, plus a little from the fingers pressing down. With mu 0.6 that is around 12 to 15 newtons; with mu 0.03 it is well under one. The rough surface also makes the force ripple: tiny moments of sticking and releasing, called stick-slip. That's the bumpiness you would feel pushing a box across rubber or carpet, versus gliding it on ice. For a robot: more motor effort, more vibration, and harder force control.");
  }

  pres.addSection({ title: "Wrap-up" });
  {
    const slide = pres.addSlide({ masterName: "Content Dark", sectionTitle: "Wrap-up" });
    slide.addText("How real robots avoid slip", { placeholder: "title" });
    const cards = [
      ["FaHandPaper", "Soft, rubbery fingertips", "Higher μ, more contact area"],
      ["FaCompressArrowsAlt", "Squeeze harder", "Up to what the object can take"],
      ["FaTachometerAlt", "Move gently", "Less acceleration, less force needed"],
      ["FaFingerprint", "Feel the slip", "Touch sensors trigger a correction"],
    ];
    for (let i = 0; i < cards.length; i++) {
      const [ic, t, s] = cards[i];
      await iconBox(deck, slide, { x: 0.6 + (i % 2) * 6.23, y: 1.7 + Math.floor(i / 2) * 2.15, w: 5.9, h: 1.8, iconName: ic, title: t, sub: s, fill: "1E2A3D", titleColor: C.background1 });
    }
    slide.addNotes("Engineers attack every term of the equation: raise mu with soft rubber pads, raise the squeeze when the object is sturdy, lower the required force by moving gently, and add tactile sensors that detect the first micro-slip and tighten the grip. Simulators like Isaac Sim approximate contact; matching real friction is part of the 'sim-to-real' challenge.");
  }

  titleSlide(deck, null, {
    section: "Wrap-up", kicker: "TAKEAWAY", title: "Grip = squeeze × friction",
    sub: "If that can't beat weight and motion, the object slips.", image: im("t9_slip_00147.jpg"),
    notes: "Recap: the gripper's squeeze lets friction hold the object. Low friction or fast motion breaks that balance. Same robot, same code, different surface, different outcome.",
  });

  await finish(deck, "Topic09_Contact_Friction.pptx");
}

// ================================================================ Topic 14
async function topic14() {
  const deck = newDeck({ title: "Topic 14 · Learning Manipulation Policies" });
  const { pres, C } = deck;

  pres.addSection({ title: "Intro" });
  titleSlide(deck, null, {
    section: "Intro", kicker: "TOPIC 14", title: "Learning Manipulation Policies",
    sub: "Robots that learn a skill instead of following a script", image: im("t4_00040.jpg"),
    notes: "Everything so far was engineered by hand: IK, planners, grip forces. Now a different approach: let the robot learn the whole skill from experience.",
  });

  photoSplit(deck, {
    section: "Intro", title: "Learning by reward",
    lines: ["Try something", "Get a treat when it works", "Repeat until it's second nature"],
    photo: web("t14_dog.jpg"), creditKey: "t14_dog",
    notes: "Nobody explains the physics of jumping to an agility dog. It tries, gets a treat when it clears the bar, and improves. Reinforcement learning trains robots the same way, just with a score instead of a treat, and millions of tries in simulation.",
  });

  pres.addSection({ title: "Concept" });
  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("The policy: sense, decide, act", { placeholder: "title" });
    const bw = 3.4, bh = 1.6, by = 1.75, xs = [0.6, 4.97, 9.33];
    const boxes = [
      ["Sense", "Joint angles, drawer position", C.background2, C.text1],
      ["Neural network", "the “policy”", C.text2, C.background1],
      ["Act", "New joint targets", C.background2, C.text1],
    ];
    boxes.forEach(([t, s, fill, tc], i) => {
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: xs[i], y: by, w: bw, h: bh, rectRadius: 0.15, fill: { color: fill }, line: { type: "none" } });
      slide.addText([{ text: t, options: { bold: true, fontSize: 22, color: i === 1 ? C.accent1 : tc, breakLine: true } }, { text: s, options: { fontSize: 15, color: tc } }],
        { x: xs[i], y: by, w: bw, h: bh, align: "center", valign: "middle", margin: 0.1, isTextBox: true });
    });
    arrow(deck, slide, xs[0] + bw + 0.1, by + bh / 2, xs[1] - 0.1, by + bh / 2, C.accent5, 4);
    arrow(deck, slide, xs[1] + bw + 0.1, by + bh / 2, xs[2] - 0.1, by + bh / 2, C.accent5, 4);
    // loop back
    const ly = by + bh + 0.45;
    slide.addShape(pres.shapes.LINE, { x: xs[2] + bw / 2, y: by + bh, w: 0, h: 0.45, line: { color: C.accent5, width: 3 } });
    slide.addShape(pres.shapes.LINE, { x: xs[0] + bw / 2, y: ly, w: xs[2] - xs[0], h: 0, line: { color: C.accent5, width: 3 } });
    arrow(deck, slide, xs[0] + bw / 2, ly, xs[0] + bw / 2, by + bh + 0.05, C.accent5, 3);
    slide.addText("repeats 60 times a second", { x: xs[1], y: ly + 0.05, w: bw, h: 0.4, fontSize: 15, color: C.accent5, align: "center", margin: 0, isTextBox: true });
    pic(slide, im("t4_00016.jpg"), 2.9, 4.4, 3.5, 2.2, { objectName: "Policy reaching handle" });
    pic(slide, im("t4_00028.jpg"), 6.93, 4.4, 3.5, 2.2, { objectName: "Policy pulling drawer" });
    slide.addNotes("A policy is just a function from what the robot senses to what it does next. Here it is a small neural network: it reads the joint angles and speeds and where the drawer and handle are, and outputs new joint targets. It runs in a loop, 60 times a second. There are no hand-written steps like 'move to handle, close gripper, pull'.");
  }

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Concept" });
    slide.addText("How it learned: reinforcement learning", { placeholder: "title" });
    const steps = [["FaRedo", "Try", "Random moves at first"], ["FaTrophy", "Score", "More drawer opened = higher reward"], ["FaBrain", "Improve", "Adjust the network toward what scored"]];
    for (let i = 0; i < steps.length; i++) {
      await iconBox(deck, slide, { x: 0.6, y: 1.6 + i * 1.55, w: 6.2, h: 1.3, iconName: steps[i][0], title: steps[i][1], sub: steps[i][2] });
    }
    bigStat(deck, slide, { x: 7.6, y: 1.6, w: 5.1, value: "Thousands", label: "of robots practising at once, in simulation" });
    bigStat(deck, slide, { x: 7.6, y: 3.95, w: 5.1, value: "~0.5 s", label: "for the trained policy to open the drawer", color: C.accent6 });
    slide.addNotes("Training happened beforehand in Isaac Lab, NVIDIA's robot-learning framework: many simulated robots practise in parallel, each attempt gets a reward, and the network is nudged toward actions that earned more. In our recording the finished policy opens the drawer about 40 cm in roughly half a second. Simulation makes this practical: no broken hardware, and far faster than real time.");
  }

  pres.addSection({ title: "Demo" });
  await videoSlide(deck, {
    section: "Demo", title: "Demo: a trained policy opens a drawer", video: vid("04_learned_policy.mp4"), cover: im("cover_04_learned_policy.jpg"),
    captions: [[0, "Real time: very fast"], [2.6, "4× slow motion"], [5.6, "Trained by reward"], [8.6, "What comes next"]],
    notes: "The real-time part is very fast, under half a second. The slow-motion replay shows the three phases: reach the handle, grip it, pull. Remind the audience that nobody programmed these phases; they emerged from training.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Half a second, three phases", { placeholder: "title" });
    strip(deck, slide, [
      { img: im("t4_00000.jpg"), label: "0.00 s", sub: "Start" },
      { img: im("t4_00016.jpg"), label: "0.27 s", sub: "Reach the handle" },
      { img: im("t4_00028.jpg"), label: "0.47 s", sub: "Grip and pull" },
      { img: im("t4_00040.jpg"), label: "0.67 s", sub: "Drawer open" },
    ], { y: 1.55, h: 3.6 });
    slide.addNotes("Frames from the 60 fps recording. The policy discovered on its own that it should approach the handle, close the gripper, and pull straight back.");
  }

  await videoSlide(deck, {
    section: "Demo", title: "Demo: the same idea, a whole humanoid", video: vid("06_humanoid_walk.mp4"), cover: im("cover_06_humanoid_walk.jpg"),
    captions: [[0, "Unitree H2 humanoid"], [1.7, "Walk forward"], [6.5, "Turn around"], [9.7, "Walk back"], [14.7, "Step sideways"], [17.7, "Stop and balance"]],
    notes: "Same recipe as the drawer, scaled up to a whole body. This is the Unitree H2 walking policy that ships with Isaac Sim, trained with reinforcement learning in Isaac Lab. We only send simple commands: walk forward at half a meter per second, turn, step sideways, stop. The neural network turns each command into joint targets 50 times a second and keeps the robot balanced. Every footstep is also a friction problem, which links back to topic 9.",
  });

  {
    const slide = pres.addSlide({ masterName: "Content", sectionTitle: "Demo" });
    slide.addText("Why it doesn't fall: domain randomization", { placeholder: "title" });
    const cards = [
      ["FaShoePrints", "Floor friction", "Slippery to grippy: μ 0.2 to 1.5"],
      ["FaWeightHanging", "Body weight", "Up to 5 kg extra on the torso"],
      ["FaCogs", "Motor strength", "Every motor a bit stronger or weaker"],
      ["FaWind", "Random pushes", "Shoves of up to 10 N"],
    ];
    for (let i = 0; i < cards.length; i++) {
      const [ic, t, sub] = cards[i];
      await iconBox(deck, slide, { x: 0.6, y: 1.5 + i * 1.22, w: 7.4, h: 1.02, iconName: ic, title: t, sub });
    }
    pic(slide, im("t6_h2_side.jpg"), 8.4, 1.5, 4.33, 4.68, { objectName: "H2 walking" });
    caption(slide, C, "Training changes the world every episode, so the policy can't rely on any one setting", 0.6, 6.35, 11);
    slide.addNotes("These numbers come from the training configuration that ships with this H2 policy. During training, every simulated robot gets a different world: floor friction anywhere from 0.2 to 1.5, its torso 1 kg lighter to 5 kg heavier, body part masses and centers of mass shifted, motor gains and joint friction varied, and random pushes of up to 10 newtons. A policy that walks in all of those worlds is much more likely to work on a real robot, whose exact values we never know. That is how domain randomization helps close the sim-to-real gap.");
  }

  pres.addSection({ title: "Wrap-up" });
  photoSplit(deck, {
    section: "Wrap-up", title: "Beyond reinforcement learning",
    lines: ["Learning from human demonstrations", "Diffusion policies: smooth, multi-step skills", "Vision-language-action models: “open the top drawer”"],
    photo: web("t14_humanoid.jpg"), creditKey: "t14_humanoid",
    notes: "Behavior cloning learns by copying human demonstrations instead of trial and error. Diffusion policies generate whole motion sequences and handle tasks with several valid ways to do them. Vision-language-action models (VLAs) take camera images plus a spoken or typed instruction and output actions, the direction humanoid robots are heading. The open challenge for all of them is the sim-to-real gap: a skill learned in simulation must still work on a real robot.",
  });

  titleSlide(deck, null, {
    section: "Wrap-up", kicker: "TAKEAWAY", title: "Write the goal, not the steps",
    sub: "The robot practises in simulation until the skill emerges.", image: im("t4_00028.jpg"),
    notes: "Recap: a policy maps senses to actions. Reinforcement learning shapes it through trial and reward, mostly in simulation. This complements the classical tools from earlier topics rather than replacing them.",
  });

  await finish(deck, "Topic14_Learned_Policies.pptx");
}

(async () => {
  await topic3();
  await topic4();
  await topic7();
  await topic9();
  await topic14();
})().catch((e) => { console.error(e); process.exit(1); });
