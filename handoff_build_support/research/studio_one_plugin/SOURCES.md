# Sources checked (27 Sep 2026)

Only pages or files actually opened or searched in this session are listed. Search-summary-only items are marked as such.

## Studio One / Fender Studio Pro
- **[S1]** PreSonus, *Studio One 7 Release Notes* (PDF on assets.ctfassets.net, file `Studio_One_7_-_Release_Notes.pdf`). 7.0.0 (9 Oct 2024) "CLAP plug-in and instrument support"; 7.0.1 "[CLAP] Freeze on instantiating certain plug-ins"; 7.2 (3 Jun 2025) "[CLAP] Latency compensation not working properly".
- **[S2]** Fender, *Fender Studio Pro 8.0.2 Release Notes* (PDF on assets.ctfassets.net, file `Fender_Studio_Pro_8.0.2_-_Release_Notes.pdf`). 8.0.0 (13 Jan 2026), 8.0.2 (3 Mar 2026); CLAP scan and multi-out fixes; Sessions naming; installs alongside v7 but cannot run simultaneously. (A "v8.1" mentioned on dubspot.com is not verified.)
- **[S3]** PreSonus Knowledge Base, *Dropout Protection* (article id 9223446792461), plus the Studio One 4/5 reference manual sections and Sound On Sound coverage: dual buffer; the < 3 ms latency rule for the low-latency monitoring path; automatic delay compensation.
- **[S4]** Sound On Sound, *Studio One: How To Do Side-chaining* (VST3 sidechain via pre/post sends or outputs; multiple sources). **[S4b]** MusicTech Studio One sidechain tutorial (same points).
- **[S6]** studiooneforum.com thread "Be aware of these Plugin Delay Compensation Fails" (FORUM, user reports of PDC issues with sidechain/bus routing).
- **[S7]** github.com/fenderdigital/presonus-plugin-extensions (public domain; pushed Jul 2026). Headers: `IContextInfoProvider` (channel name/type/index/colour, send count and levels, kDocumentID, kActiveDocumentID, kDocumentName) and `ISlaveControllerHandler` / `kSlaveModeLowLatencyClone`. The README lists feature and host version history (cloned-instance notifications S1 3.5.2+, context info S1 2.6+).
- **[S8]** PreSonus feedback portal item 198358 "Plugin sandbox to prevent crashes", and answers.presonus.com question 39894 (no sandboxing found; indirect evidence).

## Licences
- **[L1]** Steinberg VST 3 developer portal, licensing page: VST 3 SDK under MIT from 3.8; VSTGUI and mda example files under BSD-style licences. https://steinbergmedia.github.io/vst3_dev_portal/
- **[L2]** CLAP `LICENSE` (MIT): https://github.com/free-audio/clap
- **[L3]** JUCE `LICENSE.md` (AGPLv3 or commercial; points to the JUCE 9 EULA of 17 Jun 2026) and juce.com licence/pricing pages (Starter ≤ $20k, Indie $40/mo or $800 ≤ $300k, Pro $175/mo or $3,500): https://github.com/juce-framework/JUCE
- **[L4]** iPlug2 licence (zlib-style): https://github.com/iPlug2/iPlug2
- **[L5]** DPF licence (ISC): https://github.com/DISTRHO/DPF
- **[L6]** nih-plug README (ISC; VST3 bindings via vst3-sys are GPLv3): https://github.com/robbert-vdh/nih-plug

## Prior art
- **[P1]** Fiedler Audio, *Dolby Atmos Composer* manual (fiedler-audio.com download ?wpdmdl=7958 / 7957) and knowledge base https://fiedler-audio.com/knowledge-base/dolby-atmos-composer/ ; Sound On Sound review https://www.soundonsound.com/reviews/fiedler-audio-dolby-atmos-composer
- **[P2]** FLUX, *SPAT PI: Local audio path*: https://doc.flux.audio/spat-revolution/Ecosystem_&_integration_DAW_Automation_Local_Audio_Path.html ; *Reporting latency for delay compensation in SPAT Revolution*: https://www.flux.audio/2022/10/18/reporting-latency-for-delay-compensation-in-spat-revolution/
- **[P3]** Audio Ease 360pan suite: https://www.audioease.com/360/ and manual https://www.audioease.com/360/files/360pan-suite-3-Pro-Tools-Manual-1.0.pdf (360reverb private ambisonics input)
- **[P4]** 2CAudio PBJ (Precedence + Breeze): https://www.2caudio.com/products/pbj
- **[P5]** Sound On Sound review of Vienna MIR Pro 3D (standalone room app + DAW plug-ins)
- **[P6]** iZotope blog, *How Inter-plugin Communication Shows up in Your Workflow* (16 Jan 2020): https://www.izotope.com/community/blog/inter-plugin-communication-explained
- **[P7]** Blue Cat Audio, *Blue Cat's Connector* product page (app / local host / network modes, buffering, latency compensation)
- Search-summary only (**not relied on**): Sound Particles Space Controller manual (up to 128 instances), sonible smart:comp 2 group mode.

## Internal
- `/workspace/build_support/planning/C_MIGRATION_PLAN.md` §9–10 (Designs A/B, licence audit, blob versioning); `BUILD_ROADMAP.md` (P8).
