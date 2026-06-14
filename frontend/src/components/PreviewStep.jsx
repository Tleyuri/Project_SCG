import { useState } from "react";

const fmt = (n) => Number(n || 0).toLocaleString("th-TH", { maximumFractionDigits: 2 });

export default function PreviewStep({ result, onBack, onDownload, downloading }) {
  const plants = Object.keys(result?.plants || {});
  const [activePlant, setActivePlant] = useState(plants[0]);

  if (!result || plants.length === 0) {
    return (
      <div className="card">
        <h2>3. ตรวจสอบผลการถอดวัสดุ</h2>
        <p className="muted">ไม่พบข้อมูลที่ถอดได้ - ตรวจสอบ layer mapping หรือไฟล์ DXF</p>
        <button className="btn secondary" onClick={onBack}>
          ย้อนกลับ
        </button>
      </div>
    );
  }

  const current = result.plants[activePlant] || { rows: [], plant_counts: {} };
  const grandTotal = (current.rows || []).reduce((sum, r) => sum + (r.total || 0), 0);

  return (
    <div className="card">
      <h2>3. ตรวจสอบผลการถอดวัสดุ (BOQ)</h2>

      {result.legend_bbox && (
        <p className="muted">
          กรอบ legend ที่ตัดออก: x [{fmt(result.legend_bbox[0])}, {fmt(result.legend_bbox[2])}], y
          [{fmt(result.legend_bbox[1])}, {fmt(result.legend_bbox[3])}]
        </p>
      )}

      {result.warnings?.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          {result.warnings.map((w, i) => (
            <div className="warn-box" key={i}>
              ⚠️ {w.message}
            </div>
          ))}
        </div>
      )}

      <div className="tabs">
        {plants.map((p) => (
          <button
            key={p}
            className={`tab${p === activePlant ? " active" : ""}`}
            onClick={() => setActivePlant(p)}
          >
            {p}
          </button>
        ))}
      </div>

      {Object.keys(current.plant_counts || {}).length > 0 && (
        <div className="muted" style={{ marginBottom: 8 }}>
          จำนวนต้น:{" "}
          {Object.entries(current.plant_counts)
            .map(([layer, info]) => `${layer} ${info.count} ต้น (ตัด legend ${info.excluded_legend})`)
            .join(" / ")}
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>ลำดับที่</th>
            <th>Mat.code</th>
            <th>ชื่อรายการ</th>
            <th>จำนวน</th>
            <th>หน่วยนับ</th>
            <th>หมายเหตุ</th>
            <th>ราคา/ชั้น</th>
            <th>รวม</th>
          </tr>
        </thead>
        <tbody>
          {(current.rows || []).map((r, i) => (
            <tr key={i} style={r.note?.includes("ตรวจสอบ") ? { background: "#fff7e6" } : undefined}>
              <td>{i + 1}</td>
              <td>{r.mat_code}</td>
              <td>{r.name}</td>
              <td>{fmt(r.qty)}</td>
              <td>{r.unit}</td>
              <td>{r.note}</td>
              <td>{fmt(r.unit_price)}</td>
              <td>{fmt(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="summary-row">รวมทั้งหมด: {fmt(grandTotal)} บาท</div>

      <div className="toolbar" style={{ marginTop: 16 }}>
        <button className="btn secondary" onClick={onBack}>
          ย้อนกลับ
        </button>
        <button className="btn accent" onClick={onDownload} disabled={downloading}>
          {downloading ? "กำลังสร้างไฟล์..." : "ดาวน์โหลด Excel"}
        </button>
      </div>
    </div>
  );
}
