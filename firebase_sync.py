"""
Firebase Authentication + Firestore REST helpers for LoanTrack.

Only the Python standard library is used so the packaged app stays small and
needs no extra dependencies. The app keeps SQLite as its local source of truth;
this module handles the cloud side of the sync.
"""

from __future__ import annotations

import json
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
FIRESTORE_BASE = "https://firestore.googleapis.com/v1"
USER_AGENT = "LoanTrack/1.1 (Windows)"

FIREBASE_RULES = """rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null
                         && request.auth.uid == userId;
    }
  }
}"""

VALID_STATUSES = {"Baru", "Dalam Proses", "Hantar Bank", "Diluluskan", "Ditolak", "Selesai"}


class CloudError(Exception):
    """An error that can be shown to the user."""

    def __init__(self, message: str, code: str = "", detail: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail


def _friendly_auth_error(code: str) -> str:
    mapping = {
        "EMAIL_NOT_FOUND": "Email atau kata laluan tidak betul.",
        "INVALID_PASSWORD": "Email atau kata laluan tidak betul.",
        "INVALID_LOGIN_CREDENTIALS": "Email atau kata laluan tidak betul.",
        "INVALID_EMAIL": "Format email tidak sah.",
        "MISSING_EMAIL": "Sila masukkan email.",
        "MISSING_PASSWORD": "Sila masukkan kata laluan.",
        "EMAIL_EXISTS": "Email ini sudah didaftarkan. Sila log masuk.",
        "WEAK_PASSWORD": "Kata laluan terlalu lemah. Gunakan sekurang-kurangnya 6 aksara.",
        "OPERATION_NOT_ALLOWED": "Log masuk Email/Kata Laluan belum diaktifkan dalam Firebase Console.",
        "PASSWORD_LOGIN_DISABLED": "Log masuk Email/Kata Laluan belum diaktifkan dalam Firebase Console.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Terlalu banyak percubaan. Cuba lagi sebentar nanti.",
        "API_KEY_INVALID": "Web API key tidak sah. Semak semula tetapan Firebase.",
        "INVALID_API_KEY": "Web API key tidak sah. Semak semula tetapan Firebase.",
        "CONFIGURATION_NOT_FOUND": "Projek Firebase tidak dijumpai. Semak Project ID.",
        "PROJECT_NOT_FOUND": "Projek Firebase tidak dijumpai. Semak Project ID.",
        "PERMISSION_DENIED": "Kebenaran Firestore ditolak. Pastikan peraturan keselamatan telah diterbitkan.",
        "UNAUTHENTICATED": "Sesi tamat. Sila log masuk semula.",
        "TOKEN_EXPIRED": "Sesi tamat. Sila log masuk semula.",
        "USER_NOT_FOUND": "Sesi tamat. Sila log masuk semula.",
        "INVALID_REFRESH_TOKEN": "Sesi tamat. Sila log masuk semula.",
        "invalid_grant": "Sesi tamat. Sila log masuk semula.",
        "USER_DISABLED": "Akaun ini telah dinyahdayakan.",
        "QUOTA_EXCEEDED": "Had penggunaan Firebase telah dicapai. Cuba lagi kemudian.",
    }
    return mapping.get(code, "Ralat Firebase tidak dijangka.")


def _extract_error(body: str) -> tuple[str, str]:
    """Return (code, human message-ish text) from a Firebase error body."""
    try:
        parsed = json.loads(body)
    except Exception:
        return "", body[:500]
    error = parsed.get("error")
    if isinstance(error, dict):
        message = str(error.get("message", ""))
        # Identity Toolkit returns e.g. "EMAIL_NOT_FOUND"
        code = message.split(" : ")[0].strip()
        return code, message
    if isinstance(error, str):
        return error, str(parsed.get("error_description", error))
    return "", body[:500]


def _http_json(method: str, url: str, payload=None, token: str | None = None,
               form: bool = False, context: str = "generic") -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if payload is not None:
        if form:
            data = urlparse.urlencode(payload).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urlrequest.Request(url, data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        code, message = _extract_error(body)
        if exc.code == 401 or "UNAUTHENTICATED" in body or code in {
            "TOKEN_EXPIRED", "USER_NOT_FOUND", "INVALID_REFRESH_TOKEN", "invalid_grant",
        }:
            raise CloudError("Sesi tamat. Sila log masuk semula.", code="auth_expired",
                             detail=body) from None
        if "API_KEY_INVALID" in body or "INVALID_API_KEY" in body:
            raise CloudError("Web API key tidak sah. Semak semula tetapan Firebase.",
                             code="invalid_api_key", detail=body) from None
        if context == "auth":
            if code == "CONFIGURATION_NOT_FOUND" or "CONFIGURATION_NOT_FOUND" in body:
                raise CloudError(
                    "Firebase Authentication belum disediakan untuk projek ini. "
                    "Buka Firebase Console → Authentication → Get started, kemudian "
                    "aktifkan Email/Password.",
                    code="auth_not_configured", detail=body,
                ) from None
            if code in {"OPERATION_NOT_ALLOWED", "PASSWORD_LOGIN_DISABLED"}:
                raise CloudError(
                    "Log masuk Email/Password belum diaktifkan. Buka Authentication "
                    "→ Sign-in method → Email/Password → Enable.",
                    code="operation_not_allowed", detail=body,
                ) from None
            if exc.code == 429:
                raise CloudError("Terlalu banyak percubaan. Cuba lagi sebentar nanti.",
                                 code="quota", detail=body) from None
            raise CloudError(
                _friendly_auth_error(code) if code else
                f"Firebase Authentication memulangkan ralat HTTP {exc.code}.",
                code=code or f"http_{exc.code}", detail=body,
            ) from None
        if "SERVICE_DISABLED" in body or "has not been used in project" in body:
            raise CloudError(
                "Cloud Firestore API belum diaktifkan untuk projek ini. Buka "
                "Firebase Console → Firestore Database → Create database.",
                code="service_disabled", detail=body,
            ) from None
        if exc.code == 403 or "PERMISSION_DENIED" in body:
            raise CloudError(
                "Kebenaran Firestore ditolak. Pastikan peraturan keselamatan "
                "Firestore dalam Firebase Console sudah diterbitkan.",
                code="permission_denied", detail=body,
            ) from None
        if exc.code == 429:
            raise CloudError("Terlalu banyak permintaan ke Firebase. Cuba sebentar nanti.",
                             code="quota", detail=body) from None
        if exc.code == 404 or "CONFIGURATION_NOT_FOUND" in body or "PROJECT_NOT_FOUND" in body \
                or "does not exist" in body:
            raise CloudError("Projek Firebase atau Firestore tidak dijumpai. "
                             "Semak Project ID dan pastikan Firestore telah dicipta.",
                             code="not_found", detail=body) from None
        raise CloudError(_friendly_auth_error(code) if code else
                         f"Firebase memulangkan ralat HTTP {exc.code}.",
                         code=code or f"http_{exc.code}", detail=body) from None
    except urlerror.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise CloudError(
            "Tidak dapat menghubungi Firebase. Semak sambungan internet anda.",
            code="network", detail=str(reason),
        ) from None
    except TimeoutError:
        raise CloudError("Sambungan ke Firebase tamat masa. Cuba lagi.",
                         code="network") from None
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise CloudError("Firebase memulangkan respons yang tidak sah.",
                         code="bad_response", detail=raw[:500]) from None


class FirebaseAuth:
    """Email/password authentication against Firebase Identity Toolkit."""

    def __init__(self, api_key: str):
        self.api_key = (api_key or "").strip()

    def _url(self, action: str) -> str:
        return f"{AUTH_BASE}:{action}?key={urlparse.quote(self.api_key, safe='')}"

    def sign_in(self, email: str, password: str) -> dict:
        data = _http_json("POST", self._url("signInWithPassword"), {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }, context="auth")
        return self._session_from(data)

    def sign_up(self, email: str, password: str) -> dict:
        data = _http_json("POST", self._url("signUp"), {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }, context="auth")
        return self._session_from(data)

    @staticmethod
    def _session_from(data: dict) -> dict:
        try:
            return {
                "uid": data["localId"],
                "email": data.get("email", ""),
                "id_token": data["idToken"],
                "refresh_token": data["refreshToken"],
                "expires_in": int(data.get("expiresIn", 3600)),
            }
        except (KeyError, TypeError, ValueError):
            raise CloudError("Firebase tidak memulangkan sesi yang sah.",
                             code="bad_response", detail=str(data)[:500]) from None

    def refresh(self, refresh_token: str) -> dict:
        url = f"{TOKEN_URL}?key={urlparse.quote(self.api_key, safe='')}"
        data = _http_json("POST", url, {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }, form=True, context="token")
        if "id_token" not in data:
            raise CloudError("Sesi tamat. Sila log masuk semula.",
                             code="auth_expired", detail=str(data)[:500])
        return {
            "id_token": data["id_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "uid": data.get("user_id", ""),
            "expires_in": int(data.get("expires_in", 3600)),
        }


# --------------------------------------------------------- Firestore values --
def fs_value(value):
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, (int, float)):
        return {"doubleValue": float(value)}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, list):
        return {"arrayValue": {"values": [fs_value(item) for item in value]}}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {str(k): fs_value(v) for k, v in value.items()}}}
    return {"stringValue": str(value)}


