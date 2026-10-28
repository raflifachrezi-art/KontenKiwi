#!/usr/bin/env python3
"""
Import Playwright Base test cases from github.com/maseylan/playwright-base
into Kiwi TCMS database via Django ORM.
"""

import sys
import django

# Setup Django environment
from tcms.management.models import Product, Version, Build, Classification, Priority, Tag
from tcms.testcases.models import TestCase, TestCaseStatus, Category
from tcms.testplans.models import TestPlan, PlanType, TestCasePlan
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

print(f"Using user: {admin_user.username}")

# 1. Classification
classification, _ = Classification.objects.get_or_create(name="Test Automation")

# 2. Product
product, _ = Product.objects.get_or_create(
    name="Playwright Base",
    classification=classification,
    defaults={"description": "Playwright Automation Framework - https://github.com/maseylan/playwright-base"}
)

# 3. Version & Build
version, _ = Version.objects.get_or_create(product=product, value="1.0.0")
build, _ = Build.objects.get_or_create(version=version, name="1.0.0", defaults={"is_active": True})

# 4. Statuses & Priorities
status_confirmed = TestCaseStatus.objects.get(name="CONFIRMED")
p1 = Priority.objects.get(value="P1")
p2 = Priority.objects.get(value="P2")
p3 = Priority.objects.get(value="P3")

# 5. Plan Types
plan_type_e2e = PlanType.objects.get(name="System")
plan_type_api = PlanType.objects.get(name="Integration")
plan_type_master = PlanType.objects.get(name="Regression")

# 6. Test Plans
master_plan, _ = TestPlan.objects.get_or_create(
    name="Playwright Base - Master Test Suite",
    product=product,
    product_version=version,
    type=plan_type_master,
    author=admin_user,
    defaults={"text": "Kumpulan seluruh test case otomatis (E2E dan API) dari repository maseylan/playwright-base."}
)

e2e_plan, _ = TestPlan.objects.get_or_create(
    name="Playwright Base - E2E UI Suite",
    product=product,
    product_version=version,
    type=plan_type_e2e,
    author=admin_user,
    defaults={"text": "End-to-End browser UI automation test suite menggunakan Playwright pada aplikasi demo SauceDemo."}
)

api_plan, _ = TestPlan.objects.get_or_create(
    name="Playwright Base - API Integration Suite",
    product=product,
    product_version=version,
    type=plan_type_api,
    author=admin_user,
    defaults={"text": "API contract, CRUD, and data-driven filtering test suite menggunakan Restful Booker API."}
)

