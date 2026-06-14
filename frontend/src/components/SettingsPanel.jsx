const FIELD_DEFS = [
  { key: "pipe_segment_length_m", label: "ความยาวท่อ/ท่อน (ม.)", step: 0.1 },
  { key: "riser_height_m", label: "ความสูงท่อตั้ง (ม.)", step: 0.1 },
];

const PIPE_SIZE_FIELD_DEFS = [
  { key: "pipe_size_main", label: "ขนาดท่อเมน" },
  { key: "pipe_size_submain", label: "ขนาดท่อย่อย" },
  { key: "pipe_size_lateral", label: "ขนาดท่อแยก" },
];

export default function SettingsPanel({ settings, onChange, gardenLocation, gardenPhone, onGardenChange }) {
  function updateField(key, value) {
    onChange({ ...settings, [key]: value === "" ? "" : Number(value) });
  }

  function updateTextField(key, value) {
    onChange({ ...settings, [key]: value });
  }

  return (
    <div className="card">
      <h2>ตั้งค่า</h2>
      <div className="settings-grid">
        {FIELD_DEFS.map((f) => (
          <label className="field" key={f.key}>
            {f.label}
            <input
              type="number"
              step={f.step}
              value={settings[f.key] ?? ""}
              onChange={(e) => updateField(f.key, e.target.value)}
            />
          </label>
        ))}
        {PIPE_SIZE_FIELD_DEFS.map((f) => (
          <label className="field" key={f.key}>
            {f.label}
            <input
              type="text"
              placeholder='อิงตาม layer Dim อัตโนมัติ (เช่น 6")'
              value={settings[f.key] ?? ""}
              onChange={(e) => updateTextField(f.key, e.target.value)}
            />
          </label>
        ))}
        <label className="field">
          ที่ตั้งสวน (จังหวัด)
          <input
            type="text"
            value={gardenLocation}
            onChange={(e) => onGardenChange({ location: e.target.value, phone: gardenPhone })}
          />
        </label>
        <label className="field">
          เบอร์โทร
          <input
            type="text"
            value={gardenPhone}
            onChange={(e) => onGardenChange({ location: gardenLocation, phone: e.target.value })}
          />
        </label>
      </div>
    </div>
  );
}
