export async function loadVTT(url) {
    const raw = await fetchText(url);
    const lines = raw.split("\n");

    const subs = [];
    let current = null;

    for (const rawLine of lines) {
        const line = rawLine.trim();

        // Пустая строка — завершение cue
        if (!line) {
            if (current) {
                subs.push(current);
                current = null;
            }
            continue;
        }

        // Временной диапазон
        if (line.includes("-->")) {
            const [start, end] = line.split("-->").map(s => s.trim());

            current = {
                start: timeToSeconds(start),
                end: timeToSeconds(end),
                text: "",
                speaker: null,
                classes: []
            };
            continue;
        }

        // Текст с тегами — обрабатываем
        if (current) {
            const parsed = parseVTTCueText(line);
            current.text += (current.text ? "\n" : "") + parsed.text;

            // устанавливаем спикера, если есть
            if (parsed.speaker && !current.speaker) {
                current.speaker = parsed.speaker;
            }

            // добавляем классы
            if (parsed.classes.length) {
                current.classes.push(...parsed.classes);
            }
        }
    }

    return subs;
}

// -----------------------
//  ПАРСЕР СТРОКИ VTT CUE
// -----------------------
function parseVTTCueText(line) {
    let speaker = null;
    let classes = [];
    let text = line;

    // <v Speaker>
    const speakerRegex = /<v\s+([^>]+)>/i;
    const sp = text.match(speakerRegex);
    if (sp) {
        speaker = sp[1].trim();
        text = text.replace(speakerRegex, "").replace("</v>", "");
    }

    // <c.bold.italic>
    const classRegex = /<c\.([^>]+)>/gi;
    let match;
    while ((match = classRegex.exec(text)) !== null) {
        classes.push(...match[1].split("."));
    }
    text = text.replace(/<c\.[^>]+>/gi, "").replace(/<\/c>/gi, "");

    // убираем остальные HTML-теги (<i> <b> и т.д.) — в VTT так принято
    text = text.replace(/<\/?[^>]+>/g, "");

    return { speaker, classes, text };
}

// -----------------------
function timeToSeconds(t) {
    const [h, m, s] = t.split(":");
    return parseInt(h) * 3600 + parseInt(m) * 60 + parseFloat(s.replace(",", "."));
}

async function fetchText(url) {
    const r = await fetch(url, { cache: "no-cache" });
    return r.text();
}