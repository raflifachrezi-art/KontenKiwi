#!/usr/bin/env python3
"""
Create Mobile Android Test Cases, link to Plan 4, and create Test Run with Executions in Kiwi TCMS.
"""
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django_comments.models import Comment

settings.EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

from tcms.management.models import Product, Version, Build, Classification, Priority, Tag
from tcms.testcases.models import TestCase, TestCaseStatus, Category, BugSystem
from tcms.testplans.models import TestPlan, PlanType, TestCasePlan
from tcms.testruns.models import TestRun, TestExecution, TestExecutionStatus
from tcms.bugs.models import Bug, Severity
from tcms.core.contrib.linkreference.models import LinkReference
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

print(f"Executing as user: {admin_user.username}")

product = Product.objects.get(id=3) # Konten.com Mobile Android
version = Version.objects.filter(product=product).first()
if not version:
    version, _ = Version.objects.get_or_create(product=product, value="1.0.0")

build = Build.objects.filter(version=version).first()
if not build:
    build, _ = Build.objects.get_or_create(version=version, name="1.0.0", defaults={"is_active": True})

plan = TestPlan.objects.get(id=4) # Exploratory Testing Findings - Konten.com Mobile Apps Android

status_confirmed = TestCaseStatus.objects.get(name="CONFIRMED")
p1 = Priority.objects.get(value="P1")
p2 = Priority.objects.get(value="P2")
p3 = Priority.objects.get(value="P3")

exec_passed = TestExecutionStatus.objects.get(name="PASSED")
exec_failed = TestExecutionStatus.objects.get(name="FAILED")
exec_blocked = TestExecutionStatus.objects.get(name="BLOCKED")

# Setup Categories
categories = {
    "Auth": Category.objects.get_or_create(product=product, name="Authentication & Onboarding")[0],
    "Home": Category.objects.get_or_create(product=product, name="Home & Dashboard")[0],
    "Campaign": Category.objects.get_or_create(product=product, name="Campaign & Submission")[0],
    "Wallet": Category.objects.get_or_create(product=product, name="Wallet & Withdrawal")[0],
    "Profile": Category.objects.get_or_create(product=product, name="Profile & Settings")[0],
    "Security": Category.objects.get_or_create(product=product, name="Security & Compatibility")[0],
}

