# Firebase Cloud Messaging (FCM) — Setup Guide

The code is already wired for FCM on both sides. You only need to create a Firebase project
and produce **two different files**. Don't mix them up — this is the #1 source of confusion:

| File | What it is | Where it goes | Secret? |
| --- | --- | --- | --- |
| **`google-services.json`** | Client config for the Android app (project number, API key, app ID) | `app_flutter/android/app/google-services.json` | embedded in the APK; git-ignored |
| **Service-account key** (e.g. `patient-care-xxxx-firebase-adminsdk-xxxx.json`) | Backend admin credentials with a **private key** | Dokploy env var `FIREBASE_CREDS_JSON` (single line) | **YES — keep secret** |

FCM is free (the Spark/no-card plan is enough). No credit card required.

---

## Step 1 — Create a Firebase project
1. Go to <https://console.firebase.google.com> and sign in with a Google account.
2. Click **Add project** (a.k.a. *Create a project*).
3. Name it e.g. **`patient-care`** → **Continue**.
4. **Google Analytics:** toggle **OFF** (not needed for FCM) → **Continue**.
5. Wait for provisioning → **Continue**. You're now on the project overview.

---

## Step 2 — Register the Android app → get `google-services.json` (File 1)
1. On the project overview, click the **Android** icon (*"Add app" → Android*).
   (Or: ⚙️ **Project settings → Your apps → Add app → Android**.)
2. **Android package name** — type **exactly**:
   ```
   com.patientcare.patient_care
   ```
   ⚠️ It must match the app's `applicationId` (`app_flutter/android/app/build.gradle.kts:26`).
   A mismatch = the app will never receive pushes.
3. **App nickname** (optional): `Patient Care Nurse`.
4. **Debug signing certificate SHA-1** (optional): **leave blank** — FCM does not need it.
5. Click **Register app**.
6. Click **Download google-services.json**.
7. Put the file at:
   ```
   app_flutter/android/app/google-services.json
   ```
8. On the console's "Add Firebase SDK" / Gradle steps → click **Next, Next, Continue to console**
   and ignore them. This repo's Gradle is **already** configured
   (`android/settings.gradle.kts:24` declares the plugin, `app/build.gradle.kts:6` applies it).
   You only drop the file in — no Gradle edits.

---

## Step 3 — Generate the service-account key → `FIREBASE_CREDS_JSON` (File 2)
1. ⚙️ **Project settings → Service accounts** tab.
2. Under **Firebase Admin SDK**, click **Generate new private key** → **Generate key**.
   A JSON file downloads (it contains `"private_key": "-----BEGIN PRIVATE KEY-----…"`).
   **This is a secret — treat it like a password.**
3. Convert it to a **single line** (the backend does `json.loads()` on it directly):
   ```bash
   jq -c . ~/Downloads/patient-care-*-firebase-adminsdk-*.json
   ```
   Copy the one-line output.
   - ✅ Use `jq -c` (or `python3 -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1]))))" <file>`).
   - ❌ Do **not** hand-delete the newlines (it corrupts the `private_key`).
   - ❌ Do **not** base64-encode it — `backend/app/fcm.py:26` expects raw JSON, not base64.

---

## Step 4 — Give the backend the key (Dokploy)
1. Dokploy → your Compose service → **Environment**.
2. Set:
   ```
   FIREBASE_CREDS_JSON=<paste the single-line JSON from Step 3>
   ```
3. **Redeploy** the service.
4. Confirm: the first time an alert fans out, the logs print `firebase-admin initialized`
   (`backend/app/fcm.py:30`). Until the var is set, the app runs fine and logs
   `FCM not configured` instead.

---

## Step 5 — Build the app with `google-services.json` (File 1)
On a machine with the Flutter SDK (not this Pi):
```bash
cd app_flutter
flutter pub get
flutter build apk --release --dart-define=BACKEND_URL=https://ptcare.welocalhost.com
```
Install `build/app/outputs/flutter-apk/app-release.apk` on the nurse phone.

---

## Step 6 — Verify end-to-end
1. Open the app → **allow the notification permission** when prompted (Android 13+).
2. **Sign in as a nurse.** On successful login the FCM token auto-registers via
   `POST /api/v1/me/fcm-tokens` (`app_flutter/lib/fcm/fcm_setup.dart:64`).
3. **Join the bed** (the nurse must be a member of the bed to receive its pushes —
   push fans out only to that bed's nurses, `backend/app/routes/gateway.py:44-63`).
4. Trigger an alert (tap **Water** on the device, or simulate it). Expect:
   - a **push notification** on the phone (works even if the app is backgrounded/killed), **and**
   - the in-app **live feed** updates over WebSocket.

### If push doesn't arrive
- Phone has **no notification permission** → enable it in Android app settings.
- Nurse **hasn't joined that bed** → no membership = no push (by design).
- `FIREBASE_CREDS_JSON` malformed → backend logs `firebase-admin init failed` — re-do Step 3 with `jq -c`.
- Package mismatch → `google-services.json` must be for `com.patientcare.patient_care`.
- Rare: sends fail with `PERMISSION_DENIED` → enable **Firebase Cloud Messaging API** in
  Google Cloud Console → *APIs & Services → Library* (normally on by default).
