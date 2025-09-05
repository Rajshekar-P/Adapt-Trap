// server.js
const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const fs = require("fs");
const os = require("os");
const { MongoClient } = require("mongodb");
const multer = require("multer");
const crypto = require("crypto");
const mime = require("mime-types");

const app = express();
const PORT = process.env.PORT || 80;

// ---- CONFIG ---------------------------------------------------------------
const MONGO_URI  = process.env.MONGO_URI  || "mongodb://127.0.0.1:27017";
const DB_NAME    = process.env.DB_NAME    || "adapttrap";
const COLLECTION = process.env.COLLECTION || "nodepot_logs";

const BRAND_NAME = process.env.BRAND_NAME || "Acme NetSecure Appliance";
const APP_SLOGAN = process.env.APP_SLOGAN || "Unified edge security & telemetry";
const MAX_UPLOAD = parseInt(process.env.MAX_UPLOAD || "10485760", 10); // 10MB

// expose brand/slogan everywhere
app.locals.brand  = BRAND_NAME;
app.locals.slogan = APP_SLOGAN;

// also expose host/remote per-request
app.use((req, res, next) => {
  res.locals.host = process.env.BRAND_HOST
    || req.headers["x-forwarded-host"]
    || req.hostname
    || req.headers.host
    || os.hostname();
  res.locals.remote = req.headers["x-forwarded-for"]?.split(",")[0]?.trim()
    || req.ip
    || req.connection?.remoteAddress
    || "unknown";
  next();
});

// ---- MongoDB --------------------------------------------------------------
let db, logs;
MongoClient.connect(MONGO_URI)
  .then((client) => {
    db = client.db(DB_NAME);
    logs = db.collection(COLLECTION);
    console.log("[+] Connected to MongoDB");
  })
  .catch((err) => console.error("MongoDB connection error:", err));

// ---- Express / EJS --------------------------------------------------------
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.json());
app.set("trust proxy", true);

app.use("/static", express.static(path.join(__dirname, "static")));
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "templates"));

const uploadsDir = process.env.UPLOADS_DIR || path.join(__dirname, "uploads");
if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadsDir),
  filename: (_req, file, cb) => {
    const safe = (file.originalname || "upload.bin").replace(/[^\w.\-]+/g, "_");
    cb(null, `${Date.now()}__${safe}`);
  },
});
const upload = multer({ storage, limits: { fileSize: MAX_UPLOAD } });

// ---- helpers --------------------------------------------------------------
function clientIp(req) {
  return req.headers["x-forwarded-for"]?.split(",")[0]?.trim()
      || req.ip || req.connection?.remoteAddress || "unknown";
}

async function logEvent(doc) {
  try { if (logs) await logs.insertOne(doc); }
  catch (e) { console.error("[-] Mongo insert error:", e.message); }
}

// model the dashboard expects (matches your EJS)
function dashboardModel(msg = null) {
  return {
    msg,
    systemOk: true,
    firewallEnabled: true,
    stats: {
      connected: !!db,        // crude “connected” flag
      coll: COLLECTION
    },
    sessions: [
      "admin@192.168.0.101 - Session #3145",
      "root@10.10.10.1 - Session #2988"
    ],
    lastFailed: "12 mins ago"
  };
}
const renderDashboard = (res, msg = null) =>
  res.render("dashboard", dashboardModel(msg));

// ---- routes ---------------------------------------------------------------
app.get("/", (_req, res) => res.render("login"));
app.get("/dashboard", (_req, res) => renderDashboard(res));

app.post("/login", async (req, res) => {
  const { username, password } = req.body || {};
  const ip = clientIp(req);
  await logEvent({
    timestamp: new Date(),
    source: "nodepot-lite",
    event_type: "login_attempt",
    ip, method: "POST", uri: "/login",
    username, password,
    raw_log: `Login attempt from ${ip} with username=${username} & password=${password}`,
  });
  console.log("[✓] Captured Login:", { username, password, ip });
  return renderDashboard(res); // render with the full model
});

app.get("/upload", (_req, res) => {
  res.send(`<!doctype html><html><head><meta charset="utf-8">
  <title>${BRAND_NAME} — Upload</title><link rel="stylesheet" href="/static/styles.css">
  </head><body class="theme"><div class="card">
  <h3>Upload a file</h3>
  <form action="/upload" method="POST" enctype="multipart/form-data">
    <input type="file" name="file" /><button type="submit">Upload</button>
  </form>
  <p><a href="/dashboard">Back to Dashboard</a></p></div></body></html>`);
});

app.post("/upload", upload.any(), async (req, res) => {
  const ip = clientIp(req);
  try {
    const file = req.files?.find(f => f.fieldname === "file") || req.files?.[0];
    if (!file) {
      await logEvent({ timestamp:new Date(), source:"nodepot-lite",
        event_type:"upload_error", ip, method:"POST", uri:"/upload",
        error:"No file provided (missing multipart form-data)" });
      return renderDashboard(res, "No file uploaded. Choose a file and submit.");
    }

    const storedName = file.filename;
    const original   = file.originalname || storedName;
    const filePath   = path.join(uploadsDir, storedName);
    const stats      = await fs.promises.stat(filePath);
    const size       = stats.size;
    const mimetype   = file.mimetype || mime.lookup(original) || "application/octet-stream";
    const sha256     = crypto.createHash("sha256").update(await fs.promises.readFile(filePath)).digest("hex");

    await logEvent({
      timestamp:new Date(), source:"nodepot-lite", event_type:"file_upload",
      ip, method:"POST", uri:"/upload",
      filename: original, stored_as: storedName, size, mimetype, sha256,
      raw_log:`Upload from ${ip} of ${original} (${mimetype}, ${size} bytes)`
    });

    return renderDashboard(res, `Uploaded: ${original} (sha256=${sha256})`);
  } catch (e) {
    console.error("Upload handler error:", e);
    await logEvent({ timestamp:new Date(), source:"nodepot-lite",
      event_type:"upload_exception", ip, method:"POST", uri:"/upload", error: e.message });
    return renderDashboard(res, "Server error while handling upload.");
  }
});

app.get("/healthz", (_req, res) => res.json({ ok: true }));

process.on("uncaughtException", (err) => console.error("uncaughtException:", err));
process.on("unhandledRejection", (err) => console.error("unhandledRejection:", err));

app.listen(PORT, () => console.log(`Fake honeypot running on port ${PORT}`));
