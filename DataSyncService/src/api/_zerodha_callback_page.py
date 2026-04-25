import html

from fastapi.responses import HTMLResponse

from ..config import settings


def callback_page(status: str, account_id: str | None, message: str) -> HTMLResponse:
    safe_status = html.escape(status)
    safe_account = html.escape(account_id or "unknown")
    safe_message = html.escape(message)
    safe_return = html.escape(settings.zerodha_return_url, quote=True)
    body = f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Zerodha Login</title></head>
    <body style="font-family:system-ui;margin:32px;background:#0b0f14;color:#e5edf5">
      <h2>Zerodha {safe_status}</h2>
      <p>Account: <strong>{safe_account}</strong></p><p>{safe_message}</p>
      <p><a href="{safe_return}" style="color:#67e8f9">Return to cockpit</a></p>
      <script>
        const payload = {{ source: 'zerodha-auth', status: {safe_status!r}, accountId: {safe_account!r}, message: {safe_message!r} }};
        if (window.opener) {{ window.opener.postMessage(payload, '*'); window.close(); }}
      </script>
    </body></html>
    """
    return HTMLResponse(body)
