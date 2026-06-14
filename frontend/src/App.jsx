import { useState } from "react";
import "./App.css";
import { APP_VERSION, APP_VERSION_DATE } from "./version";
import UploadStep from "./components/UploadStep";
import LayerMappingStep from "./components/LayerMappingStep";
import PreviewStep from "./components/PreviewStep";
import SettingsPanel from "./components/SettingsPanel";
import { extractBoq, exportBoq, getConfig } from "./api";

const STEP_LABELS = ["อัปโหลดไฟล์", "ตรวจสอบ Layer", "ตรวจสอบ BOQ"];

export default function App() {
  const [step, setStep] = useState(0);
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null); // {session_id, filename, layers}
  const [config, setConfig] = useState(null); // {layer_mapping, pipe_sizes, price_table, settings}
  const [settings, setSettings] = useState(null);
  const [garden, setGarden] = useState({ location: "", phone: "" });
  const [boqResult, setBoqResult] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [downloading, setDownloading] = useState(false);

  async function handleUploaded(data) {
    setSession(data);
    try {
      const cfg = await getConfig();
      setConfig(cfg);
      setSettings(cfg.settings);
      setGarden({
        location: cfg.settings.garden_location || "",
        phone: cfg.settings.garden_phone || "",
      });
      setStep(1);
    } catch (e) {
      setError(e.message);
    }
  }

  async function runExtract() {
    if (!session) return;
    setExtracting(true);
    setError(null);
    try {
      const result = await extractBoq(session.session_id, { settings });
      setBoqResult(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setExtracting(false);
    }
  }

  async function goToPreview() {
    await runExtract();
    setStep(2);
  }

  async function handleDownload() {
    if (!session) return;
    setDownloading(true);
    setError(null);
    try {
      const blob = await exportBoq(session.session_id, {
        settings,
        garden_location: garden.location,
        garden_phone: garden.phone,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = session.filename.replace(/\.dxf$/i, "") + "_BOQ.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>ระบบถอดวัสดุ (BOQ) ระบบน้ำการเกษตรจาก DXF</h1>
          <div className="tagline">อัปโหลด DXF → ตรวจสอบ Layer → ถอดวัสดุ → ดาวน์โหลด Excel</div>
        </div>
        <div className="app-version" title={`อัปเดตล่าสุด ${APP_VERSION_DATE}`}>
          {APP_VERSION}
        </div>
      </header>

      <div className="steps">
        {STEP_LABELS.map((label, i) => (
          <div
            key={label}
            className={`step-pill${i === step ? " active" : i < step ? " done" : ""}`}
          >
            {i + 1}. {label}
          </div>
        ))}
      </div>

      <div className="app-body">
        {error && <div className="error-box">{error}</div>}

        {step === 0 && <UploadStep onUploaded={handleUploaded} setError={setError} />}

        {step === 1 && session && config && (
          <LayerMappingStep
            layers={session.layers}
            layerMapping={config.layer_mapping}
            onBack={() => setStep(0)}
            onNext={goToPreview}
          />
        )}

        {step === 1 && extracting && <div className="card">กำลังถอดวัสดุ...</div>}

        {step === 2 && settings && (
          <SettingsPanel
            settings={settings}
            onChange={setSettings}
            gardenLocation={garden.location}
            gardenPhone={garden.phone}
            onGardenChange={setGarden}
          />
        )}

        {step === 2 && (
          <div className="toolbar">
            <span className="muted">ปรับค่าด้านบนแล้วกดคำนวณใหม่หากต้องการ</span>
            <button className="btn secondary" onClick={runExtract} disabled={extracting}>
              {extracting ? "กำลังคำนวณ..." : "คำนวณใหม่"}
            </button>
          </div>
        )}

        {step === 2 && (
          <PreviewStep
            result={boqResult}
            onBack={() => setStep(1)}
            onDownload={handleDownload}
            downloading={downloading}
          />
        )}
      </div>
    </div>
  );
}
