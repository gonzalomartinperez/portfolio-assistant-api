# Assistant gallery, light and dark

These are browser captures of the native portfolio UI. Completed answers and citations are replayed from an
authorized GPT-6 Luna evaluation through deterministic HTTP/SSE fixtures. They show the application, not a
mockup or an enabled production site. Click a frame to open the original PNG.

## Light theme

The narrow viewport uses the same conversation implementation as the desktop layout. Long responses scroll
inside the panel; the composer stays separate from the reading surface.

<p align="center">
  <a href="../assets/gallery/07-mobile-es.png"><img src="../assets/gallery/07-mobile-es.png" width="320" alt="Mobile assistant in Spanish and the light theme, with a recorded public-answer replay and a visible composer"></a>
</p>

## Dark theme

### Expanded conversation

A recruiter's question, a substantive answer, inspectable source spans and a follow-up composer in the same
conversation surface.

<p align="center">
  <a href="../assets/gallery/02-expanded-conversation.png"><img src="../assets/gallery/02-expanded-conversation.png" width="900" alt="Expanded conversation showing a recruiter question, a recorded model answer, three public source links and an unsent follow-up"></a>
</p>

### From first question to recovery

<table>
  <tr>
    <td valign="top" width="50%"><strong>1. A welcoming starting point</strong><br>Identity, scope and a useful starter question.<br><a href="../assets/gallery/01-welcome.png"><img src="../assets/gallery/01-welcome.png" width="420" alt="Compact assistant empty state with an avatar, introductory copy, a starter question and the composer"></a></td>
    <td valign="top" width="50%"><strong>2. A compact, sourced answer</strong><br>A recorded achievement with estimates clearly qualified.<br><a href="../assets/gallery/03-compact-sources.png"><img src="../assets/gallery/03-compact-sources.png" width="420" alt="Compact assistant displaying a question about a Rampy achievement, a qualified answer, public sources and the composer"></a></td>
  </tr>
  <tr>
    <td valign="top"><strong>3. Conversation controls</strong><br>History and conversation actions belong to the shared native feature.<br><a href="../assets/gallery/04-history.png"><img src="../assets/gallery/04-history.png" width="420" alt="Conversation drawer with a new-conversation action and saved-conversation controls"></a></td>
    <td valign="top"><strong>4. Honest interruption</strong><br>Partial output stays readable; recovery checks saved history.<br><a href="../assets/gallery/05-interrupted.png"><img src="../assets/gallery/05-interrupted.png" width="420" alt="Interrupted response with preserved partial text and an explicit connection-ended notice"></a></td>
  </tr>
  <tr>
    <td valign="top"><strong>5. Unavailable service</strong><br>A safe notice with recovery controls.<br><a href="../assets/gallery/06-unavailable.png"><img src="../assets/gallery/06-unavailable.png" width="420" alt="Assistant showing a safe unavailable-service notice and recovery controls"></a></td>
    <td valign="top"><strong>6. Compact dark theme</strong><br>The hero capture of the README, in English.<br><a href="../assets/assistant/compact-dark-en.png"><img src="../assets/assistant/compact-dark-en.png" width="420" alt="Compact assistant in the dark theme answering a question about a Rampy achievement with two public sources"></a></td>
  </tr>
</table>

## Provenance and limits

[Gallery provenance](../evidence/archive/2026-10/readme-gallery.md) distinguishes recorded model output,
fixture failures and browser emulation. Captures do not prove physical-device, production-routing or
live-provider availability. No credentials or private visitor messages are included.
