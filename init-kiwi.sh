#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "===> 1. Build dan jalankan container Kiwi TCMS dari source code lokal..."
docker compose up --build -d

echo "===> 2. Menunggu container kiwi_web siap..."
until [ "$(docker inspect -f '{{.State.Status}}' kiwi_web 2>/dev/null)" = "running" ]; do
    echo "Menunggu container kiwi_web running..."
    sleep 2
done

# Tunggu beberapa detik agar uWSGI/Nginx di dalam container siap
sleep 5

echo "===> 3. Menjalankan migrasi database ke PostgreSQL lokal..."
docker exec kiwi_web /Kiwi/manage.py migrate

echo "===> 4. Mengatur domain..."
docker exec kiwi_web /Kiwi/manage.py set_domain localhost

echo "===> 5. Memperbarui permission..."
docker exec kiwi_web /Kiwi/manage.py refresh_permissions

echo "===> 6. Memastikan superuser admin tersedia..."
docker exec -e DJANGO_SUPERUSER_PASSWORD=KiwiTCMSAdmin2026! kiwi_web /Kiwi/manage.py createsuperuser --noinput --username admin --email admin@example.com || true

echo "--------------------------------------------------------"
echo "🎉 Kiwi TCMS Self-Hosted (Source Code) telah SIAP!"
echo "Akses Web: https://localhost:8443"
echo "Username : admin"
echo "Password : KiwiTCMSAdmin2026!"
echo "--------------------------------------------------------"
