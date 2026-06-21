import { useMemo, useState } from "react";
import { buildSlots, guessAssignments, applyAssignments } from "../utils/layerGuess";
import { updateLayerMapping } from "../api";

export function EntryTypeSelector({ value, onChange }) {
  const options = [
    { value: "straight", label: "แบบปกติ", desc: "ท่อตรงเข้าหัวสปริงเกอร์ทีละหัว" },
    { value: "y_branch", label: "แบบ 3 ทางวาย", desc: "แยกซ้าย-ขวา 2 หัวต่อจุด" },
  ];
  return (
    <div style={{ margin: "16px 0" }}>
      <label style={{ fontWeight: 500, fontSize: 14 }}>รูปแบบท่อเข้าต้น</label>
      <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
        {options.map((opt) => (
          <label
            key={opt.value}
            style={{
              display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
              border: `1px solid ${value === opt.value ? "var(--color-primary, #16a34a)" : "var(--color-border, #d1d5db)"}`,
              borderRadius: 8, padding: "10px 16px", flex: 1,
              background: value === opt.value ? "var(--color-primary-light, #f0fdf4)" : "transparent",
            }}
          >
            <input
              type="radio"
              name="entry_type"
              value={opt.value}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
            />
            <div>
              <div style={{ fontWeight: 500 }}>{opt.label}</div>
              <div style={{ fontSize: 12, color: "gray" }}>{opt.desc}</div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}

export default function LayerMappingStep({ layers, layerMapping, layerAliases, onBack, onNext, entryType, onEntryTypeChange }) {
  const slots = useMemo(() => buildSlots(layerMapping), [layerMapping]);
  const guesses = useMemo(
    () => guessAssignments(slots, layers, layerAliases),
    [slots, layers, layerAliases]
  );

  const [assignments, setAssignments] = useState(() => {
    const init = {};
    slots.forEach((slot) => {
      init[slot.id] = guesses[slot.id]?.layer || "";
    });
    return init;
  });
  const [saveStatus, setSaveStatus] = useState(null);

  const usableLayers = layers.filter((l) => l.entity_count > 0);

  const unresolvedSlots = slots.filter((slot) => !assignments[slot.id]);

  // ย้อนกลับ: layer DXF -> ช่องที่ถูกแม็พ (สำหรับแสดงในตาราง layer ทั้งหมด)
  const layerToSlotLabel = {};
  slots.forEach((slot) => {
    const chosen = assignments[slot.id];
    if (chosen) layerToSlotLabel[chosen] = slot.label;
  });

  function handleChange(slotId, value) {
    setAssignments((prev) => ({ ...prev, [slotId]: value }));
    setSaveStatus(null);
  }

  function buildResolvedMapping() {
    return applyAssignments(layerMapping, slots, assignments);
  }

  async function handleSaveMapping() {
    setSaveStatus("saving");
    try {
      await updateLayerMapping(buildResolvedMapping());
      setSaveStatus("saved");
    } catch (e) {
      setSaveStatus("error");
    }
  }

  function handleNext() {
    onNext(buildResolvedMapping());
  }

  return (
    <div className="card">
      <h2>2. ตรวจสอบ Layer Mapping</h2>
      <p className="muted">
        ระบบเดาให้แล้วว่า layer ในไฟล์นี้ตรงกับอะไร - ตรวจสอบและแก้ไขให้ถูกต้องก่อนถอดวัสดุ
        เลือก "ไม่ใช้" หากไฟล์นี้ไม่มี layer สำหรับรายการนั้น
      </p>

      {unresolvedSlots.length > 0 && (
        <div className="warn-box">
          มี {unresolvedSlots.length} รายการที่ระบบเดาไม่ได้ - กรุณาเลือก layer ที่ตรงกัน หรือเลือก
          "ไม่ใช้" หากไฟล์นี้ไม่มี
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>สิ่งที่ต้องใช้</th>
            <th>Layer ในไฟล์ที่เลือก</th>
            <th>สถานะ</th>
          </tr>
        </thead>
        <tbody>
          {slots.map((slot) => {
            const value = assignments[slot.id];
            const confidence = guesses[slot.id]?.confidence;
            return (
              <tr key={slot.id}>
                <td>{slot.label}</td>
                <td>
                  <select value={value} onChange={(e) => handleChange(slot.id, e.target.value)}>
                    <option value="">— ไม่ใช้ —</option>
                    {usableLayers.map((l) => (
                      <option key={l.name} value={l.name}>
                        {l.name} ({l.entity_count})
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  {!value ? (
                    <span className="layer-status unknown">ไม่ใช้</span>
                  ) : confidence === "high" ? (
                    <span className="layer-status known">เดาอัตโนมัติ</span>
                  ) : (
                    <span className="layer-status unknown">เลือกเอง</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h3 style={{ marginTop: 24 }}>Layer ทั้งหมดในไฟล์</h3>
      <table>
        <thead>
          <tr>
            <th>ชื่อ Layer</th>
            <th>จำนวน entity</th>
            <th>ใช้สำหรับ</th>
          </tr>
        </thead>
        <tbody>
          {layers.map((l) => (
            <tr key={l.name}>
              <td>{l.name}</td>
              <td>{l.entity_count}</td>
              <td>{layerToSlotLabel[l.name] || <span className="muted">-</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <EntryTypeSelector value={entryType} onChange={onEntryTypeChange} />

      <div className="toolbar" style={{ marginTop: 16 }}>
        <button className="btn secondary" onClick={onBack}>
          ย้อนกลับ
        </button>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {saveStatus === "saving" && <span className="muted">กำลังบันทึก...</span>}
          {saveStatus === "saved" && <span className="muted">บันทึก mapping แล้ว</span>}
          {saveStatus === "error" && <span className="muted">บันทึกไม่สำเร็จ</span>}
          <button className="btn secondary" onClick={handleSaveMapping}>
            บันทึก mapping นี้
          </button>
          <button className="btn" onClick={handleNext}>
            ถอดวัสดุ →
          </button>
        </div>
      </div>
    </div>
  );
}