def fs_unwrap(value):
    if not isinstance(value, dict):
        return None
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        try:
            return int(value["integerValue"])
        except (TypeError, ValueError):
            return None
    if "doubleValue" in value:
        try:
            return float(value["doubleValue"])
        except (TypeError, ValueError):
            return None
    if "stringValue" in value:
        return value["stringValue"]
    if "timestampValue" in value:
        return value["timestampValue"]
    if "arrayValue" in value:
        return [fs_unwrap(item) for item in value.get("arrayValue", {}).get("values", [])]
    if "mapValue" in value:
        fields = value.get("mapValue", {}).get("fields", {})
        return {key: fs_unwrap(item) for key, item in fields.items()}
    return None


def loan_to_fields(loan, history) -> dict:
    """Convert a local loan row + history list into Firestore fields."""
    history_list = []
    for entry in history:
        history_list.append({
            "from_status": entry["from_status"],
            "to_status": entry["to_status"],
            "note": entry["note"] or "",
            "changed_at": entry["changed_at"],
        })
    return {
        "cloud_id": fs_value(loan["cloud_id"]),
        "name": fs_value(loan["name"]),
        "ic": fs_value(loan["ic"]),
        "car": fs_value(loan["car"]),
        "bank": fs_value(loan["bank"]),
        "amount": fs_value(loan["amount"]),
        "applied_date": fs_value(loan["applied_date"]),
        "status": fs_value(loan["status"]),
        "notes": fs_value(loan["notes"] or ""),
        "created_at": fs_value(loan["created_at"]),
        "updated_at": fs_value(loan["updated_at"]),
        "schema_version": fs_value(1),
        "history": fs_value(history_list),
    }