# Test Cases data: (summary, category_key, priority, type_tag, text, expected_status, bug_details)
TEST_CASES = [
    (
        "TC-AND-AUTH-001: Splash Screen & Onboarding Carousel Navigation",
        "Auth", p2, "Functional",
        "1. Buka aplikasi Konten.com dari state fresh install.\n2. Verifikasi splash screen logo muncul.\n3. Swipe horizontal slide 1 sampai 3.\n4. Tap tombol Mulai / Lewati.",
        exec_passed, None
    ),
    (
        "TC-AND-AUTH-002: Validasi Form Login dengan Field Kosong",
        "Auth", p1, "Validation",
        "1. Masuk ke halaman Login.\n2. Kosongkan email dan password.\n3. Tap tombol Login.\n4. Verifikasi pesan validasi merah muncul di bawah masing-masing field.",
        exec_passed, None
    ),
    (
        "TC-AND-AUTH-003: Format Email Tidak Valid pada Login - Text Truncation Check",
        "Auth", p2, "UI/Visual Bug",
        "1. Masuk ke halaman Login.\n2. Input email tidak valid: '123' atau 'notanemail'.\n3. Tap tombol Login.\n4. Periksa apakah pesan error terpotong di akhir dengan elipsis (...).",
        exec_failed, {
            "summary": "Pesan validasi email terpotong elipsis (contoh: namakamu@domain.co...)",
            "desc": "Teks pesan error 'Format email tidak valid (contoh: namakamu@domain.com)' terpotong menjadi '...domain.co...' karena batas maxLines: 1 tanpa auto-wrap."
        }
    ),
    (
        "TC-AND-AUTH-004: Toggle Masking Password (Show/Hide Password)",
        "Auth", p3, "Functional",
        "1. Pada field password, ketikkan password.\n2. Tap icon mata / tombol 'Tampilkan kata sandi'.\n3. Verifikasi teks password berubah menjadi plain text.\n4. Tap kembali untuk menyembunyikan.",
        exec_passed, None
    ),
    (
        "TC-AND-AUTH-005: Login dengan Kredensial Salah / Tidak Terdaftar",
        "Auth", p1, "Functional",
        "1. Masuk ke halaman Login.\n2. Masukkan email terdaftar dengan password salah.\n3. Tap Login.\n4. Verifikasi muncul snackbar toast peringatan 'Email atau password salah'.",
        exec_passed, None
    ),
    (
        "TC-AND-AUTH-006: Login Berhasil dengan Kredensial Valid",
        "Auth", p1, "Functional",
        "1. Masukkan email 'qatest0001@yopmail.com'.\n2. Masukkan password '@Qa1234567'.\n3. Tap Login.\n4. Verifikasi user berhasil masuk ke dashboard utama dengan greeting 'Siang, Qatest-001!'.",
        exec_passed, None
    ),
    (
        "TC-AND-AUTH-007: Validasi Form Reset Password - Text Truncation Bug",
        "Auth", p2, "UI/Visual Bug",
        "1. Pada layar Login, tap 'Lupa password?'.\n2. Masukkan email tidak valid pada form Reset Password.\n3. Tap 'Kirim Link Reset Password'.\n4. Verifikasi pesan validasi error.",
        exec_failed, {
            "summary": "Pesan error validasi email terpotong elipsis pada halaman Reset Password",
            "desc": "Pesan validasi format email terpotong sama seperti pada form login karena komponen TextFormField yang dipakai bersama."
        }
    ),
    (
        "TC-AND-AUTH-008: Registrasi Akun - Validasi Field Kosong & Pushed-off Footer",
        "Auth", p2, "Layout/UI Bug",
        "1. Dari halaman landing/login, tap 'Daftar Akun'.\n2. Perhatikan teks footer 'Sudah punya akun? Login'.\n3. Langsung tekan tombol 'Daftar Akun' dengan form kosong.\n4. Perhatikan posisi footer setelah error message muncul.",
        exec_failed, {
            "summary": "Link footer 'Sudah punya akun? Login' terdorong keluar layar saat validasi error aktif",
            "desc": "Tinggi vertikal 3 pesan error validasi mendorong tombol Daftar Akun ke paling bawah dan menyebabkan footer link login terpotong keluar viewport."
        }
    ),
    (
        "TC-AND-AUTH-009: Registrasi Akun - Unchecked Checkbox Syarat & Ketentuan",
        "Auth", p2, "Validation/UX",
        "1. Isi semua field registrasi dengan data valid.\n2. Biarkan checkbox Syarat & Ketentuan tidak dicentang.\n3. Tekan 'Daftar Akun'.\n4. Verifikasi apakah ada indikator error visual pada checkbox.",
        exec_failed, {
            "summary": "Checkbox Syarat & Ketentuan tidak memiliki feedback visual saat submit dicegah",
            "desc": "Tombol submit tidak merespon tanpa memberikan highlight merah atau pesan error pada checkbox persetujuan."
        }
    ),
    (
        "TC-AND-AUTH-010: Masuk Tanpa Login (Guest Mode Navigation)",
        "Auth", p3, "Functional",
        "1. Buka landing page.\n2. Tap tombol 'Masuk Tanpa Login ->'.\n3. Verifikasi aplikasi mengizinkan navigasi eksplorasi publik.",
        exec_passed, None
    ),
    (
        "TC-AND-AUTH-011: Logout Akun dari Menu Pengaturan",
        "Auth", p2, "Functional",
        "1. Masuk ke Tab Profil.\n2. Tap icon/menu 'Pengaturan'.\n3. Scroll ke bawah dan tap 'Keluar Akun'.\n4. Verifikasi sesi dihapus dan aplikasi kembali ke landing screen.",
        exec_passed, None
    ),
    (
        "TC-AND-HOME-001: Header Greeting & Saldo Tersedia",
        "Home", p2, "UI/Data Rendering",
        "1. Buka Tab Home.\n2. Verifikasi greeting pengguna (misal 'Siang, Qatest-001!').\n3. Verifikasi kartu Saldo Tersedia dan tombol 'Withdraw'.",
        exec_passed, None
    ),
    (
        "TC-AND-HOME-002: Sembunyikan dan Tampilkan Saldo (Eye Toggle)",
        "Home", p3, "Functional/Privacy",
        "1. Pada kartu Saldo Tersedia, tap icon mata untuk sembunyikan saldo.\n2. Verifikasi nominal berubah menjadi 'Saldo tersembunyi'.\n3. Tap kembali untuk menampilkan nominal.",
        exec_passed, None
    ),
    (
        "TC-AND-HOME-003: List Campaign Diikuti - Bug Rendering String 'null'",
        "Home", p2, "Data Integrity/UI Bug",
        "1. Pada Tab Home, periksa carousel section 'Campaign Diikuti'.\n2. Swipe horizontal kartu campaign yang diikuti.\n3. Verifikasi ada/tidaknya kartu yang merender teks 'null'.",
        exec_failed, {
            "summary": "Kartu campaign merender judul string literal 'null' pada carousel Home",
            "desc": "Data campaign yang tidak memiliki judul/gambar fallback merender string 'null' langsung ke tampilan UI pengguna."
        }
    ),
    (
        "TC-AND-HOME-004: Switch View Mode 'Semua Campaign' (Grid vs List View)",
        "Home", p3, "UI/Functional",
        "1. Scroll ke section 'Semua Campaign'.\n2. Tap toggle 'Tampilan daftar'.\n3. Verifikasi layout berubah menjadi list.\n4. Tap toggle 'Tampilan grid'.\n5. Verifikasi layout berubah menjadi 2 kolom grid.",
        exec_passed, None
    ),
    (
        "TC-AND-HOME-005: Pencarian dan Filter Campaign di Beranda",
        "Home", p2, "Functional",
        "1. Tap field 'Cari campaign...'.\n2. Masukkan kata kunci pencarian.\n3. Tap tombol 'Filter' untuk memfilter berdasarkan kategori/budget.\n4. Verifikasi daftar campaign terfilter.",
        exec_passed, None
    ),
    (
        "TC-AND-HOME-006: Widget Misi Onboarding (Floating Action Button)",
        "Home", p3, "Functional/UI",
        "1. Tap tombol melayang 'Misi onboarding, Buka daftar misi dan bantuan' di kanan bawah.\n2. Verifikasi bottom sheet atau dialog misi clipper terbuka dengan benar.",
        exec_passed, None
    ),
    (
        "TC-AND-CAMP-001: Navigasi dan Filter Tab Campaign",
        "Campaign", p2, "Functional",
        "1. Tap Tab 2 'Campaign' di bottom navigation bar.\n2. Verifikasi daftar campaign aktif dimuat dengan rate hadiah, jenis (UGC/CLIPPING), dan progress budget.",
        exec_passed, None
    ),
    (
        "TC-AND-CAMP-002: Keamanan Data Brief Campaign terhadap XSS & SSTI Injection",
        "Campaign", p1, "Security/Data Rendering",
        "1. Buka campaign dengan brief yang mengandung payload XSS <script>alert('hello')</script> atau ${7*7}.\n2. Verifikasi payload dirender aman sebagai teks biasa tanpa memicu eksekusi skrip atau server template parsing.",
        exec_passed, None
    ),
    (
        "TC-AND-CAMP-003: Modal Bottom Sheet Panduan Submit Video",
        "Campaign", p2, "UI/Guidance Flow",
        "1. Pilih campaign dan tap aksi submit.\n2. Verifikasi modal 'Sebelum Submit, Kamu Harus Perhatikan Ini' muncul dengan panduan durasi 60 detik & batas 24 jam.\n3. Tap 'Selanjutnya' untuk melanjutkan alur submit.",
        exec_passed, None
    ),
    (
        "TC-AND-CAMP-004: Validasi Checkbox Persetujuan Brief sebelum Submit Video",
        "Campaign", p1, "Validation",
        "1. Buka halaman detail submit video.\n2. Jangan centang checkbox 'Saya sudah membaca dan memahami brief ini'.\n3. Tap tombol 'Mulai Buat Video'.\n4. Verifikasi sistem menolak aksi atau tombol tetap nonaktif.",
        exec_passed, None
    ),
    (
        "TC-AND-WALL-001: Tampilan Ringkasan Saldo dan Riwayat Transaksi Wallet",
        "Wallet", p2, "Functional/Financial",
        "1. Tap Tab 4 'Wallet' pada navigasi utama.\n2. Verifikasi saldo utama, pending balance, dan riwayat mutasi / penarikan dana ditampilkan akurat.",
        exec_passed, None
    ),
    (
        "TC-AND-WALL-002: Alur Penarikan Saldo (Withdrawal Flow)",
        "Wallet", p1, "Functional",
        "1. Tap tombol 'Withdraw' dari Beranda atau Wallet.\n2. Masukkan nominal penarikan valid.\n3. Pilih rekening / e-wallet tujuan.\n4. Konfirmasi penarikan dana.",
        exec_passed, None
    ),
    (
        "TC-AND-WALL-003: Konfigurasi Metode Withdrawal di Pengaturan",
        "Wallet", p2, "Functional/Settings",
        "1. Masuk ke Profil -> Pengaturan -> Metode Withdrawal.\n2. Tambahkan rekening bank atau e-wallet baru.\n3. Verifikasi validasi nomor rekening dan nama pemilik.",
        exec_passed, None
    ),
    (
        "TC-AND-PROF-001: Tampilan Header Profil & Tier Badge",
        "Profile", p2, "UI/Profile",
        "1. Tap Tab 5 'Profile'.\n2. Verifikasi avatar huruf/foto, nama clipper, tanggal bergabung.\n3. Verifikasi tier badge ('Base Clipper' / 'Verified Clipper').",
        exec_passed, None
    ),
    (
        "TC-AND-PROF-002: Kartu Statistik Analitik Clipper",
        "Profile", p2, "Data Rendering",
        "1. Pada halaman Profil, periksa kartu 'Analitik'.\n2. Verifikasi metrik Total Pendapatan, Video Approved, dan Total Views sesuai dengan data backend.",
        exec_passed, None
    ),
    (
        "TC-AND-PROF-003: Integrasi Akun Media Sosial & Discord",
        "Profile", p2, "Integration/Functional",
        "1. Periksa bagian 'Akun Media Sosial' dan 'Hubungkan Akun Discord'.\n2. Verifikasi daftar akun terhubung ditampilkan lengkap dengan jumlah follower dan status update.",
        exec_passed, None
    ),
    (
        "TC-AND-PROF-004: QA Network Inspector (Alice Inspector)",
        "Profile", p3, "Debug/QA Tool",
        "1. Buka Profil -> Pengaturan.\n2. Tap opsi 'Inspector Jaringan (QA)'.\n3. Verifikasi HTTP inspector (Alice) terbuka dan mencatat request/response Supabase dan Gateway API.",
        exec_passed, None
    ),
    (
        "TC-AND-SEC-001: Proteksi FLAG_SECURE pada MainActivity",
        "Security", p1, "Security/Compliance",
        "1. Buka aplikasi pada perangkat Android fisik.\n2. Lakukan tangkapan layar (screencap) melalui adb atau shortcut tombol HP.\n3. Verifikasi gambar hasil tangkapan di-blackout secara native oleh OS Android.",
        exec_passed, None
    ),
    (
        "TC-AND-COMPAT-001: Kompatibilitas UI & Rendering pada Android 16 (API 36)",
        "Security", p2, "Compatibility",
        "1. Jalankan aplikasi pada perangkat fisik Android 16 (API 36).\n2. Verifikasi elemen UI tidak terpotong oleh Dynamic Island / display cutout kamera atas.\n3. Verifikasi transisi antar layar berjalan mulus pada refresh rate 60-120Hz.",
        exec_passed, None
    ),
]

