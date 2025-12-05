import { classesToCss } from "./subtitles_styles.js";

/**
 * Рендер одного субтитра.
 * Цвет применяется ко ВСЕЙ реплике (speaker + text),
 * а отдельные классы — к внутренним элементам.
 */
export function renderSubtitle(id, text, color, speaker, classes = []) {
    const el = document.getElementById(id);
    if (!el) return;

    const cssClasses = classesToCss(classes);

    // Весь цвет применяется К ОБЁРТКЕ
    const colorStyle = color ? `color: ${color};` : "";

    const speakerHtml = speaker
        ? `<span class="speaker ${cssClasses}">${speaker}:</span>`
        : "";

    const textHtml = `<span class="subtitle-text ${cssClasses}">${text}</span>`;

    // Обёртка реплики (фон + цвет спикера)
    el.innerHTML = `
        <div class="subtitle-line-text ${cssClasses}" style="${colorStyle}">
            ${speakerHtml} ${textHtml}
        </div>
    `;

    el.style.display = "block";
}

export function clearSubtitle(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    el.style.display = "none";
}