def fields_to_loan(fields: dict, doc_id: str = "") -> tuple[dict, list[dict]]:
    """Parse a Firestore document's fields into (loan dict, history list)."""
    raw = {key: fs_unwrap(value) for key, value in (fields or {}).items()}
    cloud_id = raw.get("cloud_id") or doc_id
    updated_at = raw.get("updated_at")
    if not cloud_id or not updated_at:
        raise ValueError("Rekod awan tidak lengkap")
    status = raw.get("status") or "Baru"
    if status not in VALID_STATUSES:
        status = "Baru"
    amount = raw.get("amount")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None
    loan = {
        "cloud_id": str(cloud_id),
        "name": str(raw.get("name") or ""),
        "ic": str(raw.get("ic") or ""),
        "car": str(raw.get("car") or ""),
        "bank": str(raw.get("bank") or ""),
        "amount": amount,
        "applied_date": str(raw.get("applied_date") or ""),
        "status": status,
        "notes": str(raw.get("notes") or ""),
        "created_at": str(raw.get("created_at") or updated_at),
        "updated_at": str(updated_at),
    }
    history = []
    for item in raw.get("history") or []:
        if not isinstance(item, dict):
            continue
        to_status = item.get("to_status")
        if to_status not in VALID_STATUSES:
            continue
        history.append({
            "from_status": item.get("from_status"),
            "to_status": to_status,
            "note": str(item.get("note") or ""),
            "changed_at": str(item.get("changed_at") or updated_at),
        })
    history.sort(key=lambda h: h["changed_at"])
    return loan, history


