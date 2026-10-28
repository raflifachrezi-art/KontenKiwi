# 🥝 Kiwi TCMS Self-Hosted (Source Code & Customization Guide)

Panduan operasional dan kustomisasi source code Kiwi TCMS yang berjalan pada direktori `/home/eylan/Konten.com/KiwiTCMxKonten`.

---

## 🚀 Status Deployment Saat Ini

- **Mode Deployment**: Self-hosted dibangun langsung dari source code lokal (`build: .` via multi-stage Dockerfile).
- **Branch Git**: `konten-customization` (berbasis tag `v16.5`).
- **Database Backend**: PostgreSQL native host Linux (`127.0.0.1:5432`, DB: `kiwi`).
- **URL Dashboard**: **[https://localhost:8443](https://localhost:8443)**
- **Kredensial Default**:
  - **Username**: `admin`
  - **Password**: `KiwiTCMSAdmin2026!`

---

## 📂 Struktur Direktori Penting untuk Kustomisasi

```text
KiwiTCMxKonten/
├── tcms/                        # Direktori utama kode sumber Django
│   ├── templates/               # Template HTML dashboard, navigation, form, dll.
│   ├── static/                  # CSS, JavaScript, gambar
│   ├── core/                    # Logika core Kiwi TCMS
│   ├── testcases/               # Modul Test Cases
│   ├── testplans/               # Modul Test Plans
│   └── testruns/                # Modul Test Runs & Executions
├── Dockerfile                   # Spesifikasi multi-stage Docker build
├── docker-compose.yml           # Konfigurasi container service & port
├── .env                         # Konfigurasi koneksi PostgreSQL & domain
├── init-kiwi.sh                 # Script inisialisasi & migrasi otomatis
└── uploads/                     # File attachments/screenshot pengujian (persistent)
```

---

## 🎨 Panduan Melakukan Kustomisasi

### 1. Mengubah Tampilan / Template HTML
Seluruh template tampilan web berada di dalam folder `tcms/templates/`:
- Navbar & Layout umum: `tcms/templates/base.html` atau `tcms/templates/navbar.html`
- Dashboard / Beranda: `tcms/templates/dashboard/`
- Test Plan & Case view: `tcms/templates/testplans/` & `tcms/templates/testcases/`

### 2. Cara Menerapkan Perubahan

#### Opsi A: Rebuild Image Produksi (Standard)
Setelah Anda mengubah file di `tcms/`:
```bash
# Rebuild image dengan perubahan terbaru
docker compose build

# Restart container
docker compose up -d
```

#### Opsi B: Live Editing Tanpa Rebuild (Untuk Development Cepat)
Jika Anda sedang aktif mengutak-atik template HTML atau script Python dan ingin melihat perubahan secara instan tanpa menunggu proses build:
Buka `docker-compose.yml`, aktifkan (uncomment) volume mount:
```yaml
volumes:
  - ./uploads:/Kiwi/uploads:Z
  - ./tcms:/venv/lib64/python3.12/site-packages/tcms:Z
```
Lalu jalankan `docker compose restart`. Perubahan pada file HTML di `tcms/templates/` akan langsung terlihat saat halaman di-refresh.

---

## 🛠️ Perintah Operasional Harian

```bash
# Menjalankan / Memperbarui Container
./init-kiwi.sh

# Cek log container
docker logs -f kiwi_web

# Masuk ke shell Django
docker exec -it kiwi_web /Kiwi/manage.py shell

# Jalankan script migrasi manual jika ada perubahan model
docker exec -it kiwi_web /Kiwi/manage.py migrate
```