# Data test cases yang diekstrak dari repository maseylan/playwright-base
test_cases_data = [
    # -------------------------------------------------------------
    # E2E - Auth (tests/e2e/auth.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "E2E - Authentication",
        "category_desc": "Pengujian autentikasi dan manajemen sesi web UI",
        "plan": e2e_plan,
        "priority": p1,
        "summary": "[E2E-AUTH-01] Valid Login - Should authenticate successfully with valid credentials",
        "script": "tests/e2e/auth.spec.ts",
        "arguments": "npx playwright test tests/e2e/auth.spec.ts -g 'should authenticate successfully with valid credentials'",
        "tags": ["smoke", "regression", "e2e", "auth"],
        "text": """### Tujuan
Memverifikasi pengguna dapat login ke sistem dengan kredensial valid dan diarahkan ke halaman inventory.

### Prasyarat
- Aplikasi target (SauceDemo) dapat diakses.
- Akun standard_user aktif.

### Langkah-langkah
1. Buka halaman login (`/`).
2. Masukkan username valid (`standard_user`).
3. Masukkan password valid (`secret_sauce`).
4. Klik tombol Login.

### Hasil yang Diharapkan
1. Pengguna berhasil masuk ke URL `/inventory.html`.
2. Katalog produk dimuat dengan jumlah item > 0.
"""
    },
    {
        "category": "E2E - Authentication",
        "category_desc": "Pengujian autentikasi dan manajemen sesi web UI",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-AUTH-02] Missing Username - Should show validation error when username is missing",
        "script": "tests/e2e/auth.spec.ts",
        "arguments": "npx playwright test tests/e2e/auth.spec.ts -g 'should show validation error when username is missing'",
        "tags": ["regression", "e2e", "auth"],
        "text": """### Tujuan
Memverifikasi validasi input saat form login disubmit tanpa mengisi username.

### Langkah-langkah
1. Buka halaman login.
2. Kosongkan kolom Username.
3. Isi kolom Password dengan sembarang password.
4. Klik tombol Login.

### Hasil yang Diharapkan
Muncul pesan error: `Epic sadface: Username is required`.
"""
    },
    {
        "category": "E2E - Authentication",
        "category_desc": "Pengujian autentikasi dan manajemen sesi web UI",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-AUTH-03] Missing Password - Should show validation error when password is missing",
        "script": "tests/e2e/auth.spec.ts",
        "arguments": "npx playwright test tests/e2e/auth.spec.ts -g 'should show validation error when password is missing'",
        "tags": ["regression", "e2e", "auth"],
        "text": """### Tujuan
Memverifikasi validasi input saat form login disubmit tanpa mengisi password.

### Langkah-langkah
1. Buka halaman login.
2. Isi kolom Username dengan `standard_user`.
3. Kosongkan kolom Password.
4. Klik tombol Login.

### Hasil yang Diharapkan
Muncul pesan error: `Epic sadface: Password is required`.
"""
    },
    {
        "category": "E2E - Authentication",
        "category_desc": "Pengujian autentikasi dan manajemen sesi web UI",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-AUTH-04] Invalid Credentials - Should reject non-existent user credentials",
        "script": "tests/e2e/auth.spec.ts",
        "arguments": "npx playwright test tests/e2e/auth.spec.ts -g 'should reject non-existent user credentials'",
        "tags": ["regression", "e2e", "auth"],
        "text": """### Tujuan
Memverifikasi sistem menolak kombinasi username dan password yang tidak terdaftar.

### Langkah-langkah
1. Buka halaman login.
2. Masukkan username yang salah (`invalid_user`).
3. Masukkan password yang salah (`invalid_pass`).
4. Klik tombol Login.

### Hasil yang Diharapkan
Muncul pesan error: `Epic sadface: Username and password do not match any user in this service`.
"""
    },
    {
        "category": "E2E - Authentication",
        "category_desc": "Pengujian autentikasi dan manajemen sesi web UI",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-AUTH-05] Locked Out User - Should block locked out user with clear message",
        "script": "tests/e2e/auth.spec.ts",
        "arguments": "npx playwright test tests/e2e/auth.spec.ts -g 'should block locked out user with clear message'",
        "tags": ["regression", "e2e", "auth"],
        "text": """### Tujuan
Memverifikasi akun yang terkunci tidak diizinkan masuk dan diberi notifikasi yang jelas.

### Langkah-langkah
1. Buka halaman login.
2. Masukkan kredensial locked-out user (`locked_out_user`).
3. Klik tombol Login.

### Hasil yang Diharapkan
Muncul pesan error: `Epic sadface: Sorry, this user has been locked out.`.
"""
    },
    {
        "category": "E2E - Authentication",
        "category_desc": "Pengujian autentikasi dan manajemen sesi web UI",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-AUTH-06] Secure Logout - Should allow authenticated user to log out securely",
        "script": "tests/e2e/auth.spec.ts",
        "arguments": "npx playwright test tests/e2e/auth.spec.ts -g 'should allow authenticated user to log out securely'",
        "tags": ["regression", "e2e", "auth"],
        "text": """### Tujuan
Memverifikasi user dapat logout dan sesi terminasi sehingga halaman terproteksi tidak bisa diakses langsung.

### Langkah-langkah
1. Login dengan `standard_user`.
2. Buka menu navigasi dan klik tombol Logout.
3. Verifikasi kembali ke halaman login.
4. Coba akses langsung URL `/inventory.html`.

### Hasil yang Diharapkan
1. User diarahkan kembali ke halaman login.
2. Akses ke `/inventory.html` diblokir dengan pesan: `You can only access '/inventory.html' when you are logged in.`.
"""
    },

    # -------------------------------------------------------------
    # E2E - Cart & Catalogue (tests/e2e/cartState.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "E2E - Cart & Catalogue",
        "category_desc": "Pengujian sorting produk dan status keranjang belanja",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-CART-01] Product Sorting - Sort products by price low-to-high and high-to-low correctly",
        "script": "tests/e2e/cartState.spec.ts",
        "arguments": "npx playwright test tests/e2e/cartState.spec.ts -g 'should sort products by price low-to-high and high-to-low correctly'",
        "tags": ["regression", "e2e", "inventory"],
        "text": """### Tujuan
Memverifikasi fitur pengurutan (sorting) harga produk berfungsi akurat baik menaik maupun menurun.

### Langkah-langkah
1. Login dan masuk ke halaman inventory.
2. Pilih dropdown sort 'Price (low to high)' (`lohi`).
3. Verifikasi urutan harga setiap item dari terkecil ke terbesar.
4. Pilih dropdown sort 'Price (high to low)' (`hilo`).
5. Verifikasi urutan harga setiap item dari terbesar ke terkecil.

### Hasil yang Diharapkan
Seluruh produk terurut secara benar sesuai nilai nominal harga yang dipilih.
"""
    },
    {
        "category": "E2E - Cart & Catalogue",
        "category_desc": "Pengujian sorting produk dan status keranjang belanja",
        "plan": e2e_plan,
        "priority": p2,
        "summary": "[E2E-CART-02] Cart Badge Counter - Maintain accurate cart badge count through additions and removals",
        "script": "tests/e2e/cartState.spec.ts",
        "arguments": "npx playwright test tests/e2e/cartState.spec.ts -g 'should maintain accurate cart badge count through additions and removals'",
        "tags": ["regression", "e2e", "cart"],
        "text": """### Tujuan
Memverifikasi badge counter keranjang bertambah dan berkurang secara konsisten saat penambahan dan penghapusan produk.

### Langkah-langkah
1. Verifikasi counter awal keranjang kosong (0).
2. Tambahkan 'Sauce Labs Backpack', periksa badge counter bernilai 1.
3. Tambahkan 'Sauce Labs Fleece Jacket', periksa badge counter bernilai 2.
4. Hapus item pertama langsung dari halaman inventory, periksa badge counter kembali 1.
5. Masuk ke halaman keranjang (`/cart.html`), hapus item kedua.
6. Klik Continue Shopping dan kembali ke inventory.

### Hasil yang Diharapkan
Badge counter keranjang hilang/bernilai 0 setelah semua produk dihapus.
"""
    },

    # -------------------------------------------------------------
    # E2E - Checkout (tests/e2e/checkoutFlow.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "E2E - Checkout Workflow",
        "category_desc": "Pengujian alur pembelian multi-langkah dan kalkulasi harga",
        "plan": e2e_plan,
        "priority": p1,
        "summary": "[E2E-CHK-01] End-to-End Checkout - Complete multi-step purchase flow with form validation and price math verification",
        "script": "tests/e2e/checkoutFlow.spec.ts",
        "arguments": "npx playwright test tests/e2e/checkoutFlow.spec.ts -g 'complete multi-step purchase flow'",
        "tags": ["smoke", "regression", "e2e", "checkout"],
        "text": """### Tujuan
Memverifikasi end-to-end alur checkout mulai dari keranjang, validasi form pengiriman, verifikasi rumus finansial, hingga order complete.

### Langkah-langkah
1. Tambahkan dua produk ke keranjang belanja.
2. Buka halaman Cart dan validasi kedua item ada dalam daftar.
3. Klik tombol Checkout:
   - Tes boundary validasi: Submit tanpa First Name.
   - Submit tanpa Last Name.
   - Submit tanpa Postal Code.
4. Masukkan data pengiriman valid dan klik Continue.
5. Pada Step 2 (Overview):
   - Periksa subtotal item.
   - Verifikasi perhitungan matematika: Subtotal + Tax = Total secara ketat.
6. Klik Finish Order.
7. Kembali ke halaman utama produk dan pastikan keranjang ter-reset (0).

### Hasil yang Diharapkan
Order sukses dengan konfirmasi 'THANK YOU FOR YOUR ORDER' dan total tagihan akurat secara matematis.
"""
    },

    # -------------------------------------------------------------
    # API - Auth (tests/api/auth.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "API - Authentication & Health",
        "category_desc": "Pengujian endpoint autentikasi token dan status kesehatan API",
        "plan": api_plan,
        "priority": p1,
        "summary": "[API-AUTH-01] Health Check - Verify health status of the API service (/ping)",
        "script": "tests/api/auth.spec.ts",
        "arguments": "npx playwright test tests/api/auth.spec.ts -g 'should verify health status of the API service'",
        "tags": ["smoke", "api", "healthcheck"],
        "text": """### Endpoint
`GET /ping`

### Tujuan
Memverifikasi bahwa service Restful Booker aktif dan merespons request.

### Hasil yang Diharapkan
Status HTTP 201 Created.
"""
    },
    {
        "category": "API - Authentication & Health",
        "category_desc": "Pengujian endpoint autentikasi token dan status kesehatan API",
        "plan": api_plan,
        "priority": p1,
        "summary": "[API-AUTH-02] Token Creation - Generate auth token with valid credentials and match contract schema",
        "script": "tests/api/auth.spec.ts",
        "arguments": "npx playwright test tests/api/auth.spec.ts -g 'should generate an auth token with valid credentials'",
        "tags": ["smoke", "api", "auth"],
        "text": """### Endpoint
`POST /auth`

### Payload
```json
{
  "username": "admin",
  "password": "password123"
}
```

### Hasil yang Diharapkan
1. HTTP status code: 200 OK.
2. Response body valid sesuai Zod AuthSuccessSchema: memiliki property `token` berupa string.
"""
    },
    {
        "category": "API - Authentication & Health",
        "category_desc": "Pengujian endpoint autentikasi token dan status kesehatan API",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-AUTH-03] Invalid Auth - Handle invalid credentials gracefully",
        "script": "tests/api/auth.spec.ts",
        "arguments": "npx playwright test tests/api/auth.spec.ts -g 'should handle invalid credentials gracefully'",
        "tags": ["regression", "api", "auth"],
        "text": """### Endpoint
`POST /auth`

### Payload
```json
{
  "username": "wrong_admin",
  "password": "invalid_password"
}
```

### Hasil yang Diharapkan
1. HTTP status code: 200 OK.
2. Response body valid sesuai Zod AuthFailureSchema: `{"reason": "Bad credentials"}`.
"""
    },

    # -------------------------------------------------------------
    # API - Booking CRUD (tests/api/bookingCrud.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "API - Booking Lifecycle",
        "category_desc": "Pengujian rantai operasi CRUD (Create, Read, Update, Delete) booking",
        "plan": api_plan,
        "priority": p1,
        "summary": "[API-CRUD-01] Full Chained CRUD - Execute full chained CRUD lifecycle passing resource ID across steps",
        "script": "tests/api/bookingCrud.spec.ts",
        "arguments": "npx playwright test tests/api/bookingCrud.spec.ts -g 'should execute full chained CRUD lifecycle'",
        "tags": ["smoke", "api", "regression", "crud"],
        "text": """### Tujuan
Memverifikasi siklus hidup pemesanan hotel (Booking) secara berantai:
1. **POST /booking** -> Buat booking baru, validasi Zod CreateBookingResponseSchema, ekstrak `bookingid`.
2. **GET /booking/:id** -> Ambil data dengan ID dan cocokkan detail Zod BookingDetailsSchema.
3. **PUT /booking/:id** -> Update seluruh data dengan menyertakan Auth Token, periksa perubahan nama & harga.
4. **PATCH /booking/:id** -> Update sebagian (additionalneeds) dengan Auth Token, pastikan field lain tidak hilang.
5. **DELETE /booking/:id** -> Hapus booking dengan Auth Token, verifikasi response 201.
6. **GET /booking/:id** -> Pastikan booking yang sudah dihapus menghasilkan HTTP 404 Not Found (Idempotency).
"""
    },

    # -------------------------------------------------------------
    # API - Booking Schema (tests/api/bookingSchema.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "API - Contract Schema & Errors",
        "category_desc": "Pengujian kepatuhan kontrak schema Zod dan penanganan error",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-SCHEMA-01] List Contract - Validate contract schema for booking list query",
        "script": "tests/api/bookingSchema.spec.ts",
        "arguments": "npx playwright test tests/api/bookingSchema.spec.ts -g 'should validate contract schema for booking list query'",
        "tags": ["regression", "api", "schema"],
        "text": """### Endpoint
`GET /booking`

### Tujuan
Memverifikasi response daftar pemesanan memenuhi schema array ID BookingListSchema.

### Hasil yang Diharapkan
1. HTTP 200 OK.
2. Setiap elemen array memiliki atribut `bookingid` bernilai angka.
"""
    },
    {
        "category": "API - Contract Schema & Errors",
        "category_desc": "Pengujian kepatuhan kontrak schema Zod dan penanganan error",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-SCHEMA-02] Create Contract - Validate contract schema on successful booking creation",
        "script": "tests/api/bookingSchema.spec.ts",
        "arguments": "npx playwright test tests/api/bookingSchema.spec.ts -g 'should validate contract schema on successful booking creation'",
        "tags": ["regression", "api", "schema"],
        "text": """### Endpoint
`POST /booking`

### Tujuan
Memverifikasi struktur objek `booking` hasil pembuatan sesuai kontrak Zod BookingDetailsSchema.

### Hasil yang Diharapkan
HTTP 200 OK dan seluruh field tanggal, nama, harga, status deposit terisi sesuai skema.
"""
    },
    {
        "category": "API - Contract Schema & Errors",
        "category_desc": "Pengujian kepatuhan kontrak schema Zod dan penanganan error",
        "plan": api_plan,
        "priority": p3,
        "summary": "[API-SCHEMA-03] 404 Not Found - Return 404 for non-existent booking ID",
        "script": "tests/api/bookingSchema.spec.ts",
        "arguments": "npx playwright test tests/api/bookingSchema.spec.ts -g 'should return 404 for non-existent booking ID'",
        "tags": ["regression", "api", "negative"],
        "text": """### Endpoint
`GET /booking/99999999`

### Tujuan
Memverifikasi penanganan saat mencari data booking ID yang tidak tersedia di database.

### Hasil yang Diharapkan
HTTP 404 Not Found.
"""
    },
    {
        "category": "API - Contract Schema & Errors",
        "category_desc": "Pengujian kepatuhan kontrak schema Zod dan penanganan error",
        "plan": api_plan,
        "priority": p3,
        "summary": "[API-SCHEMA-04] Malformed Payload - Reject malformed payload missing mandatory dates",
        "script": "tests/api/bookingSchema.spec.ts",
        "arguments": "npx playwright test tests/api/bookingSchema.spec.ts -g 'should reject malformed payload missing mandatory dates'",
        "tags": ["regression", "api", "negative"],
        "text": """### Endpoint
`POST /booking`

### Payload
Payload tanpa properti wajib `bookingdates` (checkin / checkout).

### Hasil yang Diharapkan
HTTP 400 Bad Request atau 500 Internal Server Error (request ditolak).
"""
    },
    {
        "category": "API - Contract Schema & Errors",
        "category_desc": "Pengujian kepatuhan kontrak schema Zod dan penanganan error",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-SCHEMA-05] Unauthorized Update - Reject update without authorization token",
        "script": "tests/api/bookingSchema.spec.ts",
        "arguments": "npx playwright test tests/api/bookingSchema.spec.ts -g 'should reject update without authorization token'",
        "tags": ["regression", "api", "security"],
        "text": """### Endpoint
`PUT /booking/1`

### Skenario
Mengirim request update tanpa cookie atau token otorisasi yang valid.

### Hasil yang Diharapkan
HTTP 403 Forbidden.
"""
    },

    # -------------------------------------------------------------
    # API - Booking Query (tests/api/bookingQuery.spec.ts)
    # -------------------------------------------------------------
    {
        "category": "API - Parameterized Query Filtering",
        "category_desc": "Pengujian data-driven filtering pencarian booking berdasarkan query parameter",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-QUERY-01] Firstname Filter - Parameterized query filtering by unique firstname",
        "script": "tests/api/bookingQuery.spec.ts",
        "arguments": "npx playwright test tests/api/bookingQuery.spec.ts -g 'Filter by unique firstname'",
        "tags": ["regression", "api", "query"],
        "text": """### Endpoint
`GET /booking?firstname=<unique_firstname>`

### Langkah-langkah
1. Buat booking baru dengan firstname unik tergenerasi secara dinamis.
2. Panggil GET `/booking` dengan query parameter `firstname`.
3. Validasi skema response list.
4. Periksa ID booking yang baru dibuat ada di dalam hasil query.
5. Teardown: hapus booking yang dibuat.

### Hasil yang Diharapkan
Response mengembalikan data booking yang sesuai filter firstname.
"""
    },
    {
        "category": "API - Parameterized Query Filtering",
        "category_desc": "Pengujian data-driven filtering pencarian booking berdasarkan query parameter",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-QUERY-02] Lastname Filter - Parameterized query filtering by unique lastname",
        "script": "tests/api/bookingQuery.spec.ts",
        "arguments": "npx playwright test tests/api/bookingQuery.spec.ts -g 'Filter by unique lastname'",
        "tags": ["regression", "api", "query"],
        "text": """### Endpoint
`GET /booking?lastname=<unique_lastname>`

### Langkah-langkah
1. Buat booking baru dengan lastname unik tergenerasi secara dinamis.
2. Panggil GET `/booking` dengan query parameter `lastname`.
3. Validasi skema response list.
4. Periksa ID booking yang baru dibuat ada di dalam hasil query.
5. Teardown: hapus booking yang dibuat.

### Hasil yang Diharapkan
Response mengembalikan data booking yang sesuai filter lastname.
"""
    },
    {
        "category": "API - Parameterized Query Filtering",
        "category_desc": "Pengujian data-driven filtering pencarian booking berdasarkan query parameter",
        "plan": api_plan,
        "priority": p2,
        "summary": "[API-QUERY-03] Combined Filter - Parameterized query filtering by both firstname and lastname",
        "script": "tests/api/bookingQuery.spec.ts",
        "arguments": "npx playwright test tests/api/bookingQuery.spec.ts -g 'Filter by both firstname and lastname combined'",
        "tags": ["regression", "api", "query"],
        "text": """### Endpoint
`GET /booking?firstname=<fname>&lastname=<lname>`

### Langkah-langkah
1. Buat booking baru dengan kombinasi nama depan dan nama belakang unik.
2. Panggil GET `/booking` dengan kedua query parameter tersebut.
3. Validasi skema response list.
4. Periksa ID booking yang baru dibuat ada di dalam hasil query.
5. Teardown: hapus booking yang dibuat.

### Hasil yang Diharapkan
Pencarian gabungan mengembalikan record yang memenuhi kedua kriteria filter secara presisi.
"""
    },
]

