# Hoops Without Borders – dagelijkse Short (runbook voor de automatische sessie)

Kanaal: Hoops Without Borders · Studio-ID UC1hu7r8SS20MVl1QT6hvcFw (NIET @nielswijkvan5645)
Upload: direct openbaar (keuze eigenaar). Stem: Kokoro am_michael (gratis). Geen officiële wedstrijdbeelden, geen AI-beelden van echte spelers.

## Dagritme (keuze eigenaar, 15-11-2026)
- **09:00 – plannen + melden (niets uploaden):** als history.json een upload met status "pending" heeft, kondig je DIE opnieuw aan (nieuwsonderwerp ouder dan 3 dagen → mag vervangen worden door een nieuw onderwerp). Anders: stap 2–5 hieronder (onderwerp, feitencheck, script.json). Voeg aan script.json toe: "clips_needed": [3–6 concrete omschrijvingen, bv. "Brunson – 45 punten Game 5 Finals 2026, clutch shots laatste minuten"]. Maak op de Mac de map `/Users/nielsvanwijk/Documents/HWB highlights/<slug>/` (device_bash: mkdir -p "$HOME/mnt/Documents/HWB highlights/<slug>"). Zet in history.json een item met status "pending". Commit + push. Stuur PushNotification (≤200 tekens), bv.: "HWB vandaag: <titel>. Clips in Documenten/HWB highlights/<slug>: 1) … 2) … 3) …. Upload 17:00." Zet de volledige cliplijst ook in je eindbericht.
- **17:00 – uploaden:** zoek het item met status "pending". Staan er clips in `HWB highlights/<slug>/` (of clips met de spelernaam in `HWB highlights/`)? Ja → render met die clips (stap 5b/6) en upload openbaar (stap 7–9), status "uploaded". Nee → NIET uploaden, status blijft "pending", PushNotification: "Geen clips voor <titel> — morgen opnieuw." Nooit uploaden zonder clips.

## Stappen
1. `git clone` deze repo → `pip install --break-system-packages kokoro-onnx soundfile`; download modellen:
   - https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
   - https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
2. Lees `history.json` (eerdere onderwerpen + views). Kies een NIEUW onderwerp, niet herhalen binnen 30 dagen.
3. Onderwerpkeuze (uit kanaalanalyse 15-11-2026): bekende NBA-sterren van nu + underdog/controverse/bijnaam-hook werkt het best
   (Wemby-block 5,3K, Curry "Baby-Faced Assassin" 4,9K). Europese historie ±1,3K → max 2× per week, met sterke hook.
   Recente wedstrijdmomenten (laatste 48 u) scoren goed: zoek het nieuws van gisteren.
4. Feitencheck: elk getal/datum via WebSearch uit ≥1 betrouwbare bron (ESPN, NBA.com, AP, Basketball-Reference). Twijfel → weglaten.
5. Schrijf `shorts/<datum>-<slug>/script.json` (zie voorbeeld). 110–140 woorden, hook in zin 1, eindigen met een vraag + "follow for more".
   Titel: ≤60 tekens, hook + emoji + #shorts. Beschrijving met vraag + hashtags.
5b. ACHTERGROND-HIGHLIGHTS (keuze eigenaar, op eigen risico): clips levert de eigenaar zelf aan op de Mac in /Users/nielsvanwijk/Documents/HWB highlights/<slug>/ (of met spelernaam in HWB highlights/).
   - device_list_dir op die map; kies clips waarvan de bestandsnaam bij de speler/het onderwerp past (bv. brunson-1.mp4), anders algemene clips; liefst een andere clip per segment.
   - device_stage_files → ze komen in /mnt/user-data/uploads/HWB highlights/… Zet in script.json: "clips": ["<stagedPath1>", "<stagedPath2>", ...] (render.py wisselt per segment; per segment overschrijven kan met "clip": {"path":..., "start": sec}).
   - Geen clips in de map: render zonder clips (grafisch) en meld in je eindbericht dat de map leeg is.
   - Download zelf NOOIT video's van YouTube of andere sites; alleen clips uit deze map.
6. `python3 render.py shorts/.../script.json shorts/.../short.mp4` (≈2 min). Controleer 4 frames visueel.
7. Commit + push naar `main`. Raw-URL: https://raw.githubusercontent.com/nielsvanwijk2002-ux/HWB-shorts-/main/shorts/<map>/short.mp4
8. Upload in de built-in browser (studio.youtube.com/channel/UC1hu7r8SS20MVl1QT6hvcFw/videos/short):
   - Klik "Maken" → "Video's uploaden". Injecteer bestand via javascript_tool:
     ```js
     const r = await fetch(RAW_URL); const b = await r.blob();
     const f = new File([b], 'short.mp4', {type:'video/mp4'});
     const inp = document.querySelector('input[type=file]');
     const dt = new DataTransfer(); dt.items.add(f); inp.files = dt.files;
     inp.dispatchEvent(new Event('change', {bubbles:true})); 'ok ' + b.size
     ```
   - Open eerst https://studio.youtube.com/channel/UC1hu7r8SS20MVl1QT6hvcFw/videos/upload?d=ud (uploaddialoog met input[type=file]).
   - Titel/beschrijving: `const b=[...document.querySelectorAll('ytcp-uploads-dialog #textbox')]` → per box focus, execCommand('selectAll'), execCommand('insertText', false, tekst).
   - `tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]` klikken, `#next-button` 3× (1,2 s pauze), `tp-yt-paper-radio-button[name="PUBLIC"]`.
   - WACHT tot de controle (onderbalk "x% gecontroleerd") klaar is (~5 min, poll elke 60 s), pas dan `#done-button`. Kies nooit "Toch publiceren".
   - Komt er een auteursrecht-/beleidswaarschuwing uit de controle: NIET publiceren, privé laten, en in de pushmelding melden.
   - Short-link staat in de dialoog (youtube.com/shorts/...).
9. Update `history.json` (datum, titel, url) en push.
10. Elke 3 dagen (aparte taak): Studio → Content → Shorts: views per video in history.json zetten, analyse + pushmelding.
