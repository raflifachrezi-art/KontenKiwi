#!/usr/bin/env bash
set -e

# Pastikan dijalankan sebagai root / sudo
if [ "$EUID" -ne 0 ]; then
  echo "Harap jalankan script ini dengan sudo:"
  echo "sudo ./setup-local-postgres.sh"
  exit 1
fi

echo "===> 1. Menginstal PostgreSQL di host Ubuntu..."
apt-get update -y
apt-get install -y postgresql postgresql-contrib

echo "===> 2. Memastikan service PostgreSQL berjalan..."
systemctl enable --now postgresql

# Cari versi postgresql yang terpasang
PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | sort -V | tail -n 1)
if [ -z "$PG_VERSION" ]; then
  echo "Error: Direktori konfigurasi PostgreSQL tidak ditemukan!"
  exit 1
fi

PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"
PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"

echo "===> 3. Konfigurasi listen_addresses agar dapat diakses oleh container Kiwi TCMS..."
if grep -q "^#listen_addresses" "$PG_CONF"; then
  sed -i "s/^#listen_addresses = .*/listen_addresses = '*'/" "$PG_CONF"
elif grep -q "^listen_addresses" "$PG_CONF"; then
  sed -i "s/^listen_addresses = .*/listen_addresses = '*'/" "$PG_CONF"
else
  echo "listen_addresses = '*'" >> "$PG_CONF"
fi

echo "===> 4. Konfigurasi pg_hba.conf untuk mengizinkan koneksi dari subnet Docker..."
DOCKER_SUBNET="172.16.0.0/12"
if ! grep -q "$DOCKER_SUBNET" "$PG_HBA"; then
  echo "# Allow Docker containers (Kiwi TCMS) to connect" >> "$PG_HBA"
  echo "host    all             all             $DOCKER_SUBNET          scram-sha-256" >> "$PG_HBA"
fi

echo "===> 5. Mereload konfigurasi PostgreSQL..."
systemctl restart postgresql

echo "===> 6. Membuat user dan database 'kiwi'..."
# Password default untuk user DB kiwi
DB_PASS="kiwi-1s-aw3s0m3"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='kiwi'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER kiwi WITH PASSWORD '${DB_PASS}';"

# Update password jika user sudah ada sebelumnya
sudo -u postgres psql -c "ALTER USER kiwi WITH PASSWORD '${DB_PASS}';"

# Buat database jika belum ada
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='kiwi'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE kiwi OWNER kiwi;"

# Berikan hak akses penuh ke schema public
sudo -u postgres psql -d kiwi -c "GRANT ALL ON SCHEMA public TO kiwi;"
sudo -u postgres psql -d kiwi -c "GRANT ALL PRIVILEGES ON DATABASE kiwi TO kiwi;"

echo "--------------------------------------------------------"
echo "✅ Setup PostgreSQL lokal di host BERHASIL!"
echo "Database: kiwi"
echo "User:     kiwi"
echo "Port:     5432"
echo "Data tersimpan di host (/var/lib/postgresql) sehingga 100% AMAN dari docker prune."
echo "--------------------------------------------------------"
