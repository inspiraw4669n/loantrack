# LoanTrack — Pemantau Pinjaman Kereta

Aplikasi desktop untuk merekod dan memantau status permohonan pinjaman kereta
pelanggan. Setiap rekod menyimpan nama, No. IC, jenis kereta, bank, jumlah
pinjaman, tarikh mohon, status, catatan dan sejarah perubahan status.

SQLite kekal sebagai **storan utama** di komputer ini, dan data boleh
**disegerakkan ke Firebase Firestore** melalui akaun email/kata laluan.
Aplikasi masih boleh digunakan tanpa internet; perubahan akan disegerakkan
apabila sambungan tersedia. Terdapat juga **versi web** yang menggunakan data
Firestore yang sama:

**https://loanstatus-bc769.web.app**

---

## Cara menjalankan

### Pilihan 1 — Fail `.exe` (disyorkan)

Klik dua kali **`LoanTrack.exe`**.

Jika Windows SmartScreen memaparkan amaran (kerana aplikasi ini tidak ditandatangani
secara digital), klik **More info → Run anyway**.

### Pilihan 2 — Jalankan daripada kod sumber

Klik dua kali **`run_source.bat`**, atau jalankan:

```bat
python loan_tracker.py
```

Keperluan: Python 3.10 atau lebih baharu (Tkinter disertakan bersama Python).

---

## Versi web

Buka **https://loanstatus-bc769.web.app** dalam pelayar (desktop atau telefon).
Log masuk dengan **akaun Firebase yang sama** seperti dalam app desktop.

- Dashboard, carian, tapis status, tambah/edit/padam dan sejarah status.
- Data yang sama dengan app desktop — perubahan web dipaparkan secara langsung.
- App desktop akan menarik perubahan web pada **sync seterusnya** (buka app atau
  tekan **Awan & Sync → Sync Sekarang**).
- Padam dari web akan disegerakkan ke desktop melalui tombstone (desktop 1.1.1+).
- Web app di-host di Firebase Hosting; Access dibatasi oleh Firestore Rules.

Untuk deploy semula selepas mengubah folder `web/`:

```bat
firebase deploy --only hosting --project loanstatus-bc769
```

---

## Ciri-ciri

- **Papan pemuka ringkasan** — jumlah rekod, dalam proses, diluluskan dan ditolak.
- **Butiran lengkap** — nama, No. IC, jenis kereta, bank, jumlah pinjaman, tarikh
  mohon dan catatan.
- **Status pinjaman** — Baru, Dalam Proses, Hantar Bank, Diluluskan, Ditolak, Selesai.
- **Sejarah status automatik** — setiap perubahan status direkodkan bersama tarikh
  dan masa (termasuk status sebelum ini).
- **Carian segera** — cari melalui nama, No. IC, jenis kereta, bank, catatan atau status.
- **Tapis mengikut status** — klik status di bar sisi.
- **Eksport CSV** — eksport senarai semasa untuk dibuka dalam Excel atau Google Sheets.
- **Sync Firebase Firestore** — log masuk, sync automatik selepas setiap perubahan,
  dan butang Sync Sekarang. Data awan boleh dipulihkan pada pemasangan baharu.
- **Versi web berpusatkan Firestore** — akses dari telefon atau komputer lain.
- **Sandaran automatik setempat** — salinan SQLite sekali sehari (14 salinan terakhir).

---

## Menyediakan Firebase (sekali sahaja)

Aplikasi menyediakan panduan penuh dalam **Awan & Sync → Panduan persediaan**.
Ringkasannya:

1. Buka [Firebase Console](https://console.firebase.google.com/) dan cipta projek.
2. **Authentication → Sign-in method → Email/Password → Enable**.
3. **Firestore Database → Create database**, pilih edisi **Standard (Native mode)**
   (bukan MongoDB/Enterprise), gunakan database `(default)`, pilih lokasi terdekat
   dan mulakan dalam **Production mode**.
4. Buka tab **Rules** dan terbitkan peraturan ini:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /users/{userId}/{document=**} {
         allow read, write: if request.auth != null
                            && request.auth.uid == userId;
       }
     }
   }
   ```

5. **Project settings → General → Your apps → Add app → Web**. Daftarkan app
   dan salin nilai `projectId` dan `apiKey` daripada `firebaseConfig`.
6. Dalam LoanTrack: **Awan & Sync** → masukkan **Project ID** dan **Web API key**
   → **Simpan Konfigurasi** → **Daftar Akaun** atau **Log Masuk**.

Nota:

- Kata laluan anda **tidak disimpan**. Token sesi (refresh token) disimpan dalam
  pangkalan data setempat untuk log masuk automatik.
- Gunakan **satu akaun Firebase** untuk setiap folder data. Jika anda log masuk
  dengan akaun lain, data setempat akan digabungkan ke akaun tersebut.
- Jika API key dihadkan, benarkan **Identity Toolkit API** dan
  **Cloud Firestore API**. Jangan guna sekatan HTTP referrer untuk app desktop.
- Pelan Spark Firebase biasanya mencukupi untuk kegunaan kecil. Semak had
  semasa dalam Firebase Console.
- Data akan berada di awan Google. Pastikan penyimpanan No. IC di awan dibenarkan
  oleh dasar organisasi anda.

### Cara sync berfungsi

- Setiap perubahan setempat ditandakan dan dihantar ke Firestore secara automatik
  selepas beberapa saat.
- Semasa app dibuka atau apabila **Sync Sekarang** ditekan, rekod awan diambil
  dan digabungkan dengan rekod setempat.
- Jika rekod yang sama berubah di dua tempat, **rekod dengan `updated_at` terbaru
  menang** (last-write-wins).
- Padam rekod juga disegerakkan menggunakan tombstone setempat.
- Disyorkan untuk **satu peranti**. Untuk beberapa peranti, elakkan mengedit
  rekod yang sama serentak kerana tiada penggabungan sejarah terperinci.

---

## Lokasi data dan sandaran

```
data/
  loantrack.db          ← pangkalan data utama (SQLite)
  backups/
    loantrack_YYYY-MM-DD.db
