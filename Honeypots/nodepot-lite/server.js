// server.js
const express = require("express");
const bodyParser = require("body-parser");
const path = require("path");
const fs = require("fs");
const { MongoClient } = require("mongodb");
const multer = require("multer");
const crypto = require("crypto");
const multiUpload = multer({ storage }).any();
const mime = require("mime-types");

const app = express();
const PORT = process.env.PORT || 80;

// --- MongoDB ---
const MONGO_URI = process.env.MONGO_URI || "mongodb://192.168.186.135:27017";
const DB_NAME = process.env.DB_NAME || "adapttrap";
const COLLECTION = process.env.COLLECTION || "nodepot_logs";

let db, logs;

MongoClient.connect(MONGO_URI)
  .then((client) => {
    db = client.db(DB_NAME);
    logs = db.collection(COLLECTION);
    console.log("Connected to MongoDB");
  })
  .catch((err) => console.error("MongoDB connection error:", err));

// --- Express setup ---
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.json());
app.use("/static", express.static(path.join(__dirname, "static")));
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "templates"));

// Trust proxy headers if behind NAT/proxy so req.ip is useful
app.set("trust proxy", true);

// --- Ensure uploads dir exists ---
const uploadsDir = path.join(__dirname, "uploads");
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// --- Multer storage ---
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, uploadsDir);
  },
  filename: function (req, file, cb) {
    // preserve original name but sanitize
    const safe = (file.originalname || "upload.bin").replace(/[^\w.\-]+/g, "_");
    cb(null, `${Date.now()}__${safe}`);
  },
});
const upload = multer({ storage });

// --- Helpers ---
function clientIp(req) {
  return req.headers["x-forwarded-for"]?.split(",")[0]?.trim() || req.ip || req.connection?.remoteAddress || "unknown";
}

async function logEvent(doc) {
  try {
    if (!logs) return;
    await logs.insertOne(doc);
  } catch (e) {
    console.error("[-] Mongo insert error:", e.message);
  }
}

// --- Routes ---

// Login UI
app.get("/", (req, res) => {
  res.render("login");
});

// Handle login POST
app.post("/login", async (req, res) => {
  const { username, password } = req.body || {};
  const ip = clientIp(req);

  await logEvent({
    timestamp: new Date(),
    source: "nodepot-lite",
    event_type: "login_attempt",
    ip,
    method: "POST",
    uri: "/login",
    username,
    password,
    raw_log: `Login attempt from ${ip} with username=${username} & password=${password}`,
  });

  console.log("[✓] Captured Login:", { username, password, ip });
  res.redirect("/dashboard");
});

// Simple dashboard page (existing template)
app.get("/dashboard", (req, res) => {
  res.render("dashboard", { msg: null });
});

// Simple upload page (in case you visit directly)
app.get("/upload", (req, res) => {
  res.send(`
  <html><body style="font-family: sans-serif">
    <h3>Upload a file</h3>
    <form action="/upload" method="POST" enctype="multipart/form-data">
      <input type="file" name="file" />
      <button type="submit">Upload</button>
    </form>
    <p><a href="/dashboard">Back to Dashboard</a></p>
  </body></html>
  `);
});

// Upload handler (robust)
app.post("/upload", multiUpload, async (req, res) => {
  const ip = clientIp(req);

  try {
    // Prefer 'file', otherwise take the first available file
    let file = req.files?.find(f => f.fieldname === "file") || (req.files && req.files[0]);

    if (!file) {
      await logEvent({
        timestamp: new Date(),
        source: "nodepot-lite",
        event_type: "upload_error",
        ip,
        method: "POST",
        uri: "/upload",
        error: "No file provided (missing multipart form-data)"
      });
      return res.status(400).render("dashboard", { msg: "No file uploaded. Please choose a file and submit." });
    }

    const storedName = file.filename;
    const originalName = file.originalname || storedName;
    const filePath = path.join(uploadsDir, storedName);

    const stats = await fs.promises.stat(filePath);
    const filesize = stats.size;
    const mimetype = file.mimetype || mime.lookup(originalName) || "application/octet-stream";

    const buf = await fs.promises.readFile(filePath);
    const sha256 = crypto.createHash("sha256").update(buf).digest("hex");

    await logEvent({
      timestamp: new Date(),
      source: "nodepot-lite",
      event_type: "file_upload",
      ip,
      method: "POST",
      uri: "/upload",
      filename: originalName,
      stored_as: storedName,
      size: filesize,
      mimetype,
      sha256,
      raw_log: `Upload from ${ip} of ${originalName} (${mimetype}, ${filesize} bytes)`
    });

    res.status(200).render("dashboard", { msg: `Uploaded: ${originalName} (sha256=${sha256})` });
  } catch (e) {
    console.error("Upload handler error:", e);
    await logEvent({
      timestamp: new Date(),
      source: "nodepot-lite",
      event_type: "upload_exception",
      ip,
      method: "POST",
      uri: "/upload",
      error: e.message
    });
    res.status(500).render("dashboard", { msg: "Server error while handling upload." });
  }
});

// --- Global error safety (avoid full process crash) ---
process.on("uncaughtException", (err) => console.error("uncaughtException:", err));
process.on("unhandledRejection", (err) => console.error("unhandledRejection:", err));

// --- Start ---
app.listen(PORT, () => {
  console.log(`Fake honeypot running on port ${PORT}`);
});
