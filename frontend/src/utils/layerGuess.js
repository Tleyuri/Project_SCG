// เครื่องมือ auto-guess การแม็พ layer DXF -> "ช่อง (slot)" ที่ระบบถอด BOQ ต้องใช้
// แต่ละช่องคือ entry ใน layer_mapping.json (เดิม) เช่น pipe_layers."ท่อ"
// auto-guess จะเทียบชื่อ layer จริงในไฟล์ DXF กับ alias ของแต่ละช่อง แล้วเสนอให้ผู้ใช้ยืนยัน/แก้

export function normalize(s) {
  if (!s) return "";
  return String(s).replace(/\s+/g, "").toLowerCase();
}

function matchScore(layerNameNorm, candidateNorm) {
  if (!layerNameNorm || !candidateNorm) return 0;
  if (layerNameNorm === candidateNorm) return 2;
  if (layerNameNorm.startsWith(candidateNorm) || candidateNorm.startsWith(layerNameNorm)) return 1;
  return 0;
}

// สร้างรายการ "ช่อง" จาก layer_mapping (เดิม) - แต่ละช่องต้องมี layer DXF จริง 1 อัน
export function buildSlots(layerMapping) {
  const slots = [];
  const lm = layerMapping || {};

  Object.entries(lm.pipe_layers || {}).forEach(([key, info]) => {
    slots.push({
      id: `pipe_layers.${key}`,
      category: "pipe_layers",
      key,
      type: info._type || null,
      label: `${info.label || key} (${info.plant})`,
    });
  });

  Object.entries(lm.sprinkler_layers || {}).forEach(([key, info]) => {
    slots.push({
      id: `sprinkler_layers.${key}`,
      category: "sprinkler_layers",
      key,
      type: info._type || null,
      label: `หัวสปริงเกอร์ (${info.plant})`,
    });
  });

  Object.entries(lm.valve_layers || {}).forEach(([key, info]) => {
    slots.push({
      id: `valve_layers.${key}`,
      category: "valve_layers",
      key,
      type: info._type || null,
      label: `ชุดวาล์ว (${info.plant})`,
    });
  });

  Object.entries(lm.joint_insert_layers || {}).forEach(([key, info]) => {
    slots.push({
      id: `joint_insert_layers.${key}`,
      category: "joint_insert_layers",
      key,
      type: info._type || null,
      label: `ข้อต่อ (block) - ${info.name_th || key}`,
    });
  });

  Object.entries(lm.joint_raw_layers || {}).forEach(([key, info]) => {
    slots.push({
      id: `joint_raw_layers.${key}`,
      category: "joint_raw_layers",
      key,
      type: info._type || null,
      label: `ข้อต่อ (เส้นดิบ - ต้องตรวจสอบ) - ${info.name_th || key}`,
    });
  });

  (lm.road_layers || []).forEach((key, index) => {
    slots.push({
      id: `road_layers.${index}`,
      category: "road_layers",
      key,
      index,
      type: "road",
      label: "ถนน",
    });
  });

  Object.entries(lm.plant_layers || {}).forEach(([key, info]) => {
    slots.push({
      id: `plant_layers.${key}`,
      category: "plant_layers",
      key,
      type: info._type || null,
      label: `พืช - ${info.plant} (${info.method})`,
    });
  });

  if (lm.dim_layer) {
    slots.push({
      id: "dim_layer",
      category: "dim_layer",
      key: lm.dim_layer,
      type: "dim",
      label: "ป้ายชื่อ/legend (Dim)",
    });
  }

  if (lm.zone_layer) {
    slots.push({
      id: "zone_layer",
      category: "zone_layer",
      key: lm.zone_layer,
      type: "zone",
      label: "โซน",
    });
  }

  return slots;
}

// เดาว่า layer DXF จริงตัวไหนตรงกับแต่ละช่อง
// คืนค่า { [slotId]: { layer: string|null, confidence: "high"|"none" } }
export function guessAssignments(slots, dxfLayers, layerAliases) {
  const aliases = layerAliases || {};
  const usableLayers = (dxfLayers || []).filter((l) => l.entity_count > 0);
  const usedLayers = new Set();
  const result = {};

  slots.forEach((slot) => {
    const candidates = [slot.key, ...(aliases[slot.type] || [])].map(normalize);

    let best = null;
    let bestScore = 0;
    for (const layer of usableLayers) {
      if (usedLayers.has(layer.name)) continue;
      const layerNorm = normalize(layer.name);
      for (const cand of candidates) {
        const score = matchScore(layerNorm, cand);
        if (score > bestScore) {
          bestScore = score;
          best = layer.name;
        }
      }
    }

    if (best) {
      usedLayers.add(best);
      result[slot.id] = { layer: best, confidence: "high" };
    } else {
      result[slot.id] = { layer: null, confidence: "none" };
    }
  });

  return result;
}

// นำผลการยืนยัน/แก้ของผู้ใช้มาประกอบเป็น layer_mapping ฉบับเต็ม (rename/ลบ key ตาม assignment)
// ส่งค่านี้ทั้งชุดไปยัง backend (แทนที่ layer_mapping เดิมทั้งหมด ไม่ merge)
export function applyAssignments(layerMapping, slots, assignments) {
  const clone = JSON.parse(JSON.stringify(layerMapping || {}));

  // road_layers ต้องประมวลผลทีหลังสุดเพื่อไม่ให้ index เพี้ยนระหว่างลบสมาชิก
  const roadRemovals = new Set();

  slots.forEach((slot) => {
    const assigned = assignments[slot.id];
    const value = assigned === undefined ? slot.key : assigned;

    if (slot.category === "dim_layer" || slot.category === "zone_layer") {
      if (!value) {
        delete clone[slot.category];
      } else {
        clone[slot.category] = value;
      }
      return;
    }

    if (slot.category === "road_layers") {
      if (!value) {
        roadRemovals.add(slot.index);
      } else {
        clone.road_layers[slot.index] = value;
      }
      return;
    }

    // ช่องประเภท dict (pipe_layers, sprinkler_layers, valve_layers, joint_insert_layers,
    // joint_raw_layers, plant_layers)
    const category = clone[slot.category] || {};
    const entry = category[slot.key];

    if (!value) {
      delete category[slot.key];
    } else if (value !== slot.key) {
      delete category[slot.key];
      category[value] = entry;
    }
    clone[slot.category] = category;
  });

  if (roadRemovals.size > 0 && Array.isArray(clone.road_layers)) {
    clone.road_layers = clone.road_layers.filter((_, idx) => !roadRemovals.has(idx));
  }

  return clone;
}
