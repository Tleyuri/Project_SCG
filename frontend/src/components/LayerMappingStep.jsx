function collectKnownLayers(layerMapping) {
  const known = new Map();
  const add = (name, label) => known.set(name, label);

  Object.entries(layerMapping.pipe_layers || {}).forEach(([k, v]) =>
    add(k, `ท่อ - ${v.label} (${v.plant})`)
  );
  Object.entries(layerMapping.sprinkler_layers || {}).forEach(([k, v]) =>
    add(k, `หัวสปริงเกอร์ (${v.plant})`)
  );
  Object.entries(layerMapping.valve_layers || {}).forEach(([k, v]) =>
    add(k, `ชุดวาล์ว (${v.plant})`)
  );
  Object.entries(layerMapping.joint_insert_layers || {}).forEach(([k, v]) =>
    add(k, `ข้อต่อ (block) - ${v.name_th}`)
  );
  Object.entries(layerMapping.joint_raw_layers || {}).forEach(([k, v]) =>
    add(k, `ข้อต่อ (เส้นดิบ - ต้องตรวจสอบ) - ${v.name_th}`)
  );
  (layerMapping.road_layers || []).forEach((k) => add(k, "ถนน"));
  Object.entries(layerMapping.plant_layers || {}).forEach(([k, v]) =>
    add(k, `พืช - ${v.plant} (${v.method})`)
  );
  if (layerMapping.dim_layer) add(layerMapping.dim_layer, "ป้ายชื่อ/legend");
  if (layerMapping.zone_layer) add(layerMapping.zone_layer, "โซน");

  return known;
}

export default function LayerMappingStep({ layers, layerMapping, onBack, onNext }) {
  const known = collectKnownLayers(layerMapping || {});
  const aliases = layerMapping?._fuzzy_aliases || {};

  const rows = layers
    .filter((l) => l.entity_count > 0)
    .map((l) => {
      const isKnown = known.has(l.name);
      const aliasFor = aliases[l.name];
      return { ...l, isKnown, aliasFor };
    });

  const unknownCount = rows.filter((r) => !r.isKnown && !r.aliasFor).length;

  return (
    <div className="card">
      <h2>2. ตรวจสอบ Layer Mapping</h2>
      <p className="muted">
        ระบบจะถอดวัสดุเฉพาะ layer ที่รู้จักเท่านั้น (ตามตาราง mapping ใน config)
        layer ที่ไม่รู้จักจะถูกข้าม - ถ้าชื่อ layer สะกดต่างจากที่ระบบรู้จัก
        ให้แก้ไขไฟล์ config/layer_mapping.json แล้วอัปโหลดใหม่
      </p>

      {unknownCount > 0 && (
        <div className="warn-box">
          พบ layer ที่ไม่รู้จัก {unknownCount} รายการ - layer เหล่านี้จะไม่ถูกนับ
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>ชื่อ Layer</th>
            <th>จำนวน entity</th>
            <th>สถานะ</th>
            <th>ความหมายตามระบบ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <td>{r.name}</td>
              <td>{r.entity_count}</td>
              <td>
                {r.isKnown ? (
                  <span className="layer-status known">รู้จัก</span>
                ) : r.aliasFor ? (
                  <span className="layer-status known">แม็พจาก alias → {r.aliasFor}</span>
                ) : (
                  <span className="layer-status unknown">ไม่รู้จัก</span>
                )}
              </td>
              <td>
                {known.get(r.name) || (r.aliasFor ? known.get(r.aliasFor) || "-" : "-")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="toolbar" style={{ marginTop: 16 }}>
        <button className="btn secondary" onClick={onBack}>
          ย้อนกลับ
        </button>
        <button className="btn" onClick={onNext}>
          ถอดวัสดุ →
        </button>
      </div>
    </div>
  );
}
