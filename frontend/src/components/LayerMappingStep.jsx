import { useMemo, useState } from "react";
import { buildSlots, guessAssignments, applyAssignments } from "../utils/layerGuess";
import { updateLayerMapping } from "../api";

export default function LayerMappingStep({ layers, layerMapping, layerAliases, onBack, onNext }) {
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
