---
task_id: T50
purpose: Post-show auto-respond template fired on every Tally form capture during EMEX 2026 show window.
format: transactional email template (plain-text + minimal HTML), Mailgun/SendGrid compatible
placeholders:
  - "{{PLACEHOLDER: founding-five microsite URL}}"
  - "{{PLACEHOLDER: Bradley email}}"
  - "{{PLACEHOLDER: Philippe email}}"
  - "{{PLACEHOLDER: Quintinity logo image URL — hosted, transparent PNG, max 240px wide}}"
  - "{{PLACEHOLDER: from-address — e.g. hello@quintinity.com}}"
  - "{{PLACEHOLDER: reply-to address — should land in a real inbox a human checks}}"
last_updated: 2026-04-29
---

# Post-show 24h auto-respond email

Two versions of the same body — plain-text (preferred for trust and deliverability) and a minimal HTML wrapper. Personalisation tags `{{first_name}}` and `{{company_name}}` are populated from the Tally form fields if captured; both render gracefully when empty.

## Subject

`Thanks for stopping by Quintinity at EMEX`

## Plain-text version

```
Hi {{first_name}},

Thanks for stopping by our stand at EMEX 2026 — it was good to meet
{{company_name}} and hear about your floor.

We'll be in touch within 5 working days to set up your free 1-hour AI
diagnostic call. The call is a real working session, not a sales
pitch — bring one shop-floor problem and we'll spend the hour digging
into it together.

If you'd like to read more in the meantime, the founding-five
partnership details are here:
{{PLACEHOLDER: founding-five microsite URL}}

Reply to this email any time — it lands in a real inbox.

Bradley Festraets — {{PLACEHOLDER: Bradley email}}
Philippe Crottet — {{PLACEHOLDER: Philippe email}}
Quintinity
```

## HTML version

Minimal template. No tracking pixels, no marketing graphics, no fancy CSS. The logo is the only image; everything else is plain text in a single-column layout. Tested for Outlook desktop, Gmail web, and iOS Mail.

```html
<!doctype html>
<html lang="en-NZ">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Thanks for stopping by Quintinity at EMEX</title>
</head>
<body style="margin:0;padding:0;background:#fafafa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#1a1a1a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#fafafa;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background:#ffffff;border:1px solid #e5e5e5;border-radius:6px;">
          <tr>
            <td style="padding:24px 32px;border-bottom:1px solid #f0f0f0;">
              <img src="{{PLACEHOLDER: Quintinity logo image URL — hosted, transparent PNG, max 240px wide}}"
                   alt="Quintinity"
                   width="160"
                   style="display:block;border:0;outline:none;text-decoration:none;">
            </td>
          </tr>
          <tr>
            <td style="padding:32px;font-size:16px;line-height:1.55;">
              <p style="margin:0 0 16px 0;">Hi {{first_name}},</p>

              <p style="margin:0 0 16px 0;">
                Thanks for stopping by our stand at EMEX 2026 — it was good to meet
                {{company_name}} and hear about your floor.
              </p>

              <p style="margin:0 0 16px 0;">
                We'll be in touch within 5 working days to set up your free 1-hour
                AI diagnostic call. The call is a real working session, not a
                sales pitch — bring one shop-floor problem and we'll spend the
                hour digging into it together.
              </p>

              <p style="margin:0 0 16px 0;">
                If you'd like to read more in the meantime, the founding-five
                partnership details are here:<br>
                <a href="{{PLACEHOLDER: founding-five microsite URL}}"
                   style="color:#0a5fff;text-decoration:underline;">
                  {{PLACEHOLDER: founding-five microsite URL}}
                </a>
              </p>

              <p style="margin:0 0 24px 0;">
                Reply to this email any time — it lands in a real inbox.
              </p>

              <p style="margin:0 0 4px 0;">
                Bradley Festraets — {{PLACEHOLDER: Bradley email}}<br>
                Philippe Crottet — {{PLACEHOLDER: Philippe email}}
              </p>
              <p style="margin:0;color:#666;">Quintinity</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

## Personalisation tags

| Tag | Source | Fallback when empty |
|---|---|---|
| `{{first_name}}` | Tally field `first_name` | Renders as "Hi ," — acceptable, but Tally form should mark first name required |
| `{{company_name}}` | Tally field `company` | Renders as "to meet  and hear about your floor" — fix Tally form to mark company required, or strip the clause server-side when blank |

## Sending rules (operator-side, NOT in the email)

Auto-fire on any Tally submission during the show window **2026-05-26 00:00 NZST through 2026-05-29 23:59 NZST** (inclusive of the three show days plus the day after). Outside that window, route Tally submissions to the human-triage inbox instead — the auto-respond loses its trade-show context past day-after, and a personal reply is better.

From-address: {{PLACEHOLDER: from-address — e.g. hello@quintinity.com}}. Reply-to: {{PLACEHOLDER: reply-to address — should land in a real inbox a human checks}}. Do not use a `noreply@` address — defeats the "reply to this any time" line and looks like marketing.
