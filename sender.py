from __future__ import annotations

import html
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from summarizer import SECTION_META
from timeutils import now_in_timezone


SIGNAL_COLOR = {"HIGH": "#b42318", "MEDIUM": "#b54708"}
SECTION_STYLE = {
    "global": {
        "eyebrow": "WORLD",
        "accent": "#155eef",
        "soft": "#eff4ff",
        "dark": "#0b1f4b",
    },
    "ai_tech": {
        "eyebrow": "AI + TECH",
        "accent": "#7f56d9",
        "soft": "#f4f3ff",
        "dark": "#2d1b69",
    },
    "india": {
        "eyebrow": "INDIA",
        "accent": "#e04f16",
        "soft": "#fff4ed",
        "dark": "#7a271a",
    },
}


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


def _published_label(value: str) -> str:
    try:
        published = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return published.strftime("%d %b, %H:%M UTC")
    except (AttributeError, ValueError):
        return "Latest reporting"


def _source_mark(source: str) -> str:
    words = [word for word in source.replace("&", " ").split() if word]
    if not words:
        return "N"
    return "".join(word[0] for word in words[:2]).upper()


def _image_block(story: dict, style: dict, height: int = 260) -> str:
    image_url = story.get("image_url", "")
    if image_url:
        return f"""
        <img src="{html.escape(image_url, quote=True)}" width="100%" alt=""
          style="display:block;width:100%;height:{height}px;object-fit:cover;border:0;">
        """
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
      style="background:{style['dark']};">
      <tr>
        <td height="{height}" valign="middle" align="center"
          style="height:{height}px;padding:0 28px;color:#ffffff;">
          <div style="font-size:12px;font-weight:800;letter-spacing:3px;opacity:.7;">
            MORNING INTELLIGENCE
          </div>
          <div style="font-size:42px;font-weight:800;line-height:1;margin-top:12px;">
            {html.escape(style['eyebrow'])}
          </div>
        </td>
      </tr>
    </table>
    """


def _source_row(story: dict, style: dict) -> str:
    source = html.escape(story["source"])
    signal = html.escape(story.get("signal", "MEDIUM"))
    confidence = story.get("confidence", "single-source")
    evidence_count = len(story.get("evidence_sources", [])) or 1
    evidence = "Verified across sources" if confidence == "corroborated" else "Single-source report"
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td width="38" valign="middle">
          <div style="width:32px;height:32px;line-height:32px;border-radius:50%;
            background:{style['dark']};color:#ffffff;text-align:center;
            font-size:11px;font-weight:800;">{html.escape(_source_mark(story['source']))}</div>
        </td>
        <td valign="middle" style="font-size:12px;line-height:1.35;color:#667085;">
          <strong style="color:#101828;">{source}</strong><br>
          {_published_label(story.get('published_at', ''))}
        </td>
        <td align="right" valign="middle">
          <span style="display:inline-block;padding:6px 9px;border-radius:999px;
            background:{style['soft']};color:{style['accent']};font-size:10px;
            font-weight:800;letter-spacing:.6px;">{signal} SIGNAL</span>
          <div style="font-size:10px;color:#98a2b3;margin-top:5px;">
            {html.escape(evidence)} &middot; {evidence_count}
          </div>
        </td>
      </tr>
    </table>
    """