site = Site.objects.get_current()
med_severity = Severity.objects.get(name="Medium")

# Create or reuse Test Run (Test Runner)
test_run = TestRun.objects.filter(summary="Automated & Exploratory Test Run - Konten.com Mobile Android (v1.0.0)").first()
if not test_run:
    test_run = TestRun.objects.create(
        summary="Automated & Exploratory Test Run - Konten.com Mobile Android (v1.0.0)",
        plan=plan,
        build=build,
        manager=admin_user,
        default_tester=admin_user,
        notes="Eksekusi test case menyeluruh pada aplikasi Android Konten.com (API 36) menggunakan ADB automation dan verifikasi fisik.",
        start_date=timezone.now(),
        stop_date=timezone.now() + timedelta(hours=1)
    )

print(f"Using Test Run ID: {test_run.id} - {test_run.summary}")

created_count = 0
passed_count = 0
failed_count = 0

for summary, cat_key, prio, type_tag, text, expected_exec_status, bug_info in TEST_CASES:
    cat = categories[cat_key]
    
    # Check if TestCase already exists or create new
    tc = TestCase.objects.filter(summary=summary, category=cat).first()
    if not tc:
        tc = TestCase.objects.create(
            summary=summary,
            category=cat,
            priority=prio,
            author=admin_user,
            default_tester=admin_user,
            case_status=status_confirmed,
            text=text,
            notes=f"Test Type: {type_tag} | Target: Android 16 (API 36)"
        )
    
    # Link Tag
    tag, _ = Tag.objects.get_or_create(name=type_tag)
    tc.tag.add(tag)
    
    # Link to Plan
    TestCasePlan.objects.get_or_create(plan=plan, case=tc, defaults={"sortkey": 10})
    
    # Create or update TestExecution in TestRun
    execution = TestExecution.objects.filter(run=test_run, case=tc).first()
    if not execution:
        case_ver = tc.history.latest().history_id if tc.history.exists() else 1
        execution = TestExecution.objects.create(
            run=test_run,
            case=tc,
            build=build,
            tested_by=admin_user,
            assignee=admin_user,
            case_text_version=case_ver,
            status=expected_exec_status,
            start_date=timezone.now() - timedelta(minutes=5),
            stop_date=timezone.now(),
        )
    else:
        execution.status = expected_exec_status
        execution.tested_by = admin_user
        execution.save()
    
    # Add comment if not already added
    ct_exec = ContentType.objects.get_for_model(TestExecution)
    if not Comment.objects.filter(content_type=ct_exec, object_pk=str(execution.pk)).exists():
        Comment.objects.create(
            content_type=ct_exec,
            object_pk=str(execution.pk),
            site=site,
            user=admin_user,
            comment=f"Executed via ADB test automation on Android 16 device. Result: {expected_exec_status.name}."
        )
    
    # Link Bug if failed
    if bug_info:
        bug_summary = f"[{tc.summary.split(':')[0]}] {bug_info['summary']}"
        bug = Bug.objects.filter(summary=bug_summary, product=product).first()
        if not bug:
            bug = Bug.objects.create(
                summary=bug_summary,
                product=product,
                version=version,
                build=build,
                reporter=admin_user,
                assignee=admin_user,
                severity=med_severity,
                status=True,
            )
            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(Bug),
                object_pk=str(bug.pk),
                site=site,
                user=admin_user,
                comment=f"Steps to Reproduce & Details:\n{bug_info['desc']}\n\nLinked Test Case: {tc.summary}"
            )
        execution.bugs.add(bug)
    
    if expected_exec_status == exec_passed:
        passed_count += 1
    elif expected_exec_status == exec_failed:
        failed_count += 1
        
    created_count += 1

print(f"\nImport Completed Successfully:")
print(f"Total Test Cases Processed: {created_count}")
print(f"Test Plan: ID {plan.id} - {plan.name}")
print(f"Test Run: ID {test_run.id} - {test_run.summary}")
print(f"Executions: {passed_count} PASSED, {failed_count} FAILED")
