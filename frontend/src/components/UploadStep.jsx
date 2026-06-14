import { useRef, useState } from "react";
import { uploadDxf } from "../api";

export default function UploadStep({ onUploaded, setError }) {
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".dxf")) {
      if (file.name.toLowerCase().endsWith(".dwg")) {
        setError(
          "ไฟล์นี้เป็น .dwg - ระบบอ่านได้เฉพาะ .dxf กรุณาเปิดไฟล์ใน AutoCAD/ZWCAD แล้ว Save As เป็น DXF ก่อนอัปโหลด"
        );
      } else {
        setError("รองรับเฉพาะไฟล์ .dxf เท่านั้น");
      }
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await uploadDxf(file);
      onUploaded(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2>1. อัปโหลดไฟล์ DXF</h2>
      <p className="muted">
        ลากไฟล์ .dxf มาวาง หรือคลิกเพื่อเลือกไฟล์ — ระบบอ่านได้เฉพาะ .dxf เท่านั้น
        หากมีไฟล์ .dwg กรุณา Save As เป็น DXF จาก AutoCAD/ZWCAD ก่อน
      </p>
      <div
        className={`dropzone${dragOver ? " dragover" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
      >
        {loading ? (
          <p>กำลังอ่านไฟล์...</p>
        ) : (
          <>
            <p style={{ fontSize: 32, margin: 0 }}>📐</p>
            <p>
              <strong>ลากไฟล์ .dxf มาวางที่นี่</strong> หรือคลิกเพื่อเลือกไฟล์
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".dxf"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
    </div>
  );
}
