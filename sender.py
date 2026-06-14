from __future__ import annotations

import html
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from summarizer import SECTION_META
from timeutils import now_in_timezone


SIGNAL_COLOR = {"HIGH": "#b42318", "MEDIUM": "#b54708"}


def normalize_app_password(value: str) -> str:
    return "".join(value.split())


def _gmail_login(server: smtplib.SMTP, settings: dict) -> None:
    password = normalize_app_password(settings["gmail_app_password"])
    if len(password) != 16:
        raise RuntimeError(
            "GMAIL_APP_PASSWORD must be Google's 16-character App Password, "
            "not your normal Gmail password."
        )
    try:
        server.login(settings["gmail_address"].strip(), password)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "Gmail rejected GMAIL_ADDRESS/GMAIL_APP_PASSWORD. Generate a new "
            "16-character App Password from the same Google account used in "
            "GMAIL_ADDRESS, update the GitHub secret, and run again."
        ) from exc


def render_text(digest: dict) -> str:
    lines = [
        "YOUR MORNING INTELLIGENCE BRIEF",
        "",
        digest.get("executive_summary", ""),
        "",
        f"WATCH TODAY: {digest.get('attention', '')}",
        f"COUNTERPOINT: {digest.get('counterpoint', '')}",
    ]
    connections = digest.get("connections", [])
    if connections:
        lines.extend(["", "CONNECTING SIGNALS"])
        lines.extend(f"- {connection}" for connection in connections)
    for key, (title, _) in SECTION_META.items():
        lines.extend(["", title.upper()])
        stories = digest.get("sections", {}).get(key, [])
        if not stories:
            lines.append("No high-value new stories.")
        for story in stories:
            lines.extend(
                [
                    f"- {story['headline']} [{story.get('signal', 'MEDIUM')}]",
                    f"  {story['summary']}",
                    f"  Why it matters: {story['why_it_matters']}",
                    f"  Watch next: {story['watch_next']}",
                    f"  Evidence: {story.get('confidence', 'single-source')} "
                    f"({len(story.get('evidence_sources', [])) or 1} source(s))",
                    f"  {story['source']}: {story['url']}",
                ]
            )
    return "\n".join(lines)