def _feature_card(story: dict, style: dict) -> str:
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
      style="background:#ffffff;border:1px solid #e4e7ec;border-radius:18px;
      overflow:hidden;box-shadow:0 8px 24px rgba(16,24,40,.08);">
      <tr><td>{_image_block(story, style)}</td></tr>
      <tr>
        <td style="padding:22px 24px 24px;">
          {_source_row(story, style)}
          <h3 style="font-family:Arial,Helvetica,sans-serif;font-size:25px;line-height:1.2;
            letter-spacing:-.5px;margin:18px 0 10px;color:#101828;">
            {html.escape(story['headline'])}
          </h3>
          <p style="font-size:15px;line-height:1.65;margin:0;color:#475467;">
            {html.escape(story['summary'])}
          </p>
          <div style="margin:18px 0 0;padding:14px 16px;background:{style['soft']};
            border-left:4px solid {style['accent']};border-radius:0 10px 10px 0;
            color:#344054;font-size:13px;line-height:1.5;">
            <strong style="color:{style['dark']};">Why it matters</strong><br>
            {html.escape(story['why_it_matters'])}
          </div>
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
            style="margin-top:18px;">
            <tr>
              <td style="font-size:12px;line-height:1.45;color:#667085;padding-right:12px;">
                <strong style="color:#344054;">Watch next:</strong>
                {html.escape(story['watch_next'])}
              </td>
              <td align="right" width="126">
                <a href="{html.escape(story['url'], quote=True)}"
                  style="display:inline-block;padding:11px 16px;border-radius:999px;
                  background:#101828;color:#ffffff;text-decoration:none;font-size:12px;
                  font-weight:800;">Read story &rarr;</a>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """


