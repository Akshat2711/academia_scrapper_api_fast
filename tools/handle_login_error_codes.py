# auth_response_handler.py

def handle_login_response(data: dict) -> dict:
    """
    Robust, future-proof login response classifier.

    RULE:
    - Only block when we are 100% sure it is a failure.
    - Unknown or new success shapes must NOT break login flow.
    """

    print(data)

    # -------------------------------------------------
    # Normalize text signals
    # -------------------------------------------------
    texts = []

    for key in ("detail", "message"):
        if isinstance(data.get(key), str):
            texts.append(data[key].lower())

    for err in data.get("errors", []):
        if isinstance(err, dict) and isinstance(err.get("message"), str):
            texts.append(err["message"].lower())

    # -------------------------------------------------
    # Normalize error codes
    # -------------------------------------------------
    error_codes = set()

    if isinstance(data.get("code"), str):
        error_codes.add(data["code"])

    for err in data.get("errors", []):
        if isinstance(err, dict) and isinstance(err.get("code"), str):
            error_codes.add(err["code"])

    passwordauth = data.get("passwordauth", {})

    # =================================================
    # 1️⃣ DEFINITIVE FAILURES (block)
    # =================================================
    if "P501" in error_codes:
        return {
            "success": False,
            "type": "OTP_EXPIRED",
            "code": "P501",
            "message": "One Time Password has expired",
            "raw": data
        }

    if "U401" in error_codes:
        return {
            "success": False,
            "type": "USER_NOT_FOUND",
            "code": "U401",
            "message": "User does not exist",
            "raw": data
        }

    if "P201" in error_codes:
        return {
            "success": False,
            "type": "OLD_PASSWORD",
            "code": "P201",
            "message": "Matched with old password",
            "raw": data
        }
    
    # Invalid password (definitive auth failure)
    if "IN102" in error_codes:
        return {
            "success": False,
            "type": "INVALID_PASSWORD",
            "code": "IN102",
            "message": (
                data.get("localized_message")
                or "Invalid password"
            ),
            "raw": data
        }




    # =================================================
    # 2️⃣ DEFINITIVE SUCCESSES (allow)
    # =================================================
    # Known success codes
    if data.get("code") in {"SI200", "SIGIN_SUCCESS"}:
        return {"success": True, "type": "SUCCESS"}

    # Redirect via codes or redirect_uri
    if (
        data.get("code") in {"SI302", "SI303"}
        or isinstance(passwordauth.get("redirect_uri"), str)
    ):
        return {"success": True, "type": "REDIRECT"}

    # Success text patterns (future-proof)
    SUCCESS_KEYWORDS = (
        "signin success",
        "login success",
        "successfully signed in",
        "pre announcement redirection",
        "redirect"
    )

    if any(any(k in t for k in SUCCESS_KEYWORDS) for t in texts):
        return {
            "success": True,
            "type": "TEXTUAL_SUCCESS",
            "message": next((t for t in texts if "success" in t), None)
        }

    # =================================================
    # 3️⃣ AMBIGUOUS / UNKNOWN → DO NOT BLOCK
    # =================================================
    # This is the critical safety net
    return {
        "success": True,
        "type": "AMBIGUOUS_SUCCESS",
        "message": "Unclassified response, allowing original flow",
        "raw": data
    }
