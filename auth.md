# Logins

| Account | Email | Password | Used in |
| --- | --- | --- | --- |
| Admin | `admin@patient.care` | `Test1234!` | Admin **website** (`http://localhost:8000`) |
| Nurse 1 | `nurse1@patient.care` | `Test1234!` | Nurse **app** |
| Nurse 2 | `nurse2@patient.care` | `Test1234!` | Nurse app |
| Nurse 3 | `nurse3@patient.care` | `Test1234!` | Nurse app |
| Nurse 4 | `nurse4@patient.care` | `Test1234!` | Nurse app |
| Nurse 5 | `nurse5@patient.care` | `Test1234!` | Nurse app |

- The **admin** signs into the website to create rooms/beds, pair devices, and manage nurses.
- A **nurse** signs into the app, then joins a **bed** with the join code shown on the
  website (Rooms & Beds → open a room → a bed's *Join code*). Requests from that bed's
  device are delivered only to nurses who joined it.
- Credentials are created by `backend/seed.py`. Re-run it any time to (idempotently)
  recreate the demo accounts, rooms, beds, and a paired device.