class FirestoreClient:
    """Minimal Firestore REST client scoped to one authenticated user."""

    def __init__(self, project_id: str, id_token: str):
        self.project_id = project_id
        self.id_token = id_token
        self.base = (
            f"{FIRESTORE_BASE}/projects/{urlparse.quote(project_id, safe='')}"
            "/databases/(default)/documents"
        )

    def _doc_name(self, uid: str, cloud_id: str) -> str:
        return (f"projects/{self.project_id}/databases/(default)/documents/"
                f"users/{uid}/loans/{cloud_id}")

    def _list_collection(self, uid: str, name: str) -> list[dict]:
        documents = []
        page_token = ""
        while True:
            url = (f"{self.base}/users/{urlparse.quote(uid, safe='')}/"
                   f"{name}?pageSize=300")
            if page_token:
                url += f"&pageToken={urlparse.quote(page_token, safe='')}"
            data = _http_json("GET", url, token=self.id_token, context="firestore")
            documents.extend(data.get("documents", []) or [])
            page_token = data.get("nextPageToken", "")
            if not page_token:
                break
        return documents

    def list_loans(self, uid: str) -> list[dict]:
        return self._list_collection(uid, "loans")

    def list_tombstones(self, uid: str) -> list[dict]:
        return self._list_collection(uid, "tombstones")

    def commit(self, writes: list[dict]) -> None:
        if not writes:
            return
        url = f"{self.base}:commit"
        for start in range(0, len(writes), 400):
            chunk = writes[start:start + 400]
            data = _http_json("POST", url, {"writes": chunk},
                              token=self.id_token, context="firestore")
            # A 200 response can still carry per-write errors; treat hard errors only.
            for result in data.get("writeResults", []) or []:
                if "error" in result:
                    msg = result["error"].get("message", "Ralat menulis Firestore")
                    raise CloudError(f"Firebase menolak sebahagian data: {msg}",
                                     code="write_failed", detail=str(result))

    def make_update(self, uid: str, loan, history) -> dict:
        return {
            "update": {
                "name": self._doc_name(uid, loan["cloud_id"]),
                "fields": loan_to_fields(loan, history),
            }
        }

    def make_delete(self, uid: str, cloud_id: str) -> dict:
        return {"delete": self._doc_name(uid, cloud_id)}

    def make_tombstone(self, uid: str, cloud_id: str, deleted_at: str) -> dict:
        name = (f"projects/{self.project_id}/databases/(default)/documents/"
                f"users/{uid}/tombstones/{cloud_id}")
        return {
            "update": {
                "name": name,
                "fields": {
                    "cloud_id": fs_value(cloud_id),
                    "deleted_at": fs_value(deleted_at or ""),
                },
            }
        }


def doc_ids(documents: list[dict]) -> set[str]:
    """Return the document IDs from a Firestore list response."""
    ids = set()
    for document in documents:
        name = document.get("name", "")
        if name:
            ids.add(name.rsplit("/", 1)[-1])
    return ids