def _compact_card(story: dict, style: dict) -> str:
    image_url = story.get("image_url", "")
    visual = (
        f'<img src="{html.escape(image_url, quote=True)}" class="compact-fallback" '
        'width="132" height="112" alt="" '
        'style="display:block;width:132px;height:112px;object-fit:cover;border-radius:12px;">'
        if image_url
        else f'<div class="compact-fallback" style="width:132px;height:112px;line-height:112px;background:{style["dark"]};'
        f'color:#ffffff;text-align:center;border-radius:12px;font-size:13px;font-weight:800;'
        f'letter-spacing:1px;">{html.escape(style["eyebrow"])}</div>'
    )
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
      style="margin-top:14px;background:#ffffff;border:1px solid #e4e7ec;
      border-radius:16px;">
      <tr>
        <td width="132" class="compact-visual" valign="top"
          style="padding:14px 0 14px 14px;">{visual}</td>
        <td class="compact-copy" valign="top" style="padding:15px 16px;">
          <div style="font-size:10px;font-weight:800;letter-spacing:.7px;
            color:{style['accent']};">
            {html.escape(story.get('signal', 'MEDIUM'))} &middot;
            {html.escape(story['source'])}
          </div>
          <h3 style="font-size:17px;line-height:1.28;margin:7px 0 6px;color:#101828;">
            {html.escape(story['headline'])}
          </h3>
          <p style="font-size:12px;line-height:1.48;margin:0;color:#667085;">
            {html.escape(story['summary'])}
          </p>
          <a href="{html.escape(story['url'], quote=True)}"
            style="display:inline-block;margin-top:9px;color:{style['accent']};
            text-decoration:none;font-size:11px;font-weight:800;">Open report &rarr;</a>
        </td>
      </tr>
    </table>
    """


def render_html(digest: dict, settings: dict) -> str:
    now = now_in_timezone(settings["timezone"])
    name = settings["profile"].get("name")
    greeting = f"Good morning, {html.escape(name)}" if name else "Good morning"

    section_blocks = []
    for key, (title, subtitle) in SECTION_META.items():
        stories = digest.get("sections", {}).get(key, [])
        style = SECTION_STYLE[key]
        cards = (
            _feature_card(stories[0], style)
            + "".join(_compact_card(story, style) for story in stories[1:])
            if stories
            else '<p style="color:#667085;font-size:14px;">No high-value new stories.</p>'
        )
        section_blocks.append(
            f"""
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
              style="margin-top:42px;">
              <tr>
                <td>
                  <div style="font-size:10px;font-weight:800;letter-spacing:2px;
                    color:{style['accent']};">{style['eyebrow']}</div>
                  <h2 style="font-size:28px;letter-spacing:-.5px;margin:5px 0 4px;
                    color:#101828;">{title}</h2>
                  <p style="font-size:13px;margin:0 0 17px;color:#667085;">{subtitle}</p>
                  {cards}
                </td>
              </tr>
            </table>
            """
        )

    connections = digest.get("connections", [])
    connections_html = ""
    if connections:
        items = "".join(
            f"""
            <tr>
              <td width="31" valign="top" style="padding:7px 0;">
                <div style="width:24px;height:24px;line-height:24px;border-radius:50%;
                  background:#ffffff;color:#101828;text-align:center;font-size:11px;
                  font-weight:800;">{index}</div>
              </td>
              <td style="padding:7px 0 7px 8px;font-size:13px;line-height:1.5;color:#d0d5dd;">
                {html.escape(item)}
              </td>
            </tr>
            """
            for index, item in enumerate(connections, 1)
        )
        connections_html = f"""
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
          style="margin-top:22px;background:#101828;border-radius:16px;">
          <tr>
            <td style="padding:20px 22px;">
              <div style="font-size:10px;font-weight:800;letter-spacing:2px;color:#84adff;">
                CONNECTING SIGNALS
              </div>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                style="margin-top:8px;">{items}</table>
            </td>
          </tr>
        </table>
        """

    return f"""<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    @media only screen and (max-width:600px) {{
      .outer-pad {{ padding:0 !important; }}
      .shell {{ border-radius:0 !important; }}
      .content-pad {{ padding:28px 18px 36px !important; }}
      .header-pad {{ padding:22px 18px !important; }}
      .compact-visual {{ width:96px !important; }}
      .compact-visual img, .compact-fallback {{
        width:96px !important;
        height:104px !important;
        line-height:104px !important;
      }}
      .compact-copy {{ padding:13px 12px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#eef1f5;font-family:Arial,Helvetica,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;">Your personalized briefing for {now:%B %d}.</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
    style="background:#eef1f5;">
    <tr>
      <td align="center" class="outer-pad" style="padding:24px 10px 46px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
          class="shell"
          style="max-width:720px;background:#f8fafc;border-radius:24px;overflow:hidden;">
          <tr>
            <td class="header-pad"
              style="padding:28px 32px 26px;background:#ffffff;border-bottom:1px solid #e4e7ec;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <div style="font-size:10px;font-weight:800;letter-spacing:2.2px;color:#155eef;">
                      THE DAILY SIGNAL
                    </div>
                    <div style="font-size:12px;color:#667085;margin-top:5px;">
                      {now:%A, %B %d, %Y} &middot; 7:00 AM IST
                    </div>
                  </td>
                  <td align="right">
                    <div style="display:inline-block;padding:8px 11px;border-radius:999px;
                      background:#101828;color:#ffffff;font-size:10px;font-weight:800;">
                      PERSONAL BRIEF
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="content-pad" style="padding:36px 32px 42px;">
              <h1 style="font-size:38px;line-height:1.08;letter-spacing:-1.2px;
                margin:0;color:#101828;">{greeting}.</h1>
              <p style="font-size:17px;line-height:1.65;color:#475467;margin:15px 0 0;">
                {html.escape(digest.get('executive_summary', ''))}
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                style="margin-top:24px;background:#155eef;border-radius:16px;">
                <tr>
                  <td style="padding:19px 21px;">
                    <div style="font-size:10px;font-weight:800;letter-spacing:2px;color:#b2ccff;">
                      WATCH TODAY
                    </div>
                    <div style="font-size:15px;line-height:1.55;margin-top:7px;color:#ffffff;">
                      {html.escape(digest.get('attention', ''))}
                    </div>
                  </td>
                </tr>
              </table>
              {connections_html}
              <div style="margin-top:18px;padding:14px 16px;border:1px dashed #98a2b3;
                border-radius:12px;color:#475467;font-size:12px;line-height:1.5;">
                <strong style="color:#101828;">Reality check:</strong>
                {html.escape(digest.get('counterpoint', ''))}
              </div>
              {''.join(section_blocks)}
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px;background:#101828;color:#98a2b3;
              font-size:11px;line-height:1.55;">
              <strong style="color:#ffffff;">The Daily Signal</strong><br>
              Curated by your personal intelligence agent from trusted publications.
              Summaries can be imperfect; original reporting is always linked.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
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