print(f"Total test cases to process: {len(test_cases_data)}")

created_count = 0
updated_count = 0

for item in test_cases_data:
    cat, _ = Category.objects.get_or_create(
        product=product,
        name=item["category"],
        defaults={"description": item.get("category_desc", "")}
    )

    tc, created = TestCase.objects.get_or_create(
        summary=item["summary"],
        defaults={
            "text": item["text"],
            "script": item["script"],
            "arguments": item["arguments"],
            "is_automated": True,
            "case_status": status_confirmed,
            "category": cat,
            "priority": item["priority"],
            "author": admin_user,
            "default_tester": admin_user,
        }
    )

    if not created:
        tc.text = item["text"]
        tc.script = item["script"]
        tc.arguments = item["arguments"]
        tc.is_automated = True
        tc.case_status = status_confirmed
        tc.category = cat
        tc.priority = item["priority"]
        tc.save()
        updated_count += 1
    else:
        created_count += 1

    # Link tags
    for tag_name in item["tags"]:
        tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
        tc.tag.add(tag_obj)

    # Link to specific Plan (E2E or API)
    specific_plan = item["plan"]
    TestCasePlan.objects.get_or_create(plan=specific_plan, case=tc)

    # Link to Master Plan
    TestCasePlan.objects.get_or_create(plan=master_plan, case=tc)

print(f"Done! Created: {created_count}, Updated: {updated_count}")
print(f"Total TestCase count in DB: {TestCase.objects.count()}")
print(f"Total TestPlans in DB: {TestPlan.objects.count()}")