def render_html(digest: dict, settings: dict) -> str:
    now = now_in_timezone(settings["timezone"])
    name = settings["profile"].get("name")
    greeting = f"Good morning, {html.escape(name)}." if name else "Good morning."

    section_blocks = []
    for key, (title, subtitle) in SECTION_META.items():
        story_blocks = []
        for story in digest.get("sections", {}).get(key, []):
            signal = html.escape(story.get("signal", "MEDIUM"))
            evidence_count = len(story.get("evidence_sources", [])) or 1
            confidence = html.escape(story.get("confidence", "single-source"))
            story_blocks.append(
                f"""
                <article style="padding:20px 0;border-top:1px solid #e7e5e4;">
                  <div style="font-size:11px;font-weight:700;letter-spacing:.08em;color:{SIGNAL_COLOR.get(signal, '#57534e')};">{signal} SIGNAL &middot; {html.escape(story['source'])}</div>
                  <h3 style="font-size:19px;line-height:1.3;margin:7px 0 8px;color:#1c1917;">{html.escape(story['headline'])}</h3>
                  <p style="font-size:15px;line-height:1.6;margin:0 0 10px;color:#44403c;">{html.escape(story['summary'])}</p>
                  <p style="font-size:14px;line-height:1.5;margin:0 0 8px;color:#292524;"><strong>Why it matters:</strong> {html.escape(story['why_it_matters'])}</p>
                  <p style="font-size:13px;line-height:1.5;margin:0;color:#78716c;"><strong>Watch next:</strong> {html.escape(story['watch_next'])}</p>
                  <p style="font-size:12px;line-height:1.5;margin:8px 0 0;color:#78716c;"><strong>Evidence:</strong> {confidence}, {evidence_count} source(s)</p>
                  <a href="{html.escape(story['url'], quote=True)}" style="display:inline-block;margin-top:12px;color:#1d4ed8;font-size:13px;font-weight:600;text-decoration:none;">Read original &rarr;</a>
                </article>
                """
            )
        if not story_blocks:
            story_blocks.append(
                '<p style="color:#78716c;font-size:14px;">No high-value new stories.</p>'
            )
        section_blocks.append(
            f"""
            <section style="margin-top:34px;">
              <h2 style="font-size:22px;margin:0;color:#1c1917;">{title}</h2>
              <p style="font-size:13px;margin:5px 0 14px;color:#78716c;">{subtitle}</p>
              {''.join(story_blocks)}
            </section>
            """
        )

    connections = digest.get("connections", [])
    connections_html = ""
    if connections:
        items = "".join(
            f'<li style="margin:8px 0;">{html.escape(item)}</li>' for item in connections
        )
        connections_html = f"""
        <section style="margin:26px 0;padding:18px;background:#fafaf9;border:1px solid #e7e5e4;">
          <div style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#57534e;">CONNECTING SIGNALS</div>
          <ul style="font-size:14px;line-height:1.55;margin:8px 0 0;padding-left:19px;color:#292524;">{items}</ul>
        </section>
        """

    return f"""<!doctype html>
<html>
<body style="margin:0;background:#f5f5f4;font-family:Arial,Helvetica,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;">Your personalized briefing for {now:%B %d}.</div>
  <main style="max-width:680px;margin:0 auto;background:#ffffff;padding:36px 34px;">
    <div style="font-size:12px;font-weight:700;letter-spacing:.12em;color:#1d4ed8;">MORNING INTELLIGENCE &middot; {now:%A, %B %d, %Y}</div>
    <h1 style="font-size:31px;line-height:1.15;margin:12px 0 16px;color:#0c0a09;">{greeting}</h1>
    <p style="font-size:17px;line-height:1.65;color:#292524;margin:0;">{html.escape(digest.get('executive_summary', ''))}</p>
    <div style="margin:24px 0;padding:16px 18px;background:#eff6ff;border-left:4px solid #2563eb;">
      <div style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#1d4ed8;">WATCH TODAY</div>
      <div style="font-size:15px;line-height:1.5;margin-top:5px;color:#1e3a8a;">{html.escape(digest.get('attention', ''))}</div>
    </div>
    {connections_html}
    <div style="margin:18px 0;color:#57534e;font-size:13px;line-height:1.5;"><strong>Counterpoint:</strong> {html.escape(digest.get('counterpoint', ''))}</div>
    {''.join(section_blocks)}
    <footer style="margin-top:38px;padding-top:18px;border-top:1px solid #e7e5e4;color:#a8a29e;font-size:11px;line-height:1.5;">
      Built for you by your local news agent. Editorial summaries can be wrong; source links are always included for verification.
    </footer>
  </main>
</body>
</html>"""


def save_preview(digest: dict, settings: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(digest, settings), encoding="utf-8")


def send_digest(digest: dict, settings: dict) -> None:
    now = now_in_timezone(settings["timezone"])
    message = EmailMessage()
    message["Subject"] = f"Morning Intelligence | {now:%a, %d %b}"
    message["From"] = settings["gmail_address"]
    message["To"] = settings["recipient"]
    message.set_content(render_text(digest))
    message.add_alternative(render_html(digest, settings), subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls(context=context)
        _gmail_login(server, settings)
        server.send_message(message)


def send_alert(article, settings: dict) -> None:
    message = EmailMessage()
    message["Subject"] = f"Intelligence Alert | {article.title[:70]}"
    message["From"] = settings["gmail_address"]
    message["To"] = settings["recipient"]
    sources = ", ".join(article.corroborating_sources or (article.source,))
    message.set_content(
        "\n".join(
            [
                "HIGH-PRIORITY INTELLIGENCE ALERT",
                "",
                article.title,
                "",
                article.description,
                "",
                f"Why it surfaced: {', '.join(article.score_reasons)}",
                f"Evidence: {article.confidence}; {sources}",
                f"Score: {article.score}",
                "",
                article.url,
            ]
        )
    )
    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls(context=context)
        _gmail_login(server, settings)
        server.send_message(message)