```

- Fail data terletak di dalam folder yang sama dengan aplikasi/exe.
- Gunakan **Buka Folder Data** di bar sisi untuk membuka folder tersebut.
- Sandaran dibuat secara automatik setiap kali aplikasi dibuka; salinan lama
  (lebih 14 fail) akan dipadam.
- Untuk memindahkan semua data, salin folder `data` bersama aplikasi. Token
  Firebase yang tersimpan juga akan disalin; log masuk semula jika perlu.

---

## Papan kekunci

| Kekunci | Fungsi |
|---|---|
| `Ctrl + N` | Tambah pinjaman baharu |
| `Ctrl + F` | Fokus pada kotak carian |
| `Ctrl + E` | Eksport CSV |
| Klik dua kali baris | Buka butiran pinjaman |
| `Ctrl + S` (dalam dialog) | Simpan rekod |
| `Esc` (dalam dialog) | Tutup dialog |

---

## Privasi dan keselamatan

- SQLite setempat mengandungi No. IC dan **tidak disulitkan**. Lindungi komputer
  dan folder aplikasi.
- Jika sync Firebase diaktifkan, data (termasuk No. IC) disimpan dalam Firestore.
  Peraturan keselamatan di atas memastikan hanya akaun pengguna itu boleh
  mengakses data tersebut.
- **Kata laluan Firebase tidak disimpan**, tetapi refresh token sesi disimpan
  dalam SQLite untuk log masuk automatik. Log keluar untuk membuang token tersebut.
- Fail sandaran dan eksport CSV juga mengandungi No. IC — kendalikan dengan
  berhati-hati.
- Aplikasi tidak menghantar telemetri. Hanya Firebase Auth dan Firestore dihubungi
  apabila sync/log masuk digunakan.

---

## Masalah biasa

| Masalah | Penyelesaian |
|---|---|
| “Web API key tidak sah” | Salin semula `apiKey` daripada Firebase config. Pastikan ia daripada projek yang betul. |
| “Log masuk Email/Kata Laluan belum diaktifkan” | Aktifkan Email/Password dalam Authentication → Sign-in method. |
| “Kebenaran Firestore ditolak” | Terbitkan peraturan keselamatan di atas dalam tab Rules. |
| “Firestore tidak dijumpai” | Cipta Firestore Database dan semak Project ID. |
| “Tidak dapat menghubungi Firebase” | Semak internet/firewall; data setempat tetap selamat dan sync akan dicuba semula. |
| “Sesi tamat” | Log masuk semula. Simpan kata laluan anda di tempat selamat. |

---

## Membina semula `LoanTrack.exe`

PyInstaller diperlukan. Jalankan **`build_exe.bat`** atau:

```bat
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name LoanTrack --icon "assets\icon.ico" --add-data "assets;assets" loan_tracker.py
copy /Y "dist\LoanTrack.exe" "LoanTrack.exe"
```

PyInstaller akan menyertakan `firebase_sync.py` secara automatik kerana ia
diimport oleh `loan_tracker.py`.

---

## Struktur projek

```
loan_tracker.py        Kod sumber app desktop (Python + Tkinter + SQLite)
firebase_sync.py       Auth + Firestore REST (hanya pustaka piawai Python)
LoanTrack.exe          Aplikasi desktop siap untuk Windows
run_source.bat         Pelancar untuk menjalankan daripada kod sumber
build_exe.bat          Skrip membina semula fail .exe
web/                   Versi web (HTML/CSS/JS + Firebase Web SDK)
firebase.json          Konfigurasi Firebase Hosting
.firebaserc            Projek Firebase lalai untuk deploy
assets/
  icon.ico / icon.png  Ikon aplikasi
README.md              Fail ini
data/                  Dicipta secara automatik (pangkalan data + sandaran)
```
