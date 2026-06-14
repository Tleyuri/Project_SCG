# วิธี Deploy ขึ้นเว็บจริง (ฟรี)

ใช้ **Render** (ฟรี) สำหรับ backend (FastAPI) และ **Cloudflare Pages** (ฟรี) สำหรับ frontend (React)

## 0. เตรียม: push โค้ดขึ้น GitHub

ต้องมี repo บน GitHub ก่อน (Render และ Cloudflare Pages ทั้งคู่ deploy จาก GitHub repo)

```bash
git init
git add .
git commit -m "initial commit"
# สร้าง repo ใหม่บน GitHub แล้ว push
git remote add origin <URL ของ repo>
git push -u origin main
```

## 1. Deploy Backend (Render)

1. ไปที่ https://dashboard.render.com → New → **Blueprint**
2. เลือก repo นี้ - Render จะอ่านไฟล์ `render.yaml` ที่ root โปรเจกต์ให้อัตโนมัติ
   (ถ้าไม่ใช้ Blueprint ก็สร้าง **Web Service** เองได้ โดยตั้งค่า:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free)
3. กด Deploy แล้วรอ build เสร็จ จะได้ URL ประมาณ `https://dxf-boq-backend.onrender.com`
4. ทดสอบ: เปิด `https://dxf-boq-backend.onrender.com/api/health` ควรเห็น `{"status":"ok"}`

> **หมายเหตุ (free tier)**:
> - บริการจะ "หลับ" เมื่อไม่มีคนใช้ ~15 นาที ครั้งแรกที่เรียกหลังหลับจะช้าประมาณ 30-50 วิ
> - Disk เป็นแบบ ephemeral - ถ้าแก้ไฟล์ config (layer mapping / price table / settings) ผ่านหน้าเว็บแล้ว service restart ค่าที่แก้จะหายกลับไปเป็นค่าใน repo

## 2. Deploy Frontend (Cloudflare Pages)

1. แก้ไฟล์ [frontend/.env.production](frontend/.env.production) ให้เป็น URL จริงของ backend ที่ได้จากขั้นตอนที่ 1:
   ```
   VITE_API_BASE_URL=https://dxf-boq-backend.onrender.com/api
   ```
2. commit + push การแก้ไขนี้ขึ้น GitHub
3. ไปที่ https://dash.cloudflare.com → Workers & Pages → Create → **Pages** → Connect to Git → เลือก repo นี้
4. ตั้งค่า build:
   - Framework preset: Vite
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Build output directory: `dist`
5. กด Deploy จะได้ URL ประมาณ `https://<project>.pages.dev`

## 3. อนุญาต CORS จาก frontend ไปยัง backend

ไปที่ Render → service `dxf-boq-backend` → Environment → แก้ค่า `ALLOWED_ORIGINS` เป็น URL ของ Cloudflare Pages ที่ได้จากขั้นตอนที่ 2:

```
ALLOWED_ORIGINS=https://<project>.pages.dev
```

แล้วกด Save (service จะ redeploy อัตโนมัติ)

## 4. ทดสอบ

เปิด `https://<project>.pages.dev` แล้วลองอัปโหลดไฟล์ DXF → ถอด BOQ → ดาวน์โหลด Excel
